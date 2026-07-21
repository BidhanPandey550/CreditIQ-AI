"""Tests for typed search spaces and Optuna optimization."""

import json

import pytest

from creditiq_ai.config import load_config
from creditiq_ai.credit_intelligence import CreditDataset
from creditiq_ai.credit_intelligence.trainers.optimization_models import (
    OptimizationConfig,
    SearchDimension,
)
from creditiq_ai.credit_intelligence.trainers.optimizer import OptunaOptimizationService
from tests.fixtures.synthetic import make_credit_dataset


def _dataset() -> CreditDataset:
    frame = make_credit_dataset(120)
    return CreditDataset(
        X=frame.drop(columns=["applicant_id", "default"]), y=frame["default"], name="optuna-test"
    )


def test_configuration_is_built_from_unified_model_zoo() -> None:
    config = OptimizationConfig.from_models(load_config().models, "logistic_regression")
    assert config.algorithm == "logistic_regression"
    assert "C" in config.search_space
    assert config.fixed_params["max_iter"] == 1000


@pytest.mark.parametrize(
    "dimension",
    [
        {"type": "int", "low": 5, "high": 5},
        {"type": "float", "low": 0.1, "high": 1.0, "log": True, "step": 0.1},
        {"type": "categorical", "choices": []},
    ],
)
def test_invalid_search_dimensions_are_rejected(dimension) -> None:
    with pytest.raises(ValueError):
        SearchDimension.model_validate(dimension)


def test_optuna_optimization_and_result_persistence(tmp_path) -> None:
    config = OptimizationConfig(
        algorithm="logistic_regression",
        fixed_params={"max_iter": 500},
        search_space={"C": SearchDimension(type="float", low=0.1, high=2.0, log=True)},
        trials=2,
        cv_folds=2,
        random_seed=7,
        pruning_startup_trials=1,
    )
    result = OptunaOptimizationService(config).optimize(_dataset())
    assert result.algorithm == "logistic_regression"
    assert len(result.trials) == 2
    assert "C" in result.best_params
    output = result.save_json(tmp_path / "best-trial.json")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["best_params"] == result.best_params


def test_unavailable_trainer_fails_before_study() -> None:
    config = OptimizationConfig(
        algorithm="not_registered",
        search_space={"x": SearchDimension(type="int", low=1, high=2)},
        trials=1,
    )
    with pytest.raises(Exception, match="unavailable"):
        OptunaOptimizationService(config).optimize(_dataset())
