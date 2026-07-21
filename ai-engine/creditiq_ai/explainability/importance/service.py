"""Model-agnostic global permutation importance over predicted default probabilities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from creditiq_ai.config.models import ExplainabilityConfig
from creditiq_ai.explainability.explainers.base import ExplanationContext
from creditiq_ai.explainability.importance.models import GlobalImportanceReport, ImportanceItem


class GlobalImportanceService:
    def __init__(self, config: ExplainabilityConfig) -> None:
        self.config = config

    def analyze(self, context: ExplanationContext, data: pd.DataFrame) -> GlobalImportanceReport:
        sample = data[context.feature_names].head(self.config.global_max_samples).copy()
        if sample.empty:
            raise ValueError("Global importance requires at least one row")
        baseline = np.asarray(context.predict_proba(sample), dtype=float)
        rng = np.random.default_rng(self.config.random_seed)
        feature_results: list[tuple[str, float, float]] = []
        for feature in context.feature_names:
            changes: list[float] = []
            original = sample[feature].to_numpy(copy=True)
            for _ in range(self.config.global_repeats):
                permuted = sample.copy()
                permuted[feature] = rng.permutation(original)
                changed = np.asarray(context.predict_proba(permuted), dtype=float)
                changes.append(float(np.mean(np.abs(baseline - changed))))
            feature_results.append((feature, float(np.mean(changes)), float(np.std(changes))))
        feature_results.sort(key=lambda item: (-item[1], item[0]))
        items = [
            ImportanceItem(
                feature=feature,
                rank=rank,
                importance=round(mean, 8),
                standard_deviation=round(std, 8),
                stability=round(1.0 / (1.0 + (std / mean if mean > 0.0 else 0.0)), 4),
            )
            for rank, (feature, mean, std) in enumerate(feature_results, start=1)
        ]
        return GlobalImportanceReport(
            method="prediction_permutation",
            features=items,
            sample_count=len(sample),
            model_version=context.model_version,
            feature_version=context.feature_version,
        )
