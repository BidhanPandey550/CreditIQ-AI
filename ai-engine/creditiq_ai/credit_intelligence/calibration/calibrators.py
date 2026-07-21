"""Estimator-independent Platt and isotonic probability calibration strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.credit_intelligence.calibration.models import (
    CalibrationConfig,
    CalibrationMethod,
    CalibrationReport,
)
from creditiq_ai.exceptions import ModelNotFittedError, ValidationError


class BaseProbabilityCalibrator(BaseComponent, ABC):
    """Strategy contract for fitting and applying a one-dimensional probability mapping."""

    method: CalibrationMethod

    def __init__(self, config: CalibrationConfig) -> None:
        super().__init__(name=f"{config.method}_calibrator")
        self.calibration_config = config
        self._fitted = False

    def fit(
        self, probabilities: Sequence[float] | np.ndarray[Any, Any], labels: Sequence[int]
    ) -> CalibrationReport:
        scores, targets = self._validated(probabilities, labels, require_minimum=True)
        self._fit_mapping(scores, targets)
        self._fitted = True
        calibrated = self.transform(scores)
        report = CalibrationReport(
            method=self.method,
            sample_count=int(scores.size),
            brier_before=float(brier_score_loss(targets, scores)),
            brier_after=float(brier_score_loss(targets, calibrated)),
            log_loss_before=float(log_loss(targets, scores, labels=[0, 1])),
            log_loss_after=float(log_loss(targets, calibrated, labels=[0, 1])),
            expected_calibration_error_before=self._ece(targets, scores),
            expected_calibration_error_after=self._ece(targets, calibrated),
        )
        self.logger.info(
            "Fitted {} calibration | samples={} brier={:.4f}->{:.4f}",
            self.method,
            scores.size,
            report.brier_before,
            report.brier_after,
        )
        return report

    def transform(
        self, probabilities: Sequence[float] | np.ndarray[Any, Any]
    ) -> np.ndarray[Any, Any]:
        if not self._fitted:
            raise ModelNotFittedError(f"{self.method} calibrator is not fitted")
        scores, _ = self._validated(probabilities, None, require_minimum=False)
        calibrated = self._transform_mapping(scores)
        epsilon = self.calibration_config.clip_epsilon
        return np.clip(calibrated, epsilon, 1.0 - epsilon)

    @abstractmethod
    def _fit_mapping(
        self, probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
    ) -> None:
        """Fit the strategy-specific mapping."""

    @abstractmethod
    def _transform_mapping(self, probabilities: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        """Apply the strategy-specific mapping."""

    def _validated(
        self,
        probabilities: Sequence[float] | np.ndarray[Any, Any],
        labels: Sequence[int] | None,
        *,
        require_minimum: bool,
    ) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
        scores = np.asarray(probabilities, dtype=float)
        if scores.ndim != 1 or scores.size == 0:
            raise ValidationError("Probabilities must be a non-empty one-dimensional sequence")
        if not np.isfinite(scores).all() or ((scores < 0.0) | (scores > 1.0)).any():
            raise ValidationError("Probabilities must be finite values in [0, 1]")
        targets = np.asarray([] if labels is None else labels, dtype=int)
        if labels is not None:
            if targets.ndim != 1 or targets.size != scores.size:
                raise ValidationError(
                    "Labels and probabilities must have equal one-dimensional shape"
                )
            if not np.isin(targets, [0, 1]).all() or np.unique(targets).size != 2:
                raise ValidationError("Calibration labels must contain both binary classes")
            if require_minimum and scores.size < self.calibration_config.minimum_samples:
                raise ValidationError(
                    f"Calibration requires at least {self.calibration_config.minimum_samples} samples"
                )
        return scores, targets

    def _ece(self, labels: np.ndarray[Any, Any], probabilities: np.ndarray[Any, Any]) -> float:
        edges = np.linspace(0.0, 1.0, self.calibration_config.calibration_bins + 1)
        bins = np.minimum(np.digitize(probabilities, edges[1:-1]), len(edges) - 2)
        error = 0.0
        for index in range(self.calibration_config.calibration_bins):
            mask = bins == index
            if mask.any():
                error += float(mask.mean()) * abs(
                    float(labels[mask].mean()) - float(probabilities[mask].mean())
                )
        return error


class PlattCalibrator(BaseProbabilityCalibrator):
    method = CalibrationMethod.PLATT

    def __init__(self, config: CalibrationConfig) -> None:
        super().__init__(config)
        self._model = LogisticRegression(random_state=config.random_seed)

    def _fit_mapping(
        self, probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
    ) -> None:
        self._model.fit(probabilities.reshape(-1, 1), labels)

    def _transform_mapping(self, probabilities: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return self._model.predict_proba(probabilities.reshape(-1, 1))[:, 1]


class IsotonicCalibrator(BaseProbabilityCalibrator):
    method = CalibrationMethod.ISOTONIC

    def __init__(self, config: CalibrationConfig) -> None:
        super().__init__(config)
        self._model = IsotonicRegression(out_of_bounds="clip")

    def _fit_mapping(
        self, probabilities: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
    ) -> None:
        self._model.fit(probabilities, labels)

    def _transform_mapping(self, probabilities: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.asarray(self._model.predict(probabilities), dtype=float)


class ProbabilityCalibratorFactory:
    _strategies: dict[CalibrationMethod, type[BaseProbabilityCalibrator]] = {
        CalibrationMethod.PLATT: PlattCalibrator,
        CalibrationMethod.ISOTONIC: IsotonicCalibrator,
    }

    @classmethod
    def create(cls, config: CalibrationConfig) -> BaseProbabilityCalibrator:
        return cls._strategies[config.method](config)
