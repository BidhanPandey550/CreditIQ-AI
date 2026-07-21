"""Typed probability-calibration configuration and quality report."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CalibrationMethod(StrEnum):
    PLATT = "platt"
    ISOTONIC = "isotonic"


class CalibrationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method: CalibrationMethod = CalibrationMethod.PLATT
    clip_epsilon: float = Field(default=1e-6, gt=0.0, lt=0.5)
    calibration_bins: int = Field(default=10, ge=2)
    minimum_samples: int = Field(default=30, ge=4)
    random_seed: int = 42


class CalibrationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: CalibrationMethod
    sample_count: int
    brier_before: float
    brier_after: float
    log_loss_before: float
    log_loss_after: float
    expected_calibration_error_before: float
    expected_calibration_error_after: float

    @property
    def brier_improvement(self) -> float:
        return self.brier_before - self.brier_after
