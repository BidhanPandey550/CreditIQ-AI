"""LocalExplanationService — orchestrates local explanation end-to-end.

Purpose:  Pick the best explainer (SHAP → marginal), attribute the prediction, rank the top
          positive/negative factors, render a config-driven narrative, validate completeness, and
          assemble the audit-ready LocalExplanation. If the selected explainer fails at runtime, it
          gracefully falls back to the model-agnostic marginal explainer.
Inputs:   ExplainabilityConfig + ExplanationContext + a single-row DataFrame.
Outputs:  LocalExplanation.
Deps:     explainers (factory/marginal/base), templates.renderer, validators.completeness,
          core.schemas.Explanation.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np
import pandas as pd

from creditiq_ai.config.models import ExplainabilityConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.core.schemas import Explanation
from creditiq_ai.explainability.explainers.base import ExplanationContext
from creditiq_ai.explainability.explainers.factory import ExplainerFactory
from creditiq_ai.explainability.explainers.marginal import MarginalContributionExplainer
from creditiq_ai.explainability.explainers.result import LocalExplanation
from creditiq_ai.explainability.templates.renderer import NarrativeRenderer
from creditiq_ai.explainability.validators.completeness import CompletenessValidator

# Model family → SHAP explainer kind (config-free structural fact, not a tunable threshold).
_ALGORITHM_KIND: dict[str, str] = {
    "logistic_regression": "linear",
    "random_forest": "tree",
    "xgboost": "tree",
    "lightgbm": "tree",
    "catboost": "tree",
}


def _positive_proba(trainer: Any) -> Callable[[pd.DataFrame], np.ndarray]:
    def _fn(X: pd.DataFrame) -> np.ndarray:
        out = np.asarray(trainer.predict_proba(X))
        return out[:, 1] if out.ndim == 2 else out

    return _fn


def build_context(
    trainer: Any,
    background: pd.DataFrame,
    feature_names: list[str] | None = None,
    model_version: str | None = None,
    feature_version: str | None = None,
) -> ExplanationContext:
    """Bridge a trained model (duck-typed: predict_proba + algorithm) into an ExplanationContext."""
    features = feature_names or list(background.columns)
    return ExplanationContext(
        predict_proba=_positive_proba(trainer),
        feature_names=features,
        background=background,
        model=getattr(trainer, "_estimator", None),  # read-only; for SHAP when available
        model_kind=_ALGORITHM_KIND.get(getattr(trainer, "algorithm", ""), "other"),
        model_version=model_version,
        feature_version=feature_version,
    )


class LocalExplanationService(BaseComponent):
    def __init__(
        self, config: ExplainabilityConfig, factory: type[ExplainerFactory] = ExplainerFactory
    ) -> None:
        super().__init__()
        self._cfg = config
        self._factory = factory
        self._renderer = NarrativeRenderer(config)

    def explain(self, ctx: ExplanationContext, row: pd.DataFrame) -> LocalExplanation:
        started = time.perf_counter()
        explainer = self._factory.select(ctx)
        method = explainer.method
        try:
            raw = explainer.explain(ctx, row)
        except Exception as exc:  # noqa: BLE001  — graceful fallback
            self.logger.warning(f"{method} explainer failed ({exc}); falling back to marginal")
            fallback = MarginalContributionExplainer()
            raw = fallback.explain(ctx, row)
            method = f"{fallback.method} (fallback)"

        by_impact = sorted(raw.contributions, key=lambda c: abs(c.contribution), reverse=True)
        top_k = self._cfg.top_k
        positives = [c for c in by_impact if c.contribution > 0][:top_k]
        negatives = [c for c in by_impact if c.contribution < 0][:top_k]

        narrative = self._renderer.render(raw.prediction, positives, negatives)
        validation = CompletenessValidator(
            ctx.feature_names, self._cfg.consistency_tolerance
        ).validate(raw)
        confidence = self._renderer.confidence(
            covered=len({c.feature for c in raw.contributions}), total=len(ctx.feature_names)
        )

        explanation = Explanation(
            base_value=raw.base_value,
            prediction=raw.prediction,
            top_contributors=by_impact[:top_k],
            positive_contributors=positives,
            negative_contributors=negatives,
            narrative=narrative,
        )

        self.logger.info(
            f"Local explanation via {method} | {len(raw.contributions)} features "
            f"| complete={validation.complete} | {time.perf_counter() - started:.3f}s"
        )
        return LocalExplanation(
            explanation=explanation,
            method=method,
            confidence_explanation=confidence,
            complete=validation.complete,
            issues=validation.issues,
            model_version=ctx.model_version,
            feature_version=ctx.feature_version,
        )
