"""BaseFraudDetector — Template Method for every unsupervised fraud detector.

Purpose:  Fix the invariant detector workflow (fit reference → calibrate a [0,1] anomaly scale →
          score/flag → persist) so heterogeneous scikit-learn detectors expose ONE comparable
          interface. Subclasses provide only their model + raw anomaly signal.
Inputs:   feature matrix (DataFrame / ndarray) of a reference population, then new rows to score.
Outputs:  normalized anomaly scores in [0,1] (higher = more anomalous) + boolean flags.
Deps:     numpy, joblib; core.base.BaseComponent; exceptions.
Extend:   subclass, set `detector_name`, implement `_fit_model` / `_raw_scores` / `_raw_predict`,
          then register in the factory.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

import numpy as np
import pandas as pd

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.core.types import NDArray, PathLike
from creditiq_ai.exceptions import FraudDetectionError, ModelNotFittedError
from creditiq_ai.model_operations.domain import ModelArtifact
from creditiq_ai.model_operations.storage.artifacts import ArtifactStore


class BaseFraudDetector(BaseComponent):
    """One anomaly detector behind a normalized, comparable interface."""

    detector_name: str = "base"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(name=self.detector_name)
        self.params = params or {}
        self._model: Any = None
        self._score_min: float = 0.0
        self._score_max: float = 1.0
        self._fitted = False

    # ---- Template Method ----
    def fit(self, X: pd.DataFrame | NDArray) -> "BaseFraudDetector":
        data = self._as_array(X)
        try:
            self._model = self._fit_model(data)
            reference = self._raw_scores(data)
        except Exception as exc:  # noqa: BLE001
            raise FraudDetectionError(
                f"{self.detector_name} failed to fit", context={"error": str(exc)}
            ) from exc
        # Calibrate the [0,1] scale from the reference distribution (no hardcoded bounds).
        self._score_min = float(np.min(reference))
        self._score_max = float(np.max(reference))
        self._fitted = True
        self.logger.info(f"Fitted {self.detector_name} on {len(data)} reference rows")
        return self

    def score(self, X: pd.DataFrame | NDArray) -> NDArray:
        """Normalized anomaly score in [0,1] (higher = more anomalous)."""
        self._check_fitted()
        raw = self._raw_scores(self._as_array(X))
        span = self._score_max - self._score_min
        if span <= 0:
            return np.full(len(raw), 0.5)
        return np.clip((raw - self._score_min) / span, 0.0, 1.0)

    def predict(self, X: pd.DataFrame | NDArray) -> NDArray:
        """Boolean anomaly flag per row."""
        self._check_fitted()
        return self._raw_predict(self._as_array(X)).astype(bool)

    # ---- Hooks (subclass) ----
    @abstractmethod
    def _fit_model(self, X: NDArray) -> Any: ...

    @abstractmethod
    def _raw_scores(self, X: NDArray) -> NDArray:
        """Raw anomaly signal, HIGHER = MORE ANOMALOUS (subclasses flip sklearn's convention)."""

    @abstractmethod
    def _raw_predict(self, X: NDArray) -> NDArray:
        """Return an int/bool array where True/1 = anomaly."""

    # ---- Shared ----
    @staticmethod
    def _as_array(X: pd.DataFrame | NDArray) -> NDArray:
        return (
            X.to_numpy(dtype=float) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
        )

    def save(self, path: PathLike) -> ModelArtifact:
        """Persist this detector and return integrity metadata required for safe loading."""
        self._check_fitted()
        payload = {
            "detector": self.detector_name,
            "params": self.params,
            "model": self._model,
            "score_min": self._score_min,
            "score_max": self._score_max,
        }
        return ArtifactStore().save(payload, path)

    @classmethod
    def load(cls, path: PathLike, expected_sha256: str | None = None) -> "BaseFraudDetector":
        """Load only after verifying the caller-supplied trusted SHA-256 checksum."""
        payload = ArtifactStore().load(path, expected_sha256 or "")
        det = cls(payload["params"])
        det._model = payload["model"]
        det._score_min = payload["score_min"]
        det._score_max = payload["score_max"]
        det._fitted = True
        return det

    @classmethod
    def load_artifact(cls, artifact: ModelArtifact) -> "BaseFraudDetector":
        """Load from a registry artifact record carrying trusted integrity metadata."""
        return cls.load(artifact.path, artifact.checksum_sha256)

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise ModelNotFittedError(f"{self.detector_name} detector is not fitted")
