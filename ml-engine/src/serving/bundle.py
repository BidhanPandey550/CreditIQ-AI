"""Versioned deployable bundle contract for the ML serving adapter."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.fraud import FraudDetectionPipeline


@dataclass(frozen=True)
class ServingBundle:
    """All fitted components and reference data required for deterministic inference."""

    trainer: BaseTrainer
    fraud: FraudDetectionPipeline
    reference: pd.DataFrame
    feature_version: str
    metrics: dict[str, float | int]
    schema_version: int = 1

    def validate(self) -> None:
        """Reject incomplete or incompatible artifacts before serving traffic."""
        if self.schema_version != 1:
            raise ValueError(f"Unsupported serving bundle schema: {self.schema_version}")
        if self.reference.empty:
            raise ValueError("Serving bundle reference data cannot be empty")
        if not self.feature_version.strip():
            raise ValueError("Serving bundle requires a feature version")
