"""Unified decision contracts.

Purpose:  The request + the unified credit+fraud decision result. `UnifiedDecision` includes the
          documented flat fields (backward compatible for existing clients) plus richer audit
          fields (reasons, versions, correlation ID, timing, warnings, monitoring status).
Deps:     pydantic v2, pandas (request row).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd
from pydantic import BaseModel, Field


@dataclass
class DecisionRequest:
    row: pd.DataFrame  # single applicant feature row
    correlation_id: str | None = None
    model_versions: dict[str, str] = field(default_factory=dict)
    feature_version: str | None = None


class UnifiedDecision(BaseModel):
    # --- documented flat fields (backward compatible) ---
    credit_score: int
    probability_of_default: float
    credit_risk: str
    fraud_score: int | None = None
    fraud_probability: float | None = None
    fraud_risk: str | None = None
    recommendation: str
    confidence: float

    # --- richer audit fields ---
    decision_reasons: list[str] = Field(default_factory=list)
    model_versions: dict[str, str] = Field(default_factory=dict)
    feature_version: str | None = None
    correlation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_duration_ms: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    monitoring_status: str = "ok"
