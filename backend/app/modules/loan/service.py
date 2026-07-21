"""Loan origination + workflow use cases."""

from __future__ import annotations

import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.exceptions import DomainRuleError, NotFoundError
from app.modules.applicant.models import Applicant
from app.modules.audit import service as audit
from app.modules.loan.models import LoanApplication, LoanDecision, LoanWorkflowEvent
from app.shared.enums import LOAN_TRANSITIONS, DecisionType, LoanStatus


def _ref_no() -> str:
    return "LN-" + "".join(random.choices("0123456789", k=8))


def create_loan(db: Session, user: CurrentUser, data) -> LoanApplication:
    applicant = db.get(Applicant, data.applicant_id)
    if not applicant:
        raise NotFoundError("Applicant not found")

    loan = LoanApplication(
        organization_id=user.org_id,
        branch_id=data.branch_id or user.branch_id,
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


def get_loan(db: Session, loan_id: uuid.UUID) -> LoanApplication:
    loan = db.get(LoanApplication, loan_id)
    if not loan:
        raise NotFoundError("Loan not found")
    return loan


def list_loans(
    db: Session, org_id: uuid.UUID, status: LoanStatus | None = None
) -> list[LoanApplication]:
    stmt = select(LoanApplication).where(LoanApplication.organization_id == org_id)
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
    loan = get_loan(db, loan_id)
    # status may come back from the DB as a plain string — normalise to the enum.
    current = LoanStatus(loan.status)
    allowed = LOAN_TRANSITIONS.get(current, set())
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
    loan = get_loan(db, loan_id)
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


def workflow_history(db: Session, loan_id: uuid.UUID) -> list[LoanWorkflowEvent]:
    return list(
        db.scalars(
            select(LoanWorkflowEvent)
            .where(LoanWorkflowEvent.loan_id == loan_id)
            .order_by(LoanWorkflowEvent.created_at.asc())
        ).all()
    )
