"""One-feature-at-a-time constrained counterfactual search."""

from __future__ import annotations

import pandas as pd

from creditiq_ai.config.models import ExplainabilityConfig
from creditiq_ai.explainability.counterfactual.models import (
    CounterfactualResult,
    CounterfactualSuggestion,
)
from creditiq_ai.explainability.explainers.base import ExplanationContext


class CounterfactualService:
    def __init__(self, config: ExplainabilityConfig) -> None:
        self.config = config

    def generate(self, context: ExplanationContext, row: pd.DataFrame) -> CounterfactualResult:
        if len(row) != 1:
            raise ValueError("Counterfactual generation requires exactly one row")
        original = float(context.predict_proba(row[context.feature_names])[0])
        target = self.config.counterfactual_target_probability
        suggestions: list[CounterfactualSuggestion] = []
        for feature, policy in self.config.counterfactual_features.items():
            if feature not in row.columns or pd.isna(row[feature].iloc[0]):
                continue
            current = float(row[feature].iloc[0])
            candidate = current
            best_probability = original
            best_value = current
            direction = 1.0 if policy["direction"] == "increase" else -1.0
            step = float(policy["step"]) * direction
            minimum, maximum = float(policy["minimum"]), float(policy["maximum"])
            max_steps = int(abs((maximum - minimum) / step)) if step != 0.0 else 0
            for _ in range(max_steps):
                candidate = min(maximum, max(minimum, candidate + step))
                changed = row.copy()
                changed.loc[changed.index[0], feature] = candidate
                probability = float(context.predict_proba(changed[context.feature_names])[0])
                if probability < best_probability:
                    best_probability, best_value = probability, candidate
                if probability <= target or candidate in (minimum, maximum):
                    break
            if best_probability < original:
                suggestions.append(
                    CounterfactualSuggestion(
                        feature=feature,
                        current_value=current,
                        suggested_value=round(best_value, 4),
                        resulting_probability=round(best_probability, 4),
                        target_reached=best_probability <= target,
                        guidance=str(policy["template"]).format(value=round(best_value, 4)),
                    )
                )
        suggestions.sort(key=lambda item: (item.resulting_probability, item.feature))
        return CounterfactualResult(
            original_probability=round(original, 4),
            target_probability=target,
            suggestions=suggestions,
        )
