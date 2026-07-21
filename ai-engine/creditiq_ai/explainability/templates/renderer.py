"""Narrative renderer — turns feature contributions into plain-language text from config templates.

Purpose:  Produce business-friendly explanation sentences WITHOUT any hardcoded text. All phrasing
          and human-readable feature labels come from ExplainabilityConfig (config/base.yaml).
Inputs:   ExplainabilityConfig + contributions.
Outputs:  narrative + confidence strings.
Deps:     core.schemas.FeatureContribution; config.models.ExplainabilityConfig.
Extend:   edit templates/labels in config — no code change.
"""

from __future__ import annotations

from creditiq_ai.config.models import ExplainabilityConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.core.schemas import FeatureContribution


class NarrativeRenderer(BaseComponent):
    def __init__(self, config: ExplainabilityConfig) -> None:
        super().__init__()
        self._labels = config.feature_labels
        self._templates = config.templates

    def label(self, feature: str) -> str:
        return self._labels.get(feature, feature.replace("_", " "))

    @staticmethod
    def _fmt(value: float) -> str:
        return f"{value:.3g}"

    def render(
        self,
        prediction: float,
        positives: list[FeatureContribution],
        negatives: list[FeatureContribution],
    ) -> str:
        parts = [self._templates["summary"].format(probability=f"{prediction:.0%}")]
        for c in positives:
            parts.append(
                self._templates["increases"].format(
                    label=self.label(c.feature), value=self._fmt(c.value)
                )
            )
        for c in negatives:
            parts.append(
                self._templates["decreases"].format(
                    label=self.label(c.feature), value=self._fmt(c.value)
                )
            )
        return " ".join(parts)

    def confidence(self, covered: int, total: int) -> str:
        coverage = f"{(covered / total) if total else 0:.0%}"
        return self._templates["confidence"].format(covered=covered, total=total, coverage=coverage)
