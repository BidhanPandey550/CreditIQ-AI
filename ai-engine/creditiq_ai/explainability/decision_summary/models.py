"""Audit-ready decision summary contract."""

from pydantic import BaseModel, ConfigDict, Field


class DecisionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    credit_score: int
    probability_of_default: float = Field(ge=0.0, le=1.0)
    risk_level: str
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    primary_factors: list[str]
    key_risks: list[str]
    positive_strengths: list[str]
    suggested_improvements: list[str]
    model_version: str | None = None
    feature_version: str | None = None
