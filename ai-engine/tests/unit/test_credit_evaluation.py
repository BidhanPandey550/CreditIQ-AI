"""Tests for the Credit Intelligence evaluation engine."""

import numpy as np
import pytest

from creditiq_ai.credit_intelligence.evaluation import CreditModelEvaluator, EvaluationConfig
from creditiq_ai.exceptions import ValidationError


def test_evaluator_computes_complete_probability_report() -> None:
    labels = [0, 0, 0, 1, 1, 1]
    probabilities = [0.05, 0.20, 0.40, 0.60, 0.80, 0.95]

    report = CreditModelEvaluator(
        EvaluationConfig(decision_threshold=0.5, calibration_bins=3)
    ).evaluate(labels, probabilities, model_name="logistic_regression", model_version="1.2.0")

    assert report.accuracy == 1.0
    assert report.roc_auc == 1.0
    assert report.pr_auc == 1.0
    assert report.confusion_matrix == [[3, 0], [0, 3]]
    assert report.sample_count == 6
    assert report.positive_count == 3
    assert report.model_version == "1.2.0"
    assert report.calibration_curve
    assert report.model_dump(mode="json")["evaluated_at"]


def test_evaluator_uses_configured_threshold() -> None:
    evaluator = CreditModelEvaluator(EvaluationConfig(decision_threshold=0.8, calibration_bins=2))
    report = evaluator.evaluate([0, 0, 1, 1], [0.1, 0.7, 0.75, 0.9], model_name="candidate")
    assert report.threshold == 0.8
    assert report.confusion_matrix == [[2, 0], [1, 1]]


@pytest.mark.parametrize(
    ("labels", "probabilities"),
    [
        ([], []),
        ([0, 1], [0.2]),
        ([0, 2], [0.2, 0.8]),
        ([0, 1], [0.2, 1.1]),
        ([0, 1], [0.2, np.nan]),
        ([[0], [1]], [[0.2], [0.8]]),
    ],
)
def test_evaluator_rejects_invalid_inputs(labels: list, probabilities: list) -> None:
    with pytest.raises(ValidationError):
        CreditModelEvaluator().evaluate(labels, probabilities, model_name="invalid")


def test_evaluator_requires_both_classes() -> None:
    with pytest.raises(ValidationError, match="both target classes"):
        CreditModelEvaluator().evaluate([0, 0, 0], [0.1, 0.2, 0.3], model_name="invalid")
