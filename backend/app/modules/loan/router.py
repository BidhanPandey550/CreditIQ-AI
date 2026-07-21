"""Loan endpoints — origination, workflow, AI analysis, decisions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.modules.credit_intelligence import service as ci_service
from app.modules.credit_intelligence.models import (
    AiExplanation,
    CreditScore,
    DefaultPrediction,
    FraudAlert,
    RiskScore,
)
from app.modules.loan import service
from app.modules.loan.schemas import (
    DecisionRequest,
    LoanCreate,
    LoanOut,
    TransitionRequest,
    WorkflowEventOut,
)
from app.shared.enums import LoanStatus

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=LoanOut, status_code=201)
def create(
    body: LoanCreate,
    user: CurrentUser = Depends(require("loan:create")),
    db: Session = Depends(get_db),
) -> LoanOut:
    return LoanOut.model_validate(service.create_loan(db, user, body))


@router.get("", response_model=list[LoanOut])
def list_loans(
    status: LoanStatus | None = Query(default=None),
    user: CurrentUser = Depends(require("loan:read")),
    db: Session = Depends(get_db),
) -> list[LoanOut]:
    return [LoanOut.model_validate(x) for x in service.list_loans(db, user, status)]


@router.get("/{loan_id}", response_model=LoanOut)
def get_one(
    loan_id: uuid.UUID,
    user: CurrentUser = Depends(require("loan:read")),
    db: Session = Depends(get_db),
) -> LoanOut:
    return LoanOut.model_validate(service.get_loan(db, loan_id, user))


@router.post("/{loan_id}/submit", response_model=LoanOut)
def submit(
    loan_id: uuid.UUID,
    user: CurrentUser = Depends(require("loan:create")),
    db: Session = Depends(get_db),
) -> LoanOut:
    loan = service.transition(db, user, loan_id, LoanStatus.submitted, "Submitted by applicant")
    loan = service.transition(db, user, loan_id, LoanStatus.under_review, "Queued for review")
    return LoanOut.model_validate(loan)


@router.post("/{loan_id}/transition", response_model=LoanOut)
def transition(
    loan_id: uuid.UUID,
    body: TransitionRequest,
    user: CurrentUser = Depends(require("loan:review")),
    db: Session = Depends(get_db),
) -> LoanOut:
    return LoanOut.model_validate(
        service.transition(db, user, loan_id, body.to_status, body.reason)
    )


@router.post(
    "/{loan_id}/analyze",
    dependencies=[Depends(rate_limit("ai-analysis", settings.ai_analysis_rate_limit))],
)
def analyze(
    loan_id: uuid.UUID,
    user: CurrentUser = Depends(require("loan:review")),
    db: Session = Depends(get_db),
) -> dict:
    """Run AI risk/credit/default/fraud analysis and advance to officer review."""
    loan = service.get_loan(db, loan_id, user)
    if loan.status == LoanStatus.under_review:
        service.transition(db, user, loan_id, LoanStatus.ai_risk_analysis, "AI analysis started")
    result = ci_service.analyze_loan(db, user.org_id, loan_id, loan.applicant_id)
    loan = service.get_loan(db, loan_id, user)
    if loan.status == LoanStatus.ai_risk_analysis:
        service.transition(db, user, loan_id, LoanStatus.fraud_screening, "Fraud screening")
    if loan.status == LoanStatus.fraud_screening:
        service.transition(db, user, loan_id, LoanStatus.officer_review, "Ready for officer review")
    return result


@router.post("/{loan_id}/decision", response_model=LoanOut)
def decide(
    loan_id: uuid.UUID,
    body: DecisionRequest,
    user: CurrentUser = Depends(require("loan:approve")),
    db: Session = Depends(get_db),
) -> LoanOut:
    return LoanOut.model_validate(service.decide(db, user, loan_id, body))


@router.post("/{loan_id}/disburse", response_model=LoanOut)
def disburse(
    loan_id: uuid.UUID,
    user: CurrentUser = Depends(require("loan:disburse")),
    db: Session = Depends(get_db),
) -> LoanOut:
    service.transition(db, user, loan_id, LoanStatus.disbursed, "Funds disbursed")
    loan = service.transition(db, user, loan_id, LoanStatus.active, "Loan active")
    return LoanOut.model_validate(loan)


@router.get("/{loan_id}/history", response_model=list[WorkflowEventOut])
def history(
    loan_id: uuid.UUID,
    user: CurrentUser = Depends(require("loan:read")),
    db: Session = Depends(get_db),
) -> list[WorkflowEventOut]:
    return [WorkflowEventOut.model_validate(e) for e in service.workflow_history(db, loan_id, user)]


@router.get("/{loan_id}/intelligence")
def intelligence(
    loan_id: uuid.UUID,
    user: CurrentUser = Depends(require("risk:read")),
    db: Session = Depends(get_db),
) -> dict:
    """Latest AI outputs + SHAP explanation for a loan."""
    service.get_loan(db, loan_id, user)

    def latest(model):
        return db.scalars(
            select(model).where(model.loan_id == loan_id).order_by(model.created_at.desc())
        ).first()

    risk = latest(RiskScore)
    score = latest(CreditScore)
    pd = latest(DefaultPrediction)
    expl = latest(AiExplanation)
    frauds = db.scalars(select(FraudAlert).where(FraudAlert.loan_id == loan_id)).all()

    return {
        "risk": {"band": risk.band, "probability": float(risk.probability)} if risk else None,
        "credit_score": {"score": score.score, "subscores": score.subscores} if score else None,
        "default": {
            "probability": float(pd.probability),
            "horizon_months": pd.horizon_months,
        }
        if pd
        else None,
        "fraud_alerts": [
            {"severity": f.severity, "status": f.status, "reasons": f.reasons} for f in frauds
        ],
        "explanation": {
            "narrative": expl.narrative,
            "shap_contributions": expl.shap_contributions,
        }
        if expl
        else None,
    }
