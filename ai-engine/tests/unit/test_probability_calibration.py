"""Tests for Platt and isotonic probability calibration."""

import numpy as np
import pytest

from creditiq_ai.credit_intelligence.calibration import (
    CalibrationConfig,
    CalibrationMethod,
    IsotonicCalibrator,
    PlattCalibrator,
    ProbabilityCalibratorFactory,
)
from creditiq_ai.exceptions import ModelNotFittedError, ValidationError


def _data() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    raw = np.linspace(0.05, 0.95, 200)
    labels = rng.binomial(1, np.sqrt(raw))
    return raw, labels


@pytest.mark.parametrize(
    ("method", "expected_type"),
    [(CalibrationMethod.PLATT, PlattCalibrator), (CalibrationMethod.ISOTONIC, IsotonicCalibrator)],
)
def test_factory_builds_and_calibrator_returns_report(method, expected_type) -> None:
    scores, labels = _data()
    calibrator = ProbabilityCalibratorFactory.create(
        CalibrationConfig(method=method, minimum_samples=30, calibration_bins=8)
    )
    assert isinstance(calibrator, expected_type)
    report = calibrator.fit(scores, labels)
    transformed = calibrator.transform(scores)
    assert report.method == method
    assert report.sample_count == 200
    assert np.isfinite(report.brier_improvement)
    assert transformed.shape == scores.shape
    assert ((transformed > 0.0) & (transformed < 1.0)).all()


def test_transform_before_fit_fails() -> None:
    calibrator = PlattCalibrator(CalibrationConfig())
    with pytest.raises(ModelNotFittedError):
        calibrator.transform([0.2, 0.8])


@pytest.mark.parametrize(
    ("scores", "labels"),
    [([], []), ([0.2, 1.2], [0, 1]), ([0.2, 0.8], [0]), ([0.2, 0.8], [1, 1])],
)
def test_invalid_calibration_data_fails(scores, labels) -> None:
    calibrator = PlattCalibrator(CalibrationConfig(minimum_samples=4))
    with pytest.raises(ValidationError):
        calibrator.fit(scores, labels)


def test_minimum_sample_policy_is_enforced() -> None:
    calibrator = IsotonicCalibrator(CalibrationConfig(minimum_samples=10))
    with pytest.raises(ValidationError, match="at least 10"):
        calibrator.fit([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1])
