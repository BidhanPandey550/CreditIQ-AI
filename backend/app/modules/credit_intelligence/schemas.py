from __future__ import annotations

import uuid

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShapContribution(_StrictSchema):
    feature: str
    impact: float
    value: float | int


class RiskResult(_StrictSchema):
    band: Literal["low", "medium", "high"]
    probability: float = Field(ge=0.0, le=1.0)


class CreditScoreResult(_StrictSchema):
    score: int = Field(ge=300, le=850)
    subscores: dict


class DefaultResult(_StrictSchema):
    probability: float = Field(ge=0.0, le=1.0)
    horizon_months: int = Field(gt=0)


class FraudResult(_StrictSchema):
    severity: Literal["low", "medium", "high", "critical"]
    level: str
    reasons: list[str]
    anomaly_score: float = Field(ge=0.0, le=1.0)
    score: int = Field(ge=0, le=1000)


class ExplanationResult(_StrictSchema):
    contributions: list[ShapContribution]
    narrative: str = Field(min_length=1)


class MLPrediction(_StrictSchema):
    """Validated wire contract returned by the governed ML serving process."""

    model_version: str = Field(min_length=1)
    risk: RiskResult
    credit_score: CreditScoreResult
    default: DefaultResult
    fraud: FraudResult
    explanation: ExplanationResult


class AnalysisResult(_StrictSchema):
    loan_id: uuid.UUID
    model_version: str
    features: dict
    risk: RiskResult
    credit_score: CreditScoreResult
    default: DefaultResult
    fraud: FraudResult
    explanation_narrative: str
    shap_contributions: list[ShapContribution]
