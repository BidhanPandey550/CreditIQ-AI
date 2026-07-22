"""Applicant management + financial feature computation."""

from __future__ import annotations

import hashlib
import hmac
import uuid

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.core.data_scope import (
    branch_predicate,
    is_applicant_user,
    require_applicant_ownership,
    require_branch_access,
    resolve_creation_branch,
)
from app.core.deps import CurrentUser
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.modules.applicant.models import (
    Applicant,
    AssetRecord,
    BusinessRecord,
    EmploymentRecord,
    ExistingLoan,
    ExpenseRecord,
    IncomeRecord,
    KycRecord,
    LiabilityRecord,
    TransactionRecord,
)
from app.modules.applicant.schemas import (
    ApplicantProfileOut,
    AssetIn,
    BusinessIn,
    EmploymentIn,
    ExistingLoanIn,
    ExpenseIn,
    IncomeIn,
    LiabilityIn,
)
from app.modules.audit import service as audit
from app.modules.organization.service import require_branch


def _monthly(amount: float, frequency: str) -> float:
    factor = {
        "monthly": 1,
        "weekly": 4.33,
        "daily": 30,
        "yearly": 1 / 12,
        "quarterly": 1 / 3,
    }.get(frequency, 1)
    return float(amount) * factor


def create_applicant(db: Session, user: CurrentUser, data) -> Applicant:
    branch_id = resolve_creation_branch(user, data.branch_id)
    require_branch(db, user.org_id, branch_id)
    applicant = Applicant(
        organization_id=user.org_id,
        branch_id=branch_id,
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
                organization_id=user.org_id,
                applicant_id=applicant.id,
                national_id=data.national_id,
                document_type="citizenship",
            )
        )
    if data.employment:
        db.add(
            EmploymentRecord(
                organization_id=user.org_id,
                applicant_id=applicant.id,
                **data.employment.model_dump(),
            )
        )
    if data.business:
        db.add(
            BusinessRecord(
                organization_id=user.org_id,
                applicant_id=applicant.id,
                **data.business.model_dump(),
            )
        )
    for i in data.incomes:
        db.add(
            IncomeRecord(organization_id=user.org_id, applicant_id=applicant.id, **i.model_dump())
        )
    for e in data.expenses:
        db.add(
            ExpenseRecord(organization_id=user.org_id, applicant_id=applicant.id, **e.model_dump())
        )
    for a in data.assets:
        db.add(
            AssetRecord(organization_id=user.org_id, applicant_id=applicant.id, **a.model_dump())
        )
    for lb in data.liabilities:
        db.add(
            LiabilityRecord(
                organization_id=user.org_id,
                applicant_id=applicant.id,
                **lb.model_dump(),
            )
        )
    for xl in data.existing_loans:
        db.add(
            ExistingLoan(
                organization_id=user.org_id,
                applicant_id=applicant.id,
                **xl.model_dump(),
            )
        )
    db.flush()
    return applicant


def get_profile(db: Session, applicant_id: uuid.UUID, user: CurrentUser) -> ApplicantProfileOut:
    applicant = get_applicant(db, applicant_id, user)
    kyc = _first(db, KycRecord, applicant_id)
    employment = _first(db, EmploymentRecord, applicant_id)
    business = _first(db, BusinessRecord, applicant_id)
    return ApplicantProfileOut(
        id=applicant.id,
        branch_id=applicant.branch_id,
        full_name=applicant.full_name,
        date_of_birth=applicant.date_of_birth,
        gender=applicant.gender,
        phone=applicant.phone,
        email=applicant.email,
        address=applicant.address,
        is_self_employed=applicant.is_self_employed,
        national_id=kyc.national_id if kyc else None,
        kyc_verification_status=kyc.verification_status if kyc else None,
        employment=EmploymentIn.model_validate(employment) if employment else None,
        business=BusinessIn.model_validate(business) if business else None,
        incomes=[IncomeIn.model_validate(item) for item in _all(db, IncomeRecord, applicant_id)],
        expenses=[ExpenseIn.model_validate(item) for item in _all(db, ExpenseRecord, applicant_id)],
        assets=[AssetIn.model_validate(item) for item in _all(db, AssetRecord, applicant_id)],
        liabilities=[
            LiabilityIn.model_validate(item) for item in _all(db, LiabilityRecord, applicant_id)
        ],
        existing_loans=[
            ExistingLoanIn.model_validate(item) for item in _all(db, ExistingLoan, applicant_id)
        ],
    )


