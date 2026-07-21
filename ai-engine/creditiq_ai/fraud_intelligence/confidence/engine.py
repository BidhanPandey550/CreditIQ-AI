"""Weighted reliability estimate for a fraud assessment."""

from creditiq_ai.config.models import FraudConfidenceConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import ConfigurationError
from creditiq_ai.fraud_intelligence.confidence.models import FraudConfidence, FraudConfidenceInputs


class FraudConfidenceEngine(BaseComponent):
    COMPONENTS = frozenset(
        {
            "detector_agreement",
            "data_completeness",
            "feature_quality",
            "score_stability",
            "rule_agreement",
        }
    )

    def __init__(self, config: FraudConfidenceConfig) -> None:
        super().__init__()
        self.confidence_config = config
        if set(config.weights) != self.COMPONENTS or any(
            value < 0.0 for value in config.weights.values()
        ):
            raise ConfigurationError(
                "Fraud confidence must define all non-negative component weights"
            )
        if sum(config.weights.values()) <= 0.0 or not config.levels:
            raise ConfigurationError("Fraud confidence weights and levels must not be empty")

    def assess(self, inputs: FraudConfidenceInputs) -> FraudConfidence:
        components = inputs.model_dump()
        weights = self.confidence_config.weights
        score = sum(components[name] * weights[name] for name in self.COMPONENTS) / sum(
            weights.values()
        )
        eligible = [
            (name, threshold)
            for name, threshold in self.confidence_config.levels.items()
            if score >= threshold
        ]
        level = (
            max(eligible, key=lambda item: item[1])[0]
            if eligible
            else min(
                self.confidence_config.levels, key=lambda name: self.confidence_config.levels[name]
            )
        )
        return FraudConfidence(
            score=round(score, 4),
            level=level,
            reliability_explanation=f"fraud_assessment_reliability_{level}",
            components={name: round(value, 4) for name, value in components.items()},
        )
