"""Typed fraud confidence contracts."""

from pydantic import BaseModel, ConfigDict, Field


class FraudConfidenceInputs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    detector_agreement: float = Field(ge=0.0, le=1.0)
    data_completeness: float = Field(ge=0.0, le=1.0)
    feature_quality: float = Field(ge=0.0, le=1.0)
    score_stability: float = Field(ge=0.0, le=1.0)
    rule_agreement: float = Field(ge=0.0, le=1.0)


class FraudConfidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=1.0)
    level: str
    reliability_explanation: str
    components: dict[str, float]
