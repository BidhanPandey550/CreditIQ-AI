"""Typed contracts for inference monitoring and health snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InferenceEvent(BaseModel):
    """One privacy-safe operational event; raw applicant features are deliberately excluded."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    correlation_id: str
    success: bool
    duration_ms: float = Field(ge=0.0)
    recommendation: str | None = None
    model_versions: dict[str, str] = Field(default_factory=dict)
    warning_codes: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_utcnow)


class MonitoringSnapshot(BaseModel):
    """Aggregate operational state over the monitor's bounded retention window."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prediction_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    failure_rate: float = Field(ge=0.0, le=1.0)
    average_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)
    status: str
    reasons: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utcnow)


@runtime_checkable
class MonitoringSink(Protocol):
    """Dependency-injection boundary used by inference and decision services."""

    def record(self, event: InferenceEvent) -> None:
        """Record one event or raise when the monitoring backend is unavailable."""
