"""FraudDetectionPipeline — fit an ensemble of detectors and analyse new rows.

Purpose:  Orchestrate the configured detectors: fit them on a reference population, then score
          new applicants and aggregate per-row into the FraudDetectionResult contract (ensemble
          probability + agreement + anomaly flag via the configured vote threshold). Unregistered
          detectors are skipped with a warning so config stays forward-compatible.
Inputs:   FraudConfig (EngineConfig.fraud) + feature matrices.
Outputs:  list[FraudDetectionResult] (detector-level fields; later modules enrich the rest).
Deps:     detectors.factory / .result; config.models.FraudConfig; numpy.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from creditiq_ai.config.models import FraudConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.core.types import NDArray
from creditiq_ai.exceptions import FraudDetectionError
from creditiq_ai.fraud.detectors.base import BaseFraudDetector
from creditiq_ai.fraud.detectors.factory import FraudDetectionFactory
from creditiq_ai.fraud.detectors.result import FraudDetectionResult


class FraudDetectionPipeline(BaseComponent):
    """Ensemble of unsupervised detectors with configurable vote-based flagging."""

    def __init__(
        self, config: FraudConfig, factory: type[FraudDetectionFactory] = FraudDetectionFactory
    ) -> None:
        super().__init__()
        self._config = config
        self._vote_threshold = config.vote_threshold
        self._detectors: list[BaseFraudDetector] = []
        for spec in config.detectors:
            if not spec.enabled:
                continue
            if not factory.supports(spec.type):
                self.logger.warning(f"Skipping '{spec.type}' — no detector registered")
                continue
            self._detectors.append(factory.create(spec.type, spec.params))
        self._fitted = False

    @property
    def detector_names(self) -> list[str]:
        return [d.detector_name for d in self._detectors]

    def fit(self, X_reference: pd.DataFrame | NDArray) -> "FraudDetectionPipeline":
        if not self._detectors:
            raise FraudDetectionError("No registered detectors enabled in config")
        for detector in self._detectors:
            detector.fit(X_reference)
        self._fitted = True
        return self

    def analyze(self, X: pd.DataFrame | NDArray) -> list[FraudDetectionResult]:
        if not self._fitted:
            raise FraudDetectionError("FraudDetectionPipeline must be fitted before analyze()")
        started = time.perf_counter()

        n = len(X)
        scores = {d.detector_name: d.score(X) for d in self._detectors}
        flags = {d.detector_name: d.predict(X) for d in self._detectors}
        n_detectors = len(self._detectors)

        results: list[FraudDetectionResult] = []
        for i in range(n):
            breakdown = {name: round(float(scores[name][i]), 4) for name in scores}
            votes = int(sum(bool(flags[name][i]) for name in flags))
            results.append(
                FraudDetectionResult(
                    fraud_probability=round(float(np.mean(list(breakdown.values()))), 4),
                    anomaly_detected=votes >= self._vote_threshold,
                    detector_breakdown=breakdown,
                    detector_agreement=round(votes / n_detectors, 4),
                )
            )

        flagged = sum(r.anomaly_detected for r in results)
        self.logger.info(
            f"Fraud analysis: {n} row(s), {n_detectors} detector(s), {flagged} flagged "
            f"in {time.perf_counter() - started:.3f}s"
        )
        return results
