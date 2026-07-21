"""Explanation validators — completeness + consistency with the prediction.

Purpose:  Guard against silently-broken explanations: every feature must be attributed, the
          prediction must be a valid probability, and the net attribution direction must agree
          with prediction-vs-baseline (works for both additive SHAP and marginal explainers).
Inputs:   RawContributions + feature list + tolerance.
Outputs:  ExplanationValidation (complete flag + issues).
Deps:     explainers.base.RawContributions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from creditiq_ai.explainability.explainers.base import RawContributions


@dataclass
class ExplanationValidation:
    complete: bool
    issues: list[str] = field(default_factory=list)


class CompletenessValidator:
    def __init__(self, feature_names: list[str], tolerance: float) -> None:
        self._features = feature_names
        self._tolerance = tolerance

    def validate(self, raw: RawContributions) -> ExplanationValidation:
        issues: list[str] = []

        covered = {c.feature for c in raw.contributions}
        missing = [f for f in self._features if f not in covered]
        if missing:
            issues.append(f"Missing feature contributions: {missing}")

        if not 0.0 <= raw.prediction <= 1.0:
            issues.append(f"Prediction {raw.prediction} outside [0,1]")

        delta = raw.prediction - raw.base_value
        net = sum(c.contribution for c in raw.contributions)
        if abs(delta) > self._tolerance and abs(net) > self._tolerance and (delta > 0) != (net > 0):
            issues.append("Net contribution direction inconsistent with prediction vs baseline")

        return ExplanationValidation(complete=not issues, issues=issues)
