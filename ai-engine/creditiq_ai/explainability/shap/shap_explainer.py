"""SHAP-based local explainer (preferred when available).

Purpose:  Exact/near-exact additive attributions via SHAP for tree and linear models. Registered
          at high priority; `supports()` returns False when SHAP is not installed or the model is
          unsupported, so the factory falls back to a model-appropriate strategy (Marginal).
Inputs:   ExplanationContext (with the raw estimator + model_kind) + a single-row DataFrame.
Outputs:  RawContributions.
Deps:     shap (optional — imported lazily), numpy; core.schemas.FeatureContribution.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from creditiq_ai.core.schemas import FeatureContribution
from creditiq_ai.exceptions import ExplainabilityError
from creditiq_ai.explainability.explainers.base import (
    BaseLocalExplainer,
    ExplanationContext,
    RawContributions,
)
from creditiq_ai.explainability.explainers.registry import register

_SUPPORTED_KINDS = {"tree", "linear"}


def _shap_available() -> bool:
    try:
        import shap  # noqa: F401

        return True
    except Exception:  # pragma: no cover - env dependent
        return False


@register("shap", priority=100)
class ShapExplainer(BaseLocalExplainer):
    method = "shap"

    def supports(self, ctx: ExplanationContext) -> bool:
        return ctx.model is not None and ctx.model_kind in _SUPPORTED_KINDS and _shap_available()

    def explain(self, ctx: ExplanationContext, row: pd.DataFrame) -> RawContributions:
        import shap

        X = row[ctx.feature_names]
        try:
            if ctx.model_kind == "tree":
                explainer = shap.TreeExplainer(ctx.model)
            else:
                explainer = shap.LinearExplainer(ctx.model, ctx.background[ctx.feature_names])
            values = explainer.shap_values(X)
            base = explainer.expected_value
        except Exception as exc:  # noqa: BLE001
            raise ExplainabilityError(
                "SHAP explanation failed", context={"error": str(exc)}
            ) from exc

        row_values = self._positive_class(np.asarray(values, dtype=object))
        base_value = self._scalar_base(base)
        prediction = float(ctx.predict_proba(X)[0])

        contributions = [
            FeatureContribution(
                feature=f, value=float(X[f].iloc[0]), contribution=round(float(row_values[i]), 6)
            )
            for i, f in enumerate(ctx.feature_names)
        ]
        return RawContributions(
            base_value=round(base_value, 6),
            prediction=round(prediction, 6),
            contributions=contributions,
        )

    @staticmethod
    def _positive_class(values) -> np.ndarray:
        """Normalise the many SHAP output shapes down to a 1-D per-feature vector (positive class)."""
        arr = values
        if isinstance(arr, list):  # [class0, class1]
            arr = arr[1]
        arr = np.asarray(arr, dtype=float)
        if arr.ndim == 3:  # (n, features, classes)
            arr = arr[:, :, 1]
        return arr[0]  # first (only) row

    @staticmethod
    def _scalar_base(base) -> float:
        if isinstance(base, (list, np.ndarray)):
            seq = np.asarray(base, dtype=float).ravel()
            return float(seq[1] if seq.size >= 2 else seq[0])
        return float(base)
