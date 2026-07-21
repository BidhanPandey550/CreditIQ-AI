"""Contract tests for optional production model trainers."""

import pytest

from creditiq_ai.credit_intelligence import TrainingConfig, TrainingFactory
from creditiq_ai.credit_intelligence.algorithms.catboost import CatBoostTrainer
from creditiq_ai.credit_intelligence.algorithms.lightgbm import LightGBMTrainer
from creditiq_ai.credit_intelligence.algorithms.xgboost import XGBoostTrainer


@pytest.mark.parametrize(
    ("algorithm", "trainer_type"),
    [
        ("xgboost", XGBoostTrainer),
        ("lightgbm", LightGBMTrainer),
        ("catboost", CatBoostTrainer),
    ],
)
def test_optional_trainer_registration_and_availability(algorithm, trainer_type) -> None:
    trainer = TrainingFactory.create(TrainingConfig(algorithm=algorithm))
    assert isinstance(trainer, trainer_type)
    assert TrainingFactory.supports(algorithm) is trainer_type.dependency_available()


@pytest.mark.parametrize("algorithm", ["logistic_regression", "random_forest"])
def test_core_trainers_are_always_supported(algorithm) -> None:
    assert TrainingFactory.supports(algorithm)
