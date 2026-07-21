"""Fraud integration contract — the stable result schema consumed by the Credit Intelligence
Engine and future APIs.

Purpose:  ONE typed fraud result, populated progressively across Sprint-5 modules. Module 1
          (detectors) fills the detector-level fields + a provisional probability + the ensemble
          anomaly flag; scoring / confidence / rules / explanation modules enrich the rest.
Deps:     pydantic v2.
Note:     later-module fields are Optional/defaulted so the schema stays backward-compatible as
          the engine grows.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FraudDetectionResult(BaseModel):
    # --- filled by the detection framework (Module 1) ---
    fraud_probability: float = Field(ge=0.0, le=1.0, description="Ensemble anomaly probability")
    anomaly_detected: bool = False
    detector_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Per-detector normalized anomaly score [0,1]"
    )
    detector_agreement: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Fraction of detectors that flagged the row"
    )

    # --- filled by later modules (scoring / confidence / rules / explanation) ---
    fraud_score: int | None = Field(default=None, ge=0, le=100)  # scoring engine
    fraud_level: str | None = None  # scoring engine
    recommended_action: str | None = None  # scoring engine
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)  # confidence engine
    confidence_level: str | None = None  # confidence engine
    risk_flags: list[str] = Field(default_factory=list)  # rule engine
    explanations: list[str] = Field(default_factory=list)  # explanation engine
