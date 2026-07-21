"""Random Forest trainer — non-linear bagging baseline, robust to feature scaling.

Purpose:  Captures non-linearities and interactions with minimal tuning; a strong tabular
          baseline and a source of feature-importance signals.
Deps:     scikit-learn.
"""

from __future__ import annotations

from typing import Any

from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.credit_intelligence.trainers.registry import register


@register("random_forest")
class RandomForestTrainer(BaseTrainer):
    algorithm = "random_forest"

    def _build_estimator(self, params: dict[str, Any]) -> Any:
        from sklearn.ensemble import RandomForestClassifier

        options = {"random_state": self.train_config.random_seed, "n_jobs": -1, **params}
        return RandomForestClassifier(**options)
