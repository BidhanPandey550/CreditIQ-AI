"""Applicant management + financial feature computation."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.applicant.models import (
    Applicant,
    AssetRecord,
    EmploymentRecord,
    ExistingLoan,
    ExpenseRecord,
    IncomeRecord,
    KycRecord,
    LiabilityRecord,
    TransactionRecord,
)


def _monthly(amount: float, frequency: str) -> float:
    factor = {
        "monthly": 1,
        "weekly": 4.33,
        "daily": 30,
        "yearly": 1 / 12,
        "quarterly": 1 / 3,
    }.get(frequency, 1)
    return float(amount) * factor


def create_applicant(db: Session, org_id: uuid.UUID, data) -> Applicant:
    applicant = Applicant(
        organization_id=org_id,
        branch_id=data.branch_id,
        full_name=data.full_name,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        phone=data.phone,
        email=data.email,
        address=data.address,
        is_self_employed=data.is_self_employed,
    )
    db.add(applicant)
    db.flush()

    if data.national_id:
        db.add(
            KycRecord(
                organization_id=org_id,
                applicant_id=applicant.id,
                national_id=data.national_id,
                document_type="citizenship",
            )
        )
    if data.employment:
        db.add(
            EmploymentRecord(
                organization_id=org_id,
                applicant_id=applicant.id,
                **data.employment.model_dump(),
            )
        )
    for i in data.incomes:
        db.add(IncomeRecord(organization_id=org_id, applicant_id=applicant.id, **i.model_dump()))
    for e in data.expenses:
        db.add(ExpenseRecord(organization_id=org_id, applicant_id=applicant.id, **e.model_dump()))
    for a in data.assets:
        db.add(AssetRecord(organization_id=org_id, applicant_id=applicant.id, **a.model_dump()))
    for lb in data.liabilities:
        db.add(
            LiabilityRecord(organization_id=org_id, applicant_id=applicant.id, **lb.model_dump())
        )
    for xl in data.existing_loans:
        db.add(ExistingLoan(organization_id=org_id, applicant_id=applicant.id, **xl.model_dump()))
    db.flush()
    return applicant


def get_applicant(db: Session, applicant_id: uuid.UUID) -> Applicant:
    applicant = db.get(Applicant, applicant_id)
    if not applicant:
        raise NotFoundError("Applicant not found")
    return applicant


def list_applicants(db: Session, org_id: uuid.UUID) -> list[Applicant]:
    return list(
        db.scalars(
            select(Applicant)
            .where(Applicant.organization_id == org_id)
            .order_by(Applicant.created_at.desc())
        ).all()
    )


def compute_financials(db: Session, applicant_id: uuid.UUID) -> dict:
    """Aggregate the profile into the feature dict the ML engine consumes."""
    get_applicant(db, applicant_id)  # ensures existence / tenant scope

    incomes = db.scalars(
        select(IncomeRecord).where(IncomeRecord.applicant_id == applicant_id)
    ).all()
    expenses = db.scalars(
        select(ExpenseRecord).where(ExpenseRecord.applicant_id == applicant_id)
    ).all()
    assets = db.scalars(select(AssetRecord).where(AssetRecord.applicant_id == applicant_id)).all()
    liabilities = db.scalars(
        select(LiabilityRecord).where(LiabilityRecord.applicant_id == applicant_id)
    ).all()
    existing = db.scalars(
        select(ExistingLoan).where(ExistingLoan.applicant_id == applicant_id)
    ).all()
    txns = db.scalars(
        select(TransactionRecord).where(TransactionRecord.applicant_id == applicant_id)
    ).all()

    monthly_income = sum(_monthly(float(i.amount), i.frequency) for i in incomes)
    monthly_expenses = sum(_monthly(float(e.amount), e.frequency) for e in expenses)
    monthly_debt = sum(float(x.monthly_installment or 0) for x in existing) + sum(
        float(lb.monthly_payment or 0) for lb in liabilities
    )
    total_assets = sum(float(a.value) for a in assets)
    total_liabilities = sum(float(lb.outstanding_amount) for lb in liabilities) + sum(
        float(x.outstanding_amount) for x in existing
    )
    has_delinquency = any(x.is_delinquent for x in existing)

    dti = (monthly_debt / monthly_income) if monthly_income else 1.0
    savings = monthly_income - monthly_expenses - monthly_debt
    savings_ratio = (savings / monthly_income) if monthly_income else 0.0

    # Transaction-derived behavioural features (from simulated wallet data)
    credits = [float(t.amount) for t in txns if float(t.amount) > 0]
    income_stability = min(1.0, len(credits) / 30) if credits else 0.3
    if credits:
        mean_c = sum(credits) / len(credits)
        var = sum((c - mean_c) ** 2 for c in credits) / len(credits)
        cashflow_volatility = min(1.0, (var**0.5) / mean_c) if mean_c else 0.5
    else:
        cashflow_volatility = 0.6

    return {
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses": round(monthly_expenses, 2),
        "monthly_debt_payments": round(monthly_debt, 2),
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "net_worth": round(total_assets - total_liabilities, 2),
        "debt_to_income": round(min(dti, 2.0), 4),
        "savings_ratio": round(max(min(savings_ratio, 1.0), -1.0), 4),
        "income_stability": round(income_stability, 4),
        "cashflow_volatility": round(cashflow_volatility, 4),
        "has_delinquency": has_delinquency,
    }
