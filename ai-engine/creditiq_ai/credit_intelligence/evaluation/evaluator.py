"""Central binary credit-model evaluator.

The evaluator consumes labels and positive-class probabilities rather than a concrete estimator,
which keeps it reusable across scikit-learn, XGBoost, LightGBM, CatBoost, and remote inference.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.credit_intelligence.evaluation.models import (
    CalibrationPoint,
    CreditEvaluationReport,
    EvaluationConfig,
)
from creditiq_ai.exceptions import ValidationError


class CreditModelEvaluator(BaseComponent):
    """Evaluate binary default probabilities using one consistent metric policy."""

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        super().__init__()
        self.evaluation_config = config or EvaluationConfig()

    def evaluate(
        self,
        y_true: Sequence[int] | np.ndarray[Any, Any],
        probabilities: Sequence[float] | np.ndarray[Any, Any],
        *,
        model_name: str,
        model_version: str | None = None,
    ) -> CreditEvaluationReport:
        labels, scores = self._validate_inputs(y_true, probabilities)
        predictions = (scores >= self.evaluation_config.decision_threshold).astype(int)
        warnings: list[str] = []

        if np.unique(labels).size != 2:
            raise ValidationError("Evaluation requires both target classes")

        fraction_positive, mean_predicted = calibration_curve(
            labels,
            scores,
            n_bins=self.evaluation_config.calibration_bins,
            strategy="quantile",
        )
        points = [
            CalibrationPoint(
                predicted_probability=float(predicted), observed_frequency=float(observed)
            )
            for predicted, observed in zip(mean_predicted, fraction_positive, strict=True)
        ]

        report = CreditEvaluationReport(
            model_name=model_name,
            model_version=model_version,
            sample_count=int(labels.size),
            positive_count=int(np.sum(labels == self.evaluation_config.positive_label)),
            threshold=self.evaluation_config.decision_threshold,
            accuracy=float(accuracy_score(labels, predictions)),
            precision=float(
                precision_score(
                    labels,
                    predictions,
                    pos_label=self.evaluation_config.positive_label,
                    zero_division=self.evaluation_config.zero_division,
                )
            ),
            recall=float(
                recall_score(
                    labels,
                    predictions,
                    pos_label=self.evaluation_config.positive_label,
                    zero_division=self.evaluation_config.zero_division,
                )
            ),
            f1=float(
                f1_score(
                    labels,
                    predictions,
                    pos_label=self.evaluation_config.positive_label,
                    zero_division=self.evaluation_config.zero_division,
                )
            ),
            roc_auc=float(roc_auc_score(labels, scores)),
            pr_auc=float(average_precision_score(labels, scores)),
            log_loss=float(log_loss(labels, scores, labels=[0, 1])),
            brier_score=float(brier_score_loss(labels, scores)),
            matthews_correlation=float(matthews_corrcoef(labels, predictions)),
            balanced_accuracy=float(balanced_accuracy_score(labels, predictions)),
            confusion_matrix=confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
            classification_report=classification_report(
                labels,
                predictions,
                labels=[0, 1],
                output_dict=True,
                zero_division=self.evaluation_config.zero_division,
            ),
            calibration_curve=points,
            warnings=warnings,
        )
        self.logger.info(
            "Evaluated {} v{} | samples={} roc_auc={:.4f} pr_auc={:.4f} brier={:.4f}",
            model_name,
            model_version or "unversioned",
            labels.size,
            report.roc_auc,
            report.pr_auc,
            report.brier_score,
        )
        return report

    @staticmethod
    def _validate_inputs(
        y_true: Sequence[int] | np.ndarray[Any, Any],
        probabilities: Sequence[float] | np.ndarray[Any, Any],
    ) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
        labels = np.asarray(y_true)
        scores = np.asarray(probabilities, dtype=float)
        if labels.ndim != 1 or scores.ndim != 1:
            raise ValidationError("Labels and probabilities must be one-dimensional")
        if labels.size == 0:
            raise ValidationError("Cannot evaluate an empty dataset")
        if labels.size != scores.size:
            raise ValidationError("Labels and probabilities must have equal length")
        if not np.isfinite(scores).all() or ((scores < 0.0) | (scores > 1.0)).any():
            raise ValidationError("Probabilities must be finite values in the [0, 1] interval")
        if not np.isin(labels, [0, 1]).all():
            raise ValidationError("Labels must be binary values 0 or 1")
        return labels.astype(int), scores
