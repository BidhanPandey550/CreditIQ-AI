"""Model performance monitoring contracts."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class PerformanceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str
    baseline: float
    current: float
    change: float
    status: str
    sample_count: int = Field(ge=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
