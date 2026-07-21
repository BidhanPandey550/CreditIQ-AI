"""Stable, API-neutral enterprise inference contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.decision import UnifiedDecision
from creditiq_ai.explainability.explainers.result import LocalExplanation


@dataclass(frozen=True)
class InferenceRequest:
    """One applicant's model-ready or preprocessor-ready feature mapping."""

    features: dict[str, Any]
    correlation_id: str | None = None
    model_versions: dict[str, str] = field(default_factory=dict)
    feature_version: str | None = None
    include_explanation: bool = True


class InferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: UnifiedDecision
    explanation: LocalExplanation | None = None
    processed_features: list[str] = Field(default_factory=list)
    schema_version: str = "1.0"
