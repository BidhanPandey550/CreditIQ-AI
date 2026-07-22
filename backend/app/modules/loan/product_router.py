"""Loan-product administration API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.core.exceptions import PermissionDeniedError
from app.modules.loan import products
from app.modules.loan.schemas import LoanProductCreate, LoanProductOut, LoanProductUpdate

router = APIRouter(prefix="/loan-products", tags=["loan-products"])


@router.get("", response_model=list[LoanProductOut])
def list_products(
    include_inactive: bool = False,
    user: CurrentUser = Depends(require("loan:read")),
    db: Session = Depends(get_db),
) -> list[LoanProductOut]:
    if include_inactive and not user.has("org:configure"):
        raise PermissionDeniedError("Organization configuration permission is required")
    return [
        LoanProductOut.model_validate(item)
        for item in products.list_products(db, user.org_id, include_inactive=include_inactive)
    ]


@router.post("", response_model=LoanProductOut, status_code=201)
def create_product(
    body: LoanProductCreate,
    user: CurrentUser = Depends(require("org:configure")),
    db: Session = Depends(get_db),
) -> LoanProductOut:
    return LoanProductOut.model_validate(products.create_product(db, user, body))


@router.patch("/{product_id}", response_model=LoanProductOut)
def update_product(
    product_id: uuid.UUID,
    body: LoanProductUpdate,
    user: CurrentUser = Depends(require("org:configure")),
    db: Session = Depends(get_db),
) -> LoanProductOut:
    return LoanProductOut.model_validate(products.update_product(db, user, product_id, body))
