"""Tenant- and branch-safe fraud investigation use cases."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.data_scope import branch_predicate
from app.core.deps import CurrentUser
from app.core.exceptions import ConflictError, DomainRuleError, NotFoundError
from app.modules.applicant.models import Applicant
from app.modules.audit import service as audit
from app.modules.credit_intelligence.models import FraudAlert
from app.modules.fraud.schemas import FraudAlertOut
from app.modules.loan.models import LoanApplication
from app.shared.enums import FraudSeverity, FraudStatus


@dataclass(frozen=True)
class FraudCase:
    alert: FraudAlert
    loan: LoanApplication
    applicant: Applicant


def _query(user: CurrentUser) -> Select:
    return (
        select(FraudAlert, LoanApplication, Applicant)
        .join(LoanApplication, LoanApplication.id == FraudAlert.loan_id)
        .join(Applicant, Applicant.id == LoanApplication.applicant_id)
        .where(
            FraudAlert.organization_id == user.org_id,
            LoanApplication.organization_id == user.org_id,
            Applicant.organization_id == user.org_id,
            branch_predicate(user, LoanApplication.branch_id),
        )
    )


def _case(row) -> FraudCase:
    alert, loan, applicant = row
    return FraudCase(alert=alert, loan=loan, applicant=applicant)


def present_alert(case: FraudCase) -> FraudAlertOut:
    return FraudAlertOut(
        id=case.alert.id,
        loan_id=case.loan.id,
        loan_reference=case.loan.reference_no,
        applicant_id=case.applicant.id,
        applicant_name=case.applicant.full_name,
        severity=case.alert.severity,
        status=case.alert.status,
        reasons=list(case.alert.reasons),
        resolved_by=case.alert.resolved_by,
        resolved_at=case.alert.resolved_at,
        resolution_note=case.alert.resolution_note,
        created_at=case.alert.created_at,
    )


def list_alerts(
    db: Session,
    user: CurrentUser,
    *,
    status: FraudStatus | None = None,
    severity: FraudSeverity | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FraudAlertOut]:
    statement = _query(user)
    if status is not None:
        statement = statement.where(FraudAlert.status == status)
    if severity is not None:
        statement = statement.where(FraudAlert.severity == severity)
    rows = db.execute(
        statement.order_by(FraudAlert.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return [present_alert(_case(row)) for row in rows]


def get_alert(
    db: Session, user: CurrentUser, alert_id: uuid.UUID, *, lock: bool = False
) -> FraudCase:
    statement = _query(user).where(FraudAlert.id == alert_id)
    if lock:
        statement = statement.with_for_update(of=FraudAlert)
    row = db.execute(statement).first()
    if row is None:
        raise NotFoundError("Fraud alert not found")
    return _case(row)


def resolve_alert(
    db: Session,
    user: CurrentUser,
    alert_id: uuid.UUID,
    status: FraudStatus,
    note: str,
) -> FraudAlertOut:
    if status not in {FraudStatus.confirmed, FraudStatus.dismissed}:
        raise DomainRuleError("Fraud resolution must be confirmed or dismissed")
    case = get_alert(db, user, alert_id, lock=True)
    if FraudStatus(case.alert.status) is not FraudStatus.open:
        raise ConflictError("Fraud alert has already been resolved")

    before = {"status": FraudStatus(case.alert.status).value}
    case.alert.status = status
    case.alert.resolved_by = user.user_id
    from app.db.base import utcnow

    case.alert.resolved_at = utcnow()
    case.alert.resolution_note = note.strip()
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="fraud.alert.resolve",
        entity_type="fraud_alert",
        entity_id=case.alert.id,
        before=before,
        after={"status": status.value, "resolution_note": case.alert.resolution_note},
    )
    db.flush()
    return present_alert(case)
