from __future__ import annotations

import uuid

from pydantic import BaseModel


class ShapContribution(BaseModel):
    feature: str
    impact: float
    value: float | int


class RiskResult(BaseModel):
    band: str
    probability: float


class CreditScoreResult(BaseModel):
    score: int
    subscores: dict


class DefaultResult(BaseModel):
    probability: float
    horizon_months: int


class FraudResult(BaseModel):
    severity: str
    reasons: list[str]


class AnalysisResult(BaseModel):
    loan_id: uuid.UUID
    model_version: str
    features: dict
    risk: RiskResult
    credit_score: CreditScoreResult
    default: DefaultResult
    fraud: FraudResult
    explanation_narrative: str
    shap_contributions: list[ShapContribution]
