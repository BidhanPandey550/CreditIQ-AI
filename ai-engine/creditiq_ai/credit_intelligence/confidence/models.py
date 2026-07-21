"""Typed confidence inputs and assessment."""

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceInputs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    probability_of_default: float = Field(ge=0.0, le=1.0)
    calibration_quality: float = Field(ge=0.0, le=1.0)
    feature_completeness: float = Field(ge=0.0, le=1.0)
    prediction_stability: float = Field(ge=0.0, le=1.0)


class ConfidenceAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=1.0)
    level: str
    reliability: str
    components: dict[str, float]
