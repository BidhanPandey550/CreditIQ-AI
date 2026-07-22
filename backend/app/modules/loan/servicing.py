"""Loan servicing use cases: disbursement schedules, repayments, and arrears."""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser
from app.core.exceptions import ConflictError, DomainRuleError
from app.db.base import utcnow
from app.modules.audit import service as audit
from app.modules.loan import service as loan_service
from app.modules.loan.models import (
    LoanApplication,
    LoanDisbursement,
    LoanInstallment,
    LoanProduct,
    LoanRepayment,
)
from app.modules.loan.schemas import DisbursementRequest, RepaymentRequest
from app.shared.enums import LoanStatus

MONEY = Decimal("0.01")


@dataclass(frozen=True)
class InstallmentPlan:
    sequence_no: int
    due_date: date
    principal_due: Decimal
    interest_due: Decimal


def _money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def add_months(value: date, months: int) -> date:
    """Add calendar months while preserving the last valid day of month."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_amortization_schedule(
    principal: Decimal | float,
    annual_interest_rate: Decimal | float,
    tenor_months: int,
    first_due_date: date,
) -> list[InstallmentPlan]:
    """Build a reducing-balance monthly schedule with final-installment reconciliation."""
    if tenor_months <= 0:
        raise DomainRuleError("Loan tenor must be positive")
    balance = _money(principal)
    if balance <= 0:
        raise DomainRuleError("Disbursed principal must be positive")
    annual_rate = Decimal(str(annual_interest_rate))
    if annual_rate < 0:
        raise DomainRuleError("Interest rate cannot be negative")
    monthly_rate = annual_rate / Decimal("1200")
    if monthly_rate == 0:
        payment = balance / tenor_months
    else:
        growth = (Decimal(1) + monthly_rate) ** tenor_months
        payment = balance * monthly_rate * growth / (growth - Decimal(1))

    plans: list[InstallmentPlan] = []
    for index in range(tenor_months):
        interest = _money(balance * monthly_rate)
        principal_component = balance if index == tenor_months - 1 else _money(payment - interest)
        principal_component = min(principal_component, balance)
        plans.append(
            InstallmentPlan(
                sequence_no=index + 1,
                due_date=add_months(first_due_date, index),
                principal_due=principal_component,
                interest_due=interest,
            )
        )
        balance = _money(balance - principal_component)
    return plans


def create_disbursement(
    db: Session,
    user: CurrentUser,
    loan_id: uuid.UUID,
    data: DisbursementRequest,
) -> LoanApplication:
    loan = loan_service.get_loan(db, loan_id, user)
    db.refresh(loan, with_for_update=True)
    if LoanStatus(loan.status) != LoanStatus.approved:
        raise DomainRuleError("Only an approved loan can be disbursed")
    existing = db.scalars(
        select(LoanDisbursement).where(LoanDisbursement.loan_id == loan_id)
    ).first()
    if existing is not None:
        raise ConflictError("Loan has already been disbursed")

    product_rate = None
    if loan.product_id is not None:
        product = db.get(LoanProduct, loan.product_id)
        product_rate = float(product.interest_rate) if product is not None else None
    annual_rate = (
        data.annual_interest_rate
        if data.annual_interest_rate is not None
        else product_rate
        if product_rate is not None
        else settings.servicing_default_annual_interest_rate
    )
    today = utcnow()
    first_due = data.first_due_date or (
        today.date() + timedelta(days=settings.servicing_first_due_days)
    )
    if first_due <= today.date():
        raise DomainRuleError("First due date must be after the disbursement date")

    plans = build_amortization_schedule(
        float(loan.amount), annual_rate, loan.tenor_months, first_due
    )
    db.add(
        LoanDisbursement(
            organization_id=user.org_id,
            loan_id=loan.id,
            amount=loan.amount,
            annual_interest_rate=annual_rate,
            disbursed_at=today,
            first_due_date=first_due,
            external_reference=data.external_reference,
            disbursed_by=user.user_id,
        )
    )
    db.add_all(
        [
            LoanInstallment(
                organization_id=user.org_id,
                loan_id=loan.id,
                sequence_no=plan.sequence_no,
                due_date=plan.due_date,
                principal_due=plan.principal_due,
                interest_due=plan.interest_due,
                principal_paid=0,
                interest_paid=0,
            )
            for plan in plans
        ]
    )
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="loan.disbursement.create",
        entity_type="loan",
        entity_id=loan.id,
        after={
            "amount": float(loan.amount),
            "annual_interest_rate": annual_rate,
            "installment_count": len(plans),
        },
    )
    loan_service.transition(db, user, loan.id, LoanStatus.disbursed, "Funds disbursed")
    return loan_service.transition(db, user, loan.id, LoanStatus.active, "Loan active")


def _installment_outstanding(installment: LoanInstallment) -> Decimal:
    return _money(
        Decimal(str(installment.principal_due))
        + Decimal(str(installment.interest_due))
        - Decimal(str(installment.principal_paid))
        - Decimal(str(installment.interest_paid))
    )


def allocate_repayment(
    installments: list[LoanInstallment], amount: Decimal | float, paid_at: datetime
) -> Decimal:
    """Allocate interest then principal, oldest installment first; return pre-payment balance."""
    outstanding = sum((_installment_outstanding(item) for item in installments), Decimal(0))
    payment = _money(amount)
    if payment <= 0:
        raise DomainRuleError("Repayment amount must be positive")
    if payment > outstanding:
        raise DomainRuleError("Repayment exceeds the outstanding loan balance")

    remaining = payment
    for installment in installments:
        if remaining <= 0:
            break
        interest_balance = _money(
            Decimal(str(installment.interest_due)) - Decimal(str(installment.interest_paid))
        )
        interest_allocation = min(interest_balance, remaining)
        installment.interest_paid = _money(
            Decimal(str(installment.interest_paid)) + interest_allocation
        )
        remaining -= interest_allocation

        principal_balance = _money(
            Decimal(str(installment.principal_due)) - Decimal(str(installment.principal_paid))
        )
        principal_allocation = min(principal_balance, remaining)
        installment.principal_paid = _money(
            Decimal(str(installment.principal_paid)) + principal_allocation
        )
        remaining -= principal_allocation
        if _installment_outstanding(installment) == 0:
            installment.paid_at = paid_at
    return outstanding


def record_repayment(
    db: Session,
    user: CurrentUser,
    loan_id: uuid.UUID,
    data: RepaymentRequest,
) -> LoanRepayment:
    loan = loan_service.get_loan(db, loan_id, user)
    if LoanStatus(loan.status) not in {LoanStatus.active, LoanStatus.defaulted}:
        raise DomainRuleError("Repayments can only be recorded for active or defaulted loans")
    if data.external_reference is not None:
        duplicate = db.scalars(
            select(LoanRepayment).where(
                LoanRepayment.organization_id == user.org_id,
                LoanRepayment.external_reference == data.external_reference,
            )
        ).first()
        if duplicate is not None:
            raise ConflictError("Repayment external reference already exists")
    installments = list(
        db.scalars(
            select(LoanInstallment)
            .where(LoanInstallment.loan_id == loan_id)
            .order_by(LoanInstallment.sequence_no)
            .with_for_update()
        ).all()
    )
    amount = _money(data.amount)
    paid_at = data.paid_at or utcnow()
    if paid_at > utcnow():
        raise DomainRuleError("Repayment timestamp cannot be in the future")
    outstanding = allocate_repayment(installments, amount, paid_at)

    repayment = LoanRepayment(
        organization_id=user.org_id,
        loan_id=loan.id,
        amount=amount,
        paid_at=paid_at,
        external_reference=data.external_reference,
        recorded_by=user.user_id,
    )
    db.add(repayment)
    db.flush()
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="loan.repayment.record",
        entity_type="loan",
        entity_id=loan.id,
        after={"amount": float(amount), "repayment_id": str(repayment.id)},
    )
    if amount == outstanding:
        loan_service.transition(db, user, loan.id, LoanStatus.closed, "Loan fully repaid")
    return repayment


def servicing_data(
    db: Session, user: CurrentUser, loan_id: uuid.UUID, *, as_of: date | None = None
) -> dict:
    loan = loan_service.get_loan(db, loan_id, user)
    installments = list(
        db.scalars(
            select(LoanInstallment)
            .where(LoanInstallment.loan_id == loan_id)
            .order_by(LoanInstallment.sequence_no)
        ).all()
    )
    repayments = list(
        db.scalars(
            select(LoanRepayment)
            .where(LoanRepayment.loan_id == loan_id)
            .order_by(LoanRepayment.paid_at.desc())
        ).all()
    )
    effective_date = as_of or date.today()
    enriched = []
    overdue_amount = Decimal(0)
    max_dpd = 0
    next_due = None
    for installment in installments:
        outstanding = _installment_outstanding(installment)
        dpd = max(0, (effective_date - installment.due_date).days) if outstanding > 0 else 0
        is_overdue = dpd > settings.servicing_grace_days
        if is_overdue:
            overdue_amount += outstanding
            max_dpd = max(max_dpd, dpd)
        if outstanding > 0 and next_due is None:
            next_due = installment.due_date
        enriched.append((installment, float(outstanding), dpd))

    total_due = sum(
        (
            Decimal(str(item.principal_due)) + Decimal(str(item.interest_due))
            for item in installments
        ),
        Decimal(0),
    )
    total_paid = sum((Decimal(str(item.amount)) for item in repayments), Decimal(0))
    return {
        "loan": loan,
        "installments": enriched,
        "repayments": repayments,
        "original_principal": float(loan.amount),
        "total_due": float(_money(total_due)),
        "total_paid": float(_money(total_paid)),
        "outstanding": float(_money(total_due - total_paid)),
        "overdue_amount": float(_money(overdue_amount)),
        "days_past_due": max_dpd,
        "next_due_date": next_due,
    }
