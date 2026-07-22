"""Tenant loan-product policy administration."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.exceptions import ConflictError, DomainRuleError, NotFoundError
from app.modules.audit import service as audit
from app.modules.loan.models import LoanProduct
from app.modules.loan.schemas import LoanProductCreate, LoanProductUpdate


def normalize_code(value: str) -> str:
    return value.strip().upper()


def list_products(
    db: Session, org_id: uuid.UUID, *, include_inactive: bool = False
) -> list[LoanProduct]:
    statement = select(LoanProduct).where(LoanProduct.organization_id == org_id)
    if not include_inactive:
        statement = statement.where(LoanProduct.status == "active")
    return list(db.scalars(statement.order_by(LoanProduct.name)).all())


def get_product(db: Session, org_id: uuid.UUID, product_id: uuid.UUID) -> LoanProduct:
    product = db.get(LoanProduct, product_id)
    if product is None or product.organization_id != org_id:
        raise NotFoundError("Loan product not found")
    return product


def create_product(db: Session, actor: CurrentUser, data: LoanProductCreate) -> LoanProduct:
    code = normalize_code(data.code)
    duplicate = db.scalars(
        select(LoanProduct).where(
            LoanProduct.organization_id == actor.org_id,
            LoanProduct.code == code,
        )
    ).first()
    if duplicate is not None:
        raise ConflictError("Loan product code already exists")
    product = LoanProduct(
        organization_id=actor.org_id,
        code=code,
        status="active",
        **data.model_dump(exclude={"code"}),
    )
    db.add(product)
    db.flush()
    audit.record(
        db,
        org_id=actor.org_id,
        actor_user_id=actor.user_id,
        action="loan_product.create",
        entity_type="loan_product",
        entity_id=product.id,
        after={"code": product.code, "name": product.name, "status": product.status},
    )
    return product


def update_product(
    db: Session,
    actor: CurrentUser,
    product_id: uuid.UUID,
    data: LoanProductUpdate,
) -> LoanProduct:
    product = get_product(db, actor.org_id, product_id)
    before = _policy_snapshot(product)
    values = data.model_dump(exclude_unset=True)
    candidate = {**before, **values}
    _validate_policy(candidate)
    for field, value in values.items():
        setattr(product, field, value)
    audit.record(
        db,
        org_id=actor.org_id,
        actor_user_id=actor.user_id,
        action="loan_product.update",
        entity_type="loan_product",
        entity_id=product.id,
        before=before,
        after=_policy_snapshot(product),
    )
    db.flush()
    return product


def validate_application(product: LoanProduct, amount: float, tenor_months: int) -> None:
    if product.status != "active":
        raise DomainRuleError("Selected loan product is inactive")
    if not float(product.min_amount) <= amount <= float(product.max_amount):
        raise DomainRuleError("Loan amount is outside the selected product limits")
    if not product.min_tenor_months <= tenor_months <= product.max_tenor_months:
        raise DomainRuleError("Loan tenor is outside the selected product limits")


def _policy_snapshot(product: LoanProduct) -> dict:
    return {
        "name": product.name,
        "min_amount": float(product.min_amount),
        "max_amount": float(product.max_amount),
        "min_tenor_months": product.min_tenor_months,
        "max_tenor_months": product.max_tenor_months,
        "interest_rate": float(product.interest_rate),
        "status": product.status,
    }


def _validate_policy(values: dict) -> None:
    if float(values["min_amount"]) > float(values["max_amount"]):
        raise DomainRuleError("Minimum amount cannot exceed maximum amount")
    if int(values["min_tenor_months"]) > int(values["max_tenor_months"]):
        raise DomainRuleError("Minimum tenor cannot exceed maximum tenor")
