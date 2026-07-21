"""CatBoost credit-risk trainer with an optional, lazily imported dependency."""

from __future__ import annotations

from importlib.util import find_spec
from typing import Any

from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.credit_intelligence.trainers.registry import register
from creditiq_ai.exceptions import ModelTrainingError


@register("catboost")
class CatBoostTrainer(BaseTrainer):
    algorithm = "catboost"

    @classmethod
    def dependency_available(cls) -> bool:
        return find_spec("catboost") is not None

    def _build_estimator(self, params: dict[str, Any]) -> Any:
        try:
            from catboost import CatBoostClassifier
        except ImportError as exc:
            raise ModelTrainingError("CatBoost requires the 'modeling' Poetry extra") from exc
        options = {"random_seed": self.train_config.random_seed, "verbose": False, **params}
        return CatBoostClassifier(**options)
