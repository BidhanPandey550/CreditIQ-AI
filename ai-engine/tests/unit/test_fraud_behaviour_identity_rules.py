"""Tests for fraud behaviour, identity, and rule intelligence."""

from creditiq_ai.config import load_config
from creditiq_ai.fraud_intelligence import (
    BehaviourAnalyzer,
    BehaviourInput,
    FraudRuleEngine,
    IdentityValidator,
)


def test_behaviour_profile_computes_all_indicators() -> None:
    analyzer = BehaviourAnalyzer(load_config().fraud_intelligence.behaviour)
    profile = analyzer.analyze(
        BehaviourInput(
            monthly_income=[50000, 51000, 49000, 80000],
            monthly_expenses=[30000, 32000, 31000, 70000],
            monthly_savings=[10000, 9000, 11000, 1000],
            monthly_debt_payments=[5000, 5000, 5000, 20000],
            transaction_counts=[25, 27, 26, 90],
        )
    )
    assert 0.0 < profile.risk_score <= 1.0
    assert len(profile.indicators) == 7
    assert profile.data_completeness == 1.0


def test_incomplete_behaviour_history_is_explicit() -> None:
    profile = BehaviourAnalyzer(load_config().fraud_intelligence.behaviour).analyze(
        BehaviourInput(monthly_income=[50000])
    )
    assert profile.data_completeness == 0.2
    assert "incomplete_behaviour_history" in profile.warnings


def test_identity_validation_detects_missing_mismatch_and_duplicate() -> None:
    validator = IdentityValidator(
        load_config().fraud_intelligence.identity,
        duplicate_check=lambda identity: identity.get("government_id") == "DUPLICATE",
    )
    result = validator.validate(
        {
            "full_name": "Test Applicant",
            "government_id": "DUPLICATE",
            "declared_date_of_birth": "1990-01-01",
            "verified_date_of_birth": "1991-01-01",
        }
    )
    assert result.duplicate_suspected
    assert "date_of_birth" in result.missing_fields
    assert result.mismatches
    assert result.risk_score > 0.0


def test_fraud_rules_reuse_priority_and_stop_semantics() -> None:
    result = FraudRuleEngine(load_config().fraud_intelligence.rules).evaluate(
        {"debt_to_income": 2.5, "recent_loan_requests": 8, "income_growth_ratio": 4.0}
    )
    assert result.recommended_action == "reject"
    assert result.stopped_early
    assert result.triggered[0].rule_name == "impossible_debt_ratio"
