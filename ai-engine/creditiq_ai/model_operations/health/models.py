"""Unified model health result."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class ModelHealthReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    operational_status: str
    drift_status: str | None = None
    performance_status: str | None = None
    reasons: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
