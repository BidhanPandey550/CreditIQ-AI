"""Tests for Sprint 7 Module 1 — Fraud Intelligence config + Fraud Scoring Engine."""

import pytest

from creditiq_ai.config import load_config
from creditiq_ai.config.models import FraudScoreBand, FraudScoringConfig
from creditiq_ai.exceptions import ConfigurationError
from creditiq_ai.fraud_intelligence import (
    FraudRiskLevel,
    FraudScoringEngine,
    FraudSignals,
)


def _engine() -> FraudScoringEngine:
    return FraudScoringEngine(load_config().fraud_intelligence.scoring)


# --------------------------------------------------------------------------- config
def test_config_exposes_fraud_intelligence_scoring():
    scoring = load_config().fraud_intelligence.scoring
    assert scoring.score_max == 1000
    assert {"anomaly", "rules", "behaviour"} <= set(scoring.weights)
    assert len(scoring.bands) == 5


# --------------------------------------------------------------------------- scoring extremes
def test_zero_signals_is_very_low():
    result = _engine().score(FraudSignals())
    assert result.fraud_score == 0
    assert result.fraud_risk_level is FraudRiskLevel.VERY_LOW
    assert result.recommended_action == "approve"


def test_max_signals_is_critical():
    result = _engine().score(
        FraudSignals(anomaly_probability=1.0, rule_penalty=1.0, behaviour_risk=1.0)
    )
    assert result.fraud_score == 1000
    assert result.fraud_risk_level is FraudRiskLevel.CRITICAL
    assert result.recommended_action == "reject"


# --------------------------------------------------------------------------- band mapping
@pytest.mark.parametrize(
    "signals,expected_score,expected_level",
    [
        (FraudSignals(anomaly_probability=0.5), 250, FraudRiskLevel.LOW),
        (FraudSignals(anomaly_probability=1.0), 500, FraudRiskLevel.MODERATE),
        (FraudSignals(anomaly_probability=1.0, behaviour_risk=1.0), 650, FraudRiskLevel.HIGH),
        (FraudSignals(anomaly_probability=1.0, rule_penalty=1.0), 850, FraudRiskLevel.CRITICAL),
    ],
)
def test_band_mapping(signals, expected_score, expected_level):
    result = _engine().score(signals)
    assert result.fraud_score == expected_score
    assert result.fraud_risk_level is expected_level


def test_components_reflect_weighting():
    result = _engine().score(FraudSignals(anomaly_probability=1.0))
    assert result.components["anomaly"] == 0.5  # weight 0.5 * signal 1.0
    assert result.components["rules"] == 0.0


# --------------------------------------------------------------------------- configurability
def test_scoring_is_fully_configurable():
    # A custom config: rules dominate, smaller range.
    cfg = FraudScoringConfig(
        score_min=0,
        score_max=100,
        weights={"anomaly": 0.1, "rules": 0.9, "behaviour": 0.0},
        bands=[
            FraudScoreBand(level="very_low", min_score=0),
            FraudScoreBand(level="critical", min_score=50),
        ],
        actions={"very_low": "approve", "critical": "reject"},
    )
    result = FraudScoringEngine(cfg).score(FraudSignals(rule_penalty=1.0))
    assert result.fraud_score == 90  # 0.9 weight → 0.9 prob → 90/100
    assert result.fraud_risk_level is FraudRiskLevel.CRITICAL


def test_empty_bands_raises():
    with pytest.raises(ConfigurationError):
        FraudScoringEngine(FraudScoringConfig(bands=[]))


def test_signals_reject_out_of_range():
    with pytest.raises(Exception):
        FraudSignals(anomaly_probability=1.5)
