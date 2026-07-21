"""Serializable contracts for credit model evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationConfig(BaseModel):
    """Threshold and calibration settings injected into the evaluator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_threshold: float = Field(default=0.5, gt=0.0, lt=1.0)
    calibration_bins: int = Field(default=10, ge=2)
    positive_label: int = 1
    zero_division: int = Field(default=0, ge=0, le=1)


class CalibrationPoint(BaseModel):
    predicted_probability: float
    observed_frequency: float


class CreditEvaluationReport(BaseModel):
    """Machine-readable evaluation result for a binary probability model."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    model_version: str | None = None
    sample_count: int = Field(gt=0)
    positive_count: int = Field(ge=0)
    threshold: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    log_loss: float
    brier_score: float
    matthews_correlation: float
    balanced_accuracy: float
    confusion_matrix: list[list[int]]
    classification_report: dict[str, object]
    calibration_curve: list[CalibrationPoint]
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_confusion_matrix(self) -> "CreditEvaluationReport":
        if len(self.confusion_matrix) != 2 or any(len(row) != 2 for row in self.confusion_matrix):
            raise ValueError("confusion_matrix must be 2x2")
        return self
