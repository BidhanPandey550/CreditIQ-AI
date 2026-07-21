"""Tests for automatic multi-metric model comparison."""

import pytest

from creditiq_ai.credit_intelligence.evaluation import (
    ComparisonConfig,
    CreditModelEvaluator,
    ModelComparisonService,
)
from creditiq_ai.exceptions import ValidationError


def _report(name: str, probabilities: list[float], version: str = "1"):
    return CreditModelEvaluator().evaluate(
        [0, 0, 0, 1, 1, 1], probabilities, model_name=name, model_version=version
    )


def test_comparison_ranks_and_selects_best_model() -> None:
    strong = _report("strong", [0.05, 0.1, 0.2, 0.8, 0.9, 0.95])
    weak = _report("weak", [0.2, 0.6, 0.4, 0.55, 0.7, 0.8])
    result = ModelComparisonService().compare([weak, strong])
    assert result.selected_model == "strong"
    assert result.leaderboard[0].rank == 1
    assert result.leaderboard[0].model_name == "strong"
    assert result.leaderboard[0].composite_score >= result.leaderboard[1].composite_score


def test_eligibility_gate_excludes_higher_composite_candidate() -> None:
    accurate_but_uncalibrated = _report("ungated", [0.01, 0.01, 0.01, 0.51, 0.51, 0.51])
    eligible = _report("eligible", [0.1, 0.2, 0.3, 0.65, 0.75, 0.85])
    config = ComparisonConfig(
        metric_weights={"roc_auc": 1.0}, maximum_metrics={"brier_score": 0.12}
    )
    result = ModelComparisonService(config).compare([accurate_but_uncalibrated, eligible])
    assert result.selected_model == "eligible"
    rejected = next(entry for entry in result.leaderboard if entry.model_name == "ungated")
    assert not rejected.eligible
    assert rejected.failed_gates


def test_no_eligible_model_fails_closed() -> None:
    report = _report("candidate", [0.2, 0.3, 0.4, 0.6, 0.7, 0.8])
    service = ModelComparisonService(ComparisonConfig(minimum_metrics={"roc_auc": 1.1}))
    with pytest.raises(ValidationError, match="No model"):
        service.compare([report])


def test_empty_and_duplicate_comparisons_are_rejected() -> None:
    service = ModelComparisonService()
    with pytest.raises(ValidationError):
        service.compare([])
    report = _report("duplicate", [0.2, 0.3, 0.4, 0.6, 0.7, 0.8])
    with pytest.raises(ValidationError, match="unique"):
        service.compare([report, report])


@pytest.mark.parametrize(
    "config",
    [
        {"metric_weights": {"unknown": 1.0}},
        {"metric_weights": {"roc_auc": 0.0}},
        {"minimum_metrics": {"brier_score": 0.2}},
        {"maximum_metrics": {"roc_auc": 0.8}},
    ],
)
def test_invalid_comparison_configuration_is_rejected(config) -> None:
    with pytest.raises(ValueError):
        ComparisonConfig(**config)
