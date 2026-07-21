"""Tests for credit business rules and confidence estimation."""

import pytest

from creditiq_ai.config import load_config
from creditiq_ai.config.models import CreditConfidenceConfig, CreditRuleSpec, CreditRulesConfig
from creditiq_ai.credit_intelligence.business_rules import CreditBusinessRuleEngine
from creditiq_ai.credit_intelligence.confidence import ConfidenceInputs, CreditConfidenceEngine
from creditiq_ai.exceptions import ConfigurationError


def test_rules_are_prioritized_and_stop_on_reject() -> None:
    engine = CreditBusinessRuleEngine(load_config().credit_intelligence.business_rules)
    result = engine.evaluate(
        {"monthly_income": 10000, "debt_to_income": 0.8, "employment_months": 2}
    )
    assert result.recommended_action == "reject"
    assert result.stopped_early
    assert [item.rule_name for item in result.triggered] == ["minimum_income"]
    assert "10000" in result.triggered[0].explanation


def test_rules_report_missing_fields_without_triggering() -> None:
    result = CreditBusinessRuleEngine(load_config().credit_intelligence.business_rules).evaluate(
        {"monthly_income": 50000}
    )
    assert result.recommended_action == "proceed"
    assert "missing_rule_field:debt_to_income" in result.warnings


def test_unknown_operator_is_rejected() -> None:
    config = CreditRulesConfig(
        rules=[
            CreditRuleSpec(
                name="bad",
                field="x",
                operator="magic",
                value=1,
                explanation="bad",
            )
        ]
    )
    with pytest.raises(ConfigurationError):
        CreditBusinessRuleEngine(config)


def test_confidence_combines_all_components() -> None:
    engine = CreditConfidenceEngine(load_config().credit_intelligence.confidence)
    result = engine.assess(
        ConfidenceInputs(
            probability_of_default=0.05,
            calibration_quality=0.9,
            feature_completeness=1.0,
            prediction_stability=0.8,
        )
    )
    assert result.level == "high"
    assert result.score > 0.75
    assert set(result.components) == {"probability", "calibration", "completeness", "stability"}


def test_invalid_confidence_weights_fail() -> None:
    with pytest.raises(ConfigurationError):
        CreditConfidenceEngine(CreditConfidenceConfig(weights={"probability": 1.0}))
