"""XGBoost credit-risk trainer with an optional, lazily imported dependency."""

from __future__ import annotations

from importlib.util import find_spec
from typing import Any

from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.credit_intelligence.trainers.registry import register
from creditiq_ai.exceptions import ModelTrainingError


@register("xgboost")
class XGBoostTrainer(BaseTrainer):
    algorithm = "xgboost"

    @classmethod
    def dependency_available(cls) -> bool:
        return find_spec("xgboost") is not None

    def _build_estimator(self, params: dict[str, Any]) -> Any:
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise ModelTrainingError("XGBoost requires the 'modeling' Poetry extra") from exc
        options = {
            "random_state": self.train_config.random_seed,
            "n_jobs": -1,
            "eval_metric": "logloss",
            **params,
        }
        return XGBClassifier(**options)
