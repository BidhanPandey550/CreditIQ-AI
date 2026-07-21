"""Weighted confidence assessment for credit predictions."""

from creditiq_ai.config.models import CreditConfidenceConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.credit_intelligence.confidence.models import (
    ConfidenceAssessment,
    ConfidenceInputs,
)
from creditiq_ai.exceptions import ConfigurationError


class CreditConfidenceEngine(BaseComponent):
    REQUIRED_COMPONENTS = frozenset({"probability", "calibration", "completeness", "stability"})

    def __init__(self, config: CreditConfidenceConfig) -> None:
        super().__init__()
        self.confidence_config = config
        if set(config.weights) != self.REQUIRED_COMPONENTS or any(
            weight < 0.0 for weight in config.weights.values()
        ):
            raise ConfigurationError("Confidence weights must define all non-negative components")
        if sum(config.weights.values()) <= 0.0 or not config.levels:
            raise ConfigurationError("Confidence weights and levels cannot be empty")

    def assess(self, inputs: ConfidenceInputs) -> ConfidenceAssessment:
        components = {
            "probability": 2.0 * abs(inputs.probability_of_default - 0.5),
            "calibration": inputs.calibration_quality,
            "completeness": inputs.feature_completeness,
            "stability": inputs.prediction_stability,
        }
        weights = self.confidence_config.weights
        score = sum(components[name] * weight for name, weight in weights.items()) / sum(
            weights.values()
        )
        level = max(
            (
                (name, threshold)
                for name, threshold in self.confidence_config.levels.items()
                if score >= threshold
            ),
            key=lambda item: item[1],
            default=(
                min(
                    self.confidence_config.levels,
                    key=lambda name: self.confidence_config.levels[name],
                ),
                0.0,
            ),
        )[0]
        return ConfidenceAssessment(
            score=round(score, 4),
            level=level,
            reliability=f"prediction_reliability_{level}",
            components={name: round(value, 4) for name, value in components.items()},
        )
