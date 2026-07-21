"""Fraud Scoring Engine — combine normalized signals into a 0–1000 fraud score.

Purpose:  Turn the pipeline's fraud signals (anomaly / rules / behaviour) into a single
          configurable fraud score, risk level, and recommended action. Weights, the 0–1000 range,
          band thresholds, and actions are ALL configuration — no magic numbers in code.
Inputs:   FraudScoringConfig + FraudSignals.
Outputs:  FraudScore.
Deps:     config.models.FraudScoringConfig; core.base.BaseComponent; exceptions.
Extend:   add a signal → add a weight in config/base.yaml and a field on FraudSignals.
"""

from __future__ import annotations

from creditiq_ai.config.models import FraudScoringConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import ConfigurationError
from creditiq_ai.fraud_intelligence.models.results import (
    FraudRiskLevel,
    FraudScore,
    FraudSignals,
)


class FraudScoringEngine(BaseComponent):
    """Weighted, fully-configurable fraud scorer."""

    def __init__(self, config: FraudScoringConfig) -> None:
        super().__init__()
        self._cfg = config
        if not config.bands:
            raise ConfigurationError("Fraud scoring requires at least one score band")
        # Highest-min-score first so band resolution is a simple first-match.
        self._bands = sorted(config.bands, key=lambda b: b.min_score, reverse=True)

    def score(self, signals: FraudSignals) -> FraudScore:
        weights = self._cfg.weights
        total_weight = sum(weights.values()) or 1.0
        components = {
            "anomaly": weights.get("anomaly", 0.0) * signals.anomaly_probability,
            "rules": weights.get("rules", 0.0) * signals.rule_penalty,
            "behaviour": weights.get("behaviour", 0.0) * signals.behaviour_risk,
        }
        probability = min(1.0, max(0.0, sum(components.values()) / total_weight))

        span = self._cfg.score_max - self._cfg.score_min
        fraud_score = int(round(self._cfg.score_min + probability * span))
        level = self._band(fraud_score)
        action = self._cfg.actions.get(level.value, "review")

        self.logger.info(
            f"Fraud score={fraud_score} ({level.value}) prob={probability:.3f} action={action}"
        )
        return FraudScore(
            fraud_score=fraud_score,
            fraud_probability=round(probability, 4),
            fraud_risk_level=level,
            recommended_action=action,
            components={k: round(v, 4) for k, v in components.items()},
        )

    def _band(self, score: int) -> FraudRiskLevel:
        for band in self._bands:
            if score >= band.min_score:
                return FraudRiskLevel(band.level)
        return FraudRiskLevel(self._bands[-1].level)
