"""Applicant endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.integrations.simulated import SimulatedWalletAdapter
from app.modules.applicant import service
from app.modules.applicant.models import TransactionRecord
from app.modules.applicant.schemas import (
    ApplicantCreate,
    ApplicantOut,
    FinancialSummary,
)

router = APIRouter(prefix="/applicants", tags=["applicants"])


@router.post("", response_model=ApplicantOut, status_code=201)
def create(
    body: ApplicantCreate,
    user: CurrentUser = Depends(require("applicant:manage")),
    db: Session = Depends(get_db),
) -> ApplicantOut:
    applicant = service.create_applicant(db, user.org_id, body)
    return ApplicantOut.model_validate(applicant)


@router.get("", response_model=list[ApplicantOut])
def list_all(
    user: CurrentUser = Depends(require("applicant:read")),
    db: Session = Depends(get_db),
) -> list[ApplicantOut]:
    return [
        ApplicantOut.model_validate(a) for a in service.list_applicants(db, user.org_id)
    ]


@router.get("/{applicant_id}", response_model=ApplicantOut)
def get_one(
    applicant_id: uuid.UUID,
    user: CurrentUser = Depends(require("applicant:read")),
    db: Session = Depends(get_db),
) -> ApplicantOut:
    return ApplicantOut.model_validate(service.get_applicant(db, applicant_id))


@router.get("/{applicant_id}/financials", response_model=FinancialSummary)
def financials(
    applicant_id: uuid.UUID,
    user: CurrentUser = Depends(require("applicant:read")),
    db: Session = Depends(get_db),
) -> FinancialSummary:
    f = service.compute_financials(db, applicant_id)
    return FinancialSummary(**{k: f[k] for k in FinancialSummary.model_fields})


@router.post("/{applicant_id}/simulate-transactions", status_code=201)
def simulate_transactions(
    applicant_id: uuid.UUID,
    user: CurrentUser = Depends(require("applicant:manage")),
    db: Session = Depends(get_db),
) -> dict:
    """Populate SIMULATED wallet transactions (clearly flagged is_simulated=True)."""
    service.get_applicant(db, applicant_id)  # tenant-scope check
    adapter = SimulatedWalletAdapter()
    txns = adapter.fetch_transactions(str(applicant_id))
    for t in txns:
        db.add(
            TransactionRecord(
                organization_id=user.org_id,
                applicant_id=applicant_id,
                source_type="wallet",
                txn_date=t["txn_date"],
                amount=t["amount"],
                description=t["description"],
                is_simulated=True,
            )
        )
    db.flush()
    return {"created": len(txns), "is_simulated": True}
