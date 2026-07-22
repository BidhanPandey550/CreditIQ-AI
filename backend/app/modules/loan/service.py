"""Loan origination + workflow use cases."""

from __future__ import annotations

import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.data_scope import (
    branch_predicate,
    is_applicant_user,
    require_applicant_ownership,
    require_branch_access,
    resolve_creation_branch,
)
from app.core.config import settings
from app.core.deps import CurrentUser
from app.core.exceptions import DomainRuleError, NotFoundError
from app.modules.applicant.models import Applicant
from app.modules.audit import service as audit
from app.modules.credit_intelligence.models import FraudAlert
from app.modules.loan.models import LoanApplication, LoanDecision, LoanWorkflowEvent
from app.modules.loan.products import get_product, validate_application
from app.modules.loan.workflow import LoanWorkflowPolicy, LoanWorkflowSettings
from app.modules.organization.models import Organization
from app.modules.organization.service import require_branch
from app.shared.enums import DecisionType, FraudStatus, LoanStatus


def _ref_no() -> str:
    return "LN-" + "".join(random.choices("0123456789", k=8))


def create_loan(db: Session, user: CurrentUser, data) -> LoanApplication:
    applicant = db.get(Applicant, data.applicant_id)
    if not applicant:
        raise NotFoundError("Applicant not found")
    require_applicant_ownership(user, applicant.id)
    if is_applicant_user(user):
        if data.branch_id is not None and data.branch_id != applicant.branch_id:
            raise DomainRuleError("Applicant cannot select another branch")
        branch_id = applicant.branch_id
    else:
        require_branch_access(user, applicant.branch_id)
        branch_id = resolve_creation_branch(user, data.branch_id or applicant.branch_id)
    require_branch(db, user.org_id, branch_id)
    if data.product_id is not None:
        validate_application(
            get_product(db, user.org_id, data.product_id), data.amount, data.tenor_months
        )

    loan = LoanApplication(
        organization_id=user.org_id,
        branch_id=branch_id,
        applicant_id=data.applicant_id,
        product_id=data.product_id,
        reference_no=_ref_no(),
        amount=data.amount,
        tenor_months=data.tenor_months,
        purpose=data.purpose,
        status=LoanStatus.draft,
        created_by=user.user_id,
    )
    db.add(loan)
    db.flush()
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="loan.create",
        entity_type="loan",
        entity_id=loan.id,
        after={"reference_no": loan.reference_no, "amount": float(loan.amount)},
    )
    return loan


def get_loan(db: Session, loan_id: uuid.UUID, user: CurrentUser | None = None) -> LoanApplication:
    loan = db.get(LoanApplication, loan_id)
    if not loan:
        raise NotFoundError("Loan not found")
    if user is not None:
        require_applicant_ownership(user, loan.applicant_id)
        if not is_applicant_user(user):
            require_branch_access(user, loan.branch_id)
    return loan


def list_loans(
    db: Session, user: CurrentUser, status: LoanStatus | None = None
) -> list[LoanApplication]:
    stmt = select(LoanApplication).where(LoanApplication.organization_id == user.org_id)
    if is_applicant_user(user):
        if user.applicant_id is None:
            return []
        stmt = stmt.where(LoanApplication.applicant_id == user.applicant_id)
    else:
        stmt = stmt.where(branch_predicate(user, LoanApplication.branch_id))
    if status:
        stmt = stmt.where(LoanApplication.status == status)
    return list(db.scalars(stmt.order_by(LoanApplication.created_at.desc())).all())


def transition(
    db: Session,
    user: CurrentUser,
    loan_id: uuid.UUID,
    to_status: LoanStatus,
    reason: str | None,
) -> LoanApplication:
    loan = get_loan(db, loan_id, user)
    # status may come back from the DB as a plain string — normalise to the enum.
    current = LoanStatus(loan.status)
    organization = db.get(Organization, user.org_id)
    workflow_settings = LoanWorkflowSettings.model_validate(
        (organization.settings if organization else {}).get("loan_workflow", {})
    )
    allowed = LoanWorkflowPolicy(workflow_settings).allowed(current, amount=loan.amount)
    if to_status not in allowed:
        raise DomainRuleError(
            f"Illegal transition {current.value} → {to_status.value}. "
            f"Allowed: {sorted(s.value for s in allowed)}"
        )
    loan.status = to_status
    db.add(
        LoanWorkflowEvent(
            organization_id=user.org_id,
            loan_id=loan.id,
            from_status=current.value,
            to_status=to_status.value,
            actor_user_id=user.user_id,
            reason=reason,
        )
    )
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="loan.transition",
        entity_type="loan",
        entity_id=loan.id,
        before={"status": current.value},
        after={"status": to_status.value},
    )
    db.flush()
    return loan


def decide(db: Session, user: CurrentUser, loan_id: uuid.UUID, data) -> LoanApplication:
    loan = get_loan(db, loan_id, user)
    if data.decision is DecisionType.approve:
        ensure_fraud_clearance(db, loan.id)
    db.add(
        LoanDecision(
            organization_id=user.org_id,
            loan_id=loan.id,
            decision=data.decision,
            decided_by=user.user_id,
            rationale=data.rationale,
            conditions=data.conditions,
        )
    )
    target = {
        DecisionType.approve: LoanStatus.approved,
        DecisionType.reject: LoanStatus.rejected,
        DecisionType.needs_more_info: LoanStatus.needs_more_info,
    }[data.decision]
    # Decisions are made during officer/analyst review — validate via the same state machine.
    return transition(db, user, loan_id, target, reason=data.rationale or "Decision recorded")


def ensure_fraud_clearance(db: Session, loan_id: uuid.UUID) -> None:
    """Block approval while a configured-severity alert remains open or confirmed."""
    blocking_alert = db.scalar(
        select(FraudAlert.id)
        .where(
            FraudAlert.loan_id == loan_id,
            FraudAlert.severity.in_(settings.approval_blocking_fraud_severities),
            FraudAlert.status != FraudStatus.dismissed,
        )
        .limit(1)
    )
    if blocking_alert is not None:
        raise DomainRuleError(
            "Loan cannot be approved until blocking fraud alerts are dismissed; "
            "confirmed alerts require rejection or further investigation"
        )


def workflow_history(db: Session, loan_id: uuid.UUID, user: CurrentUser) -> list[LoanWorkflowEvent]:
    get_loan(db, loan_id, user)
    return list(
        db.scalars(
            select(LoanWorkflowEvent)
            .where(LoanWorkflowEvent.loan_id == loan_id)
            .order_by(LoanWorkflowEvent.created_at.asc())
        ).all()
    )
