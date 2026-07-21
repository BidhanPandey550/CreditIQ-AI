"""Logistic Regression trainer — interpretable linear baseline for credit risk.

Purpose:  A regularised logistic model; the transparent benchmark every other model must beat.
Deps:     scikit-learn.
"""

from __future__ import annotations

from typing import Any

from creditiq_ai.credit_intelligence.trainers.base import BaseTrainer
from creditiq_ai.credit_intelligence.trainers.registry import register


@register("logistic_regression")
class LogisticRegressionTrainer(BaseTrainer):
    algorithm = "logistic_regression"

    def _build_estimator(self, params: dict[str, Any]) -> Any:
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(random_state=self.train_config.random_seed, **params)