def update_profile(
    db: Session, user: CurrentUser, applicant_id: uuid.UUID, data
) -> ApplicantProfileOut:
    applicant = get_applicant(db, applicant_id, user)
    db.refresh(applicant, with_for_update=True)
    before = _audit_profile(get_profile(db, applicant_id, user))
    supplied = data.model_fields_set

    for field in (
        "full_name",
        "date_of_birth",
        "gender",
        "phone",
        "email",
        "address",
        "is_self_employed",
    ):
        if field in supplied:
            setattr(applicant, field, getattr(data, field))
    if "branch_id" in supplied:
        branch_id = resolve_creation_branch(user, data.branch_id)
        require_branch(db, user.org_id, branch_id)
        applicant.branch_id = branch_id

    if "national_id" in supplied:
        _replace_one(
            db,
            KycRecord,
            user.org_id,
            applicant.id,
            {"national_id": data.national_id, "document_type": "citizenship"}
            if data.national_id
            else None,
        )
    if "employment" in supplied:
        _replace_one(
            db,
            EmploymentRecord,
            user.org_id,
            applicant.id,
            data.employment.model_dump() if data.employment else None,
        )
    if "business" in supplied:
        _replace_one(
            db,
            BusinessRecord,
            user.org_id,
            applicant.id,
            data.business.model_dump() if data.business else None,
        )

    collections = {
        "incomes": IncomeRecord,
        "expenses": ExpenseRecord,
        "assets": AssetRecord,
        "liabilities": LiabilityRecord,
        "existing_loans": ExistingLoan,
    }
    for field, model in collections.items():
        if field in supplied:
            _replace_many(db, model, user.org_id, applicant.id, getattr(data, field) or [])

    db.flush()
    after = get_profile(db, applicant_id, user)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="applicant.profile.update",
        entity_type="applicant",
        entity_id=applicant.id,
        before=before,
        after=_audit_profile(after),
    )
    return after


def _first(db: Session, model, applicant_id: uuid.UUID):
    return db.scalars(select(model).where(model.applicant_id == applicant_id)).first()


def _all(db: Session, model, applicant_id: uuid.UUID) -> list:
    return list(db.scalars(select(model).where(model.applicant_id == applicant_id)).all())


def _replace_one(
    db: Session, model, org_id: uuid.UUID, applicant_id: uuid.UUID, values: dict | None
) -> None:
    db.execute(delete(model).where(model.applicant_id == applicant_id))
    if values is not None:
        db.add(model(organization_id=org_id, applicant_id=applicant_id, **values))


def _replace_many(
    db: Session, model, org_id: uuid.UUID, applicant_id: uuid.UUID, values: list
) -> None:
    db.execute(delete(model).where(model.applicant_id == applicant_id))
    db.add_all(
        [
            model(organization_id=org_id, applicant_id=applicant_id, **item.model_dump())
            for item in values
        ]
    )


def _audit_profile(profile: ApplicantProfileOut) -> dict:
    """Retain change evidence without copying identity data into long-lived logs."""
    snapshot = profile.model_dump(mode="json")
    for field in ("full_name", "phone", "email", "address", "national_id"):
        value = snapshot.get(field)
        if value:
            digest = hmac.new(
                settings.jwt_secret_key.encode("utf-8"),
                b"audit-pii\0" + str(value).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            snapshot[field] = f"hmac-sha256:{digest}"
    return snapshot


def get_applicant(
    db: Session, applicant_id: uuid.UUID, user: CurrentUser | None = None
) -> Applicant:
    applicant = db.get(Applicant, applicant_id)
    if not applicant:
        raise NotFoundError("Applicant not found")
    if user is not None:
        require_applicant_ownership(user, applicant.id)
        if not is_applicant_user(user):
            require_branch_access(user, applicant.branch_id)
    return applicant


def list_applicants(db: Session, user: CurrentUser) -> list[Applicant]:
    if is_applicant_user(user):
        if user.applicant_id is None:
            return []
        return list(
            db.scalars(
                select(Applicant).where(
                    Applicant.organization_id == user.org_id,
                    Applicant.id == user.applicant_id,
                )
            ).all()
        )
    return list(
        db.scalars(
            select(Applicant)
            .where(
                Applicant.organization_id == user.org_id,
                branch_predicate(user, Applicant.branch_id),
            )
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


def list_transactions(
    db: Session,
    user: CurrentUser,
    applicant_id: uuid.UUID,
    *,
    source_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Return an authorized, paginated ledger plus SQL-computed cash-flow totals."""
    get_applicant(db, applicant_id, user)
    conditions = [
        TransactionRecord.organization_id == user.org_id,
        TransactionRecord.applicant_id == applicant_id,
    ]
    if source_type is not None:
        conditions.append(TransactionRecord.source_type == source_type)

    total, credits, debits, simulated = db.execute(
        select(
            func.count(TransactionRecord.id),
            func.coalesce(
                func.sum(case((TransactionRecord.amount > 0, TransactionRecord.amount), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((TransactionRecord.amount < 0, -TransactionRecord.amount), else_=0)),
                0,
            ),
            func.count(TransactionRecord.id).filter(TransactionRecord.is_simulated.is_(True)),
        ).where(*conditions)
    ).one()
    items = list(
        db.scalars(
            select(TransactionRecord)
            .where(*conditions)
            .order_by(TransactionRecord.txn_date.desc(), TransactionRecord.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    credit_value = float(credits)
    debit_value = float(debits)
    return {
        "items": items,
        "total": total,
        "total_credits": round(credit_value, 2),
        "total_debits": round(debit_value, 2),
        "net_cashflow": round(credit_value - debit_value, 2),
        "simulated_count": simulated,
    }
