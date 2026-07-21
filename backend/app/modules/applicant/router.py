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
from app.modules.audit import service as audit

router = APIRouter(prefix="/applicants", tags=["applicants"])


@router.post("", response_model=ApplicantOut, status_code=201)
def create(
    body: ApplicantCreate,
    user: CurrentUser = Depends(require("applicant:manage")),
    db: Session = Depends(get_db),
) -> ApplicantOut:
    applicant = service.create_applicant(db, user, body)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="applicant.create",
        entity_type="applicant",
        entity_id=applicant.id,
        after={"full_name": applicant.full_name, "branch_id": str(applicant.branch_id)},
    )
    return ApplicantOut.model_validate(applicant)


@router.get("", response_model=list[ApplicantOut])
def list_all(
    user: CurrentUser = Depends(require("applicant:read")),
    db: Session = Depends(get_db),
) -> list[ApplicantOut]:
    return [ApplicantOut.model_validate(a) for a in service.list_applicants(db, user)]


@router.get("/{applicant_id}", response_model=ApplicantOut)
def get_one(
    applicant_id: uuid.UUID,
    user: CurrentUser = Depends(require("applicant:read")),
    db: Session = Depends(get_db),
) -> ApplicantOut:
    return ApplicantOut.model_validate(service.get_applicant(db, applicant_id, user))


@router.get("/{applicant_id}/financials", response_model=FinancialSummary)
def financials(
    applicant_id: uuid.UUID,
    user: CurrentUser = Depends(require("applicant:read")),
    db: Session = Depends(get_db),
) -> FinancialSummary:
    service.get_applicant(db, applicant_id, user)
    f = service.compute_financials(db, applicant_id)
    return FinancialSummary(**{k: f[k] for k in FinancialSummary.model_fields})


@router.post("/{applicant_id}/simulate-transactions", status_code=201)
def simulate_transactions(
    applicant_id: uuid.UUID,
    user: CurrentUser = Depends(require("applicant:manage")),
    db: Session = Depends(get_db),
) -> dict:
    """Populate SIMULATED wallet transactions (clearly flagged is_simulated=True)."""
    service.get_applicant(db, applicant_id, user)
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
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="applicant.transactions.simulate",
        entity_type="applicant",
        entity_id=applicant_id,
        after={"created": len(txns), "source": "wallet", "is_simulated": True},
    )
    return {"created": len(txns), "is_simulated": True}
