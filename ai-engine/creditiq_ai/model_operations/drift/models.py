"""Typed feature and dataset drift results."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class FeatureDrift(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    feature: str
    psi: float = Field(ge=0.0)
    status: str
    reference_count: int = Field(ge=0)
    current_count: int = Field(ge=0)


class DriftReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    features: list[FeatureDrift]
    drifted_features: list[str]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
