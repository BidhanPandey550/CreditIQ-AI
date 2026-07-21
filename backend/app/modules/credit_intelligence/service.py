"""Credit Intelligence use case: run all ML predictions for a loan and persist them
(with explanations). This is the single gateway to the ML engine."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.applicant.service import compute_financials
from app.modules.credit_intelligence.ml_client import ml_client
from app.modules.credit_intelligence.models import (
    AiExplanation,
    CreditScore,
    DefaultPrediction,
    FraudAlert,
    RiskScore,
)


def analyze_loan(
    db: Session, org_id: uuid.UUID, loan_id: uuid.UUID, applicant_id: uuid.UUID
) -> dict:
    features = compute_financials(db, applicant_id)
    result = ml_client.predict(features)
    version = result.get("model_version", "unknown")

    db.add(
        RiskScore(
            organization_id=org_id,
            loan_id=loan_id,
            band=result["risk"]["band"],
            probability=result["risk"]["probability"],
            model_version=version,
            feature_snapshot=features,
        )
    )
    db.add(
        CreditScore(
            organization_id=org_id,
            loan_id=loan_id,
            score=result["credit_score"]["score"],
            subscores=result["credit_score"]["subscores"],
            model_version=version,
        )
    )
    db.add(
        DefaultPrediction(
            organization_id=org_id,
            loan_id=loan_id,
            probability=result["default"]["probability"],
            horizon_months=result["default"]["horizon_months"],
            model_version=version,
        )
    )

    fraud = result["fraud"]
    if fraud["severity"] != "low":
        db.add(
            FraudAlert(
                organization_id=org_id,
                loan_id=loan_id,
                alert_type="application_screening",
                severity=fraud["severity"],
                reasons=fraud["reasons"],
            )
        )

    expl = result["explanation"]
    db.add(
        AiExplanation(
            organization_id=org_id,
            loan_id=loan_id,
            prediction_type="risk",
            shap_contributions=expl["contributions"],
            narrative=expl["narrative"],
        )
    )
    db.flush()

    return {
        "loan_id": loan_id,
        "model_version": version,
        "features": features,
        "risk": result["risk"],
        "credit_score": result["credit_score"],
        "default": result["default"],
        "fraud": fraud,
        "explanation_narrative": expl["narrative"],
        "shap_contributions": expl["contributions"],
    }
