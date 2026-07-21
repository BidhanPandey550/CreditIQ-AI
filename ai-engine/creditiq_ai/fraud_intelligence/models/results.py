"""Fraud Intelligence core contracts.

Purpose:  Typed inputs/outputs for the fraud engine. `FraudSignals` decouples the scoring engine
          from the components that produce signals (anomaly detection, rules, behaviour) — each is
          built and tested independently, then composed by the pipeline (Dependency Inversion).
Deps:     pydantic v2.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FraudRiskLevel(str, Enum):
    """Ordinal fraud risk bands (thresholds live in config, not here)."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class FraudSignals(BaseModel):
    """Normalized [0,1] fraud signals from the pipeline stages (injected into scoring)."""

    anomaly_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    rule_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    behaviour_risk: float = Field(default=0.0, ge=0.0, le=1.0)


class FraudScore(BaseModel):
    """Output of the Fraud Scoring Engine."""

    fraud_score: int = Field(ge=0, le=1000)
    fraud_probability: float = Field(ge=0.0, le=1.0)
    fraud_risk_level: FraudRiskLevel
    recommended_action: str
    components: dict[str, float] = Field(
        default_factory=dict, description="Weighted contribution of each signal to the score"
    )
