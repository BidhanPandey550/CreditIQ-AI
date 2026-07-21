"""Integration coverage for the complete Credit Intelligence training path."""

import json

from creditiq_ai.credit_intelligence import (
    CreditDataset,
    CreditTrainingOrchestrator,
    OrchestrationConfig,
    TrainingConfig,
)
from tests.fixtures.synthetic import make_credit_dataset


def test_training_orchestrator_selects_champion_and_generates_reports(tmp_path) -> None:
    frame = make_credit_dataset(240)
    dataset = CreditDataset(
        X=frame.drop(columns=["applicant_id", "default"]), y=frame["default"], name="orchestration"
    )
    configs = [
        TrainingConfig("logistic_regression", {"max_iter": 500}, cv_folds=2),
        TrainingConfig("random_forest", {"n_estimators": 30}, cv_folds=2),
    ]
    run = CreditTrainingOrchestrator(
        configs, OrchestrationConfig(test_size=0.25, random_seed=7)
    ).run(dataset, report_directory=tmp_path)

    assert len(run.training_results) == 2
    assert len(run.evaluation_reports) == 2
    assert run.comparison.selected_model in {"logistic_regression", "random_forest"}
    assert run.champion.algorithm == run.comparison.selected_model
    assert len(run.report_artifacts) == 2
    assert run.training_dataset_version != run.holdout_dataset_version

    payload = json.loads((tmp_path / "credit-training-report.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "credit-training-report.md").read_text(encoding="utf-8")
    assert payload["summary"]["selected_model"] == run.comparison.selected_model
    assert "## Leaderboard" in markdown
