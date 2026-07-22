"""Applicant endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.integrations.simulated import SimulatedWalletAdapter
from app.modules.applicant import documents, service
from app.modules.applicant.models import TransactionRecord
from app.modules.applicant.schemas import (
    ApplicantCreate,
    ApplicantOut,
    ApplicantProfileOut,
    ApplicantProfileUpdate,
    FinancialSummary,
    FinancialDocumentOut,
    TransactionPage,
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
        after={"profile_created": True, "branch_id": str(applicant.branch_id)},
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


@router.get("/{applicant_id}/profile", response_model=ApplicantProfileOut)
def get_profile(
    applicant_id: uuid.UUID,
    user: CurrentUser = Depends(require("applicant:read")),
    db: Session = Depends(get_db),
) -> ApplicantProfileOut:
    return service.get_profile(db, applicant_id, user)


@router.patch("/{applicant_id}/profile", response_model=ApplicantProfileOut)
def update_profile(
    applicant_id: uuid.UUID,
    body: ApplicantProfileUpdate,
    user: CurrentUser = Depends(require("applicant:manage")),
    db: Session = Depends(get_db),
) -> ApplicantProfileOut:
    return service.update_profile(db, user, applicant_id, body)


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
    replaced = (
        db.scalar(
            select(func.count(TransactionRecord.id)).where(
                TransactionRecord.organization_id == user.org_id,
                TransactionRecord.applicant_id == applicant_id,
                TransactionRecord.source_type == "wallet",
                TransactionRecord.is_simulated.is_(True),
            )
        )
        or 0
    )
    db.execute(
        delete(TransactionRecord).where(
            TransactionRecord.organization_id == user.org_id,
            TransactionRecord.applicant_id == applicant_id,
            TransactionRecord.source_type == "wallet",
            TransactionRecord.is_simulated.is_(True),
        )
    )
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
        after={
            "created": len(txns),
            "replaced": replaced,
            "source": "wallet",
            "is_simulated": True,
        },
    )
    return {"created": len(txns), "replaced": replaced, "is_simulated": True}


@router.get("/{applicant_id}/transactions", response_model=TransactionPage)
def transactions(
    applicant_id: uuid.UUID,
    source_type: str | None = Query(default=None, pattern=r"^(bank|wallet|utility)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(require("applicant:read")),
    db: Session = Depends(get_db),
) -> TransactionPage:
    """Return authorized financial evidence; simulated records remain explicitly labelled."""
    return TransactionPage.model_validate(
        service.list_transactions(
            db, user, applicant_id, source_type=source_type, limit=limit, offset=offset
        )
    )


@router.get("/{applicant_id}/documents", response_model=list[FinancialDocumentOut])
def list_documents(
    applicant_id: uuid.UUID,
    user: CurrentUser = Depends(require("document:read")),
    db: Session = Depends(get_db),
) -> list[FinancialDocumentOut]:
    return [
        FinancialDocumentOut.model_validate(item)
        for item in documents.list_documents(db, user, applicant_id)
    ]


@router.post(
    "/{applicant_id}/documents",
    response_model=FinancialDocumentOut,
    status_code=201,
    dependencies=[Depends(rate_limit("document-upload", settings.document_upload_rate_limit))],
)
async def upload_document(
    applicant_id: uuid.UUID,
    doc_type: str = Form(..., max_length=80),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require("document:upload")),
    db: Session = Depends(get_db),
) -> FinancialDocumentOut:
    content = await file.read(settings.document_max_bytes + 1)
    await file.close()
    document = documents.create_document(
        db,
        user,
        applicant_id,
        doc_type=doc_type,
        filename=file.filename,
        declared_content_type=file.content_type,
        content=content,
    )
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="applicant.document.upload",
        entity_type="financial_document",
        entity_id=document.id,
        after={
            "applicant_id": str(applicant_id),
            "doc_type": document.doc_type,
            "size_bytes": document.size_bytes,
            "scan_status": document.scan_status,
        },
    )
    return FinancialDocumentOut.model_validate(document)


@router.get("/{applicant_id}/documents/{document_id}/download")
def download_document(
    applicant_id: uuid.UUID,
    document_id: uuid.UUID,
    user: CurrentUser = Depends(require("document:read")),
    db: Session = Depends(get_db),
) -> Response:
    document, content = documents.read_document(db, user, applicant_id, document_id)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="applicant.document.download",
        entity_type="financial_document",
        entity_id=document.id,
    )
    return Response(
        content=content,
        media_type=document.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_filename or "document"}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
