"""Marginal-contribution explainer — model-agnostic local attribution.

Purpose:  The universal fallback: attribute a prediction by ablating each feature toward its
          background baseline and measuring the change in predicted default probability. Works for
          ANY model exposing predict_proba, so an explanation is always available.
Inputs:   ExplanationContext + a single-row DataFrame.
Outputs:  RawContributions (signed: + increased default risk vs baseline).
Deps:     pandas, numpy; core.schemas.FeatureContribution.
"""

from __future__ import annotations

import pandas as pd

from creditiq_ai.core.schemas import FeatureContribution
from creditiq_ai.explainability.explainers.base import (
    BaseLocalExplainer,
    ExplanationContext,
    RawContributions,
)
from creditiq_ai.explainability.explainers.registry import register


@register("marginal", priority=10)
class MarginalContributionExplainer(BaseLocalExplainer):
    method = "marginal"

    def supports(self, ctx: ExplanationContext) -> bool:
        return len(ctx.background) > 0  # only needs predict_proba + a baseline

    def explain(self, ctx: ExplanationContext, row: pd.DataFrame) -> RawContributions:
        baseline = ctx.background[ctx.feature_names].mean().to_frame().T
        prediction = float(ctx.predict_proba(row[ctx.feature_names])[0])
        base_value = float(ctx.predict_proba(baseline)[0])

        contributions: list[FeatureContribution] = []
        for feature in ctx.feature_names:
            perturbed = row[ctx.feature_names].copy()
            perturbed[feature] = baseline[feature].iloc[0]
            pred_without = float(ctx.predict_proba(perturbed)[0])
            contributions.append(
                FeatureContribution(
                    feature=feature,
                    value=float(row[feature].iloc[0]),
                    contribution=round(prediction - pred_without, 6),
                )
            )
        return RawContributions(
            base_value=round(base_value, 6),
            prediction=round(prediction, 6),
            contributions=contributions,
        )
