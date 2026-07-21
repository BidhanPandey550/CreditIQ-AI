"""D2 tests — Unified Decision Engine scenarios A–G + policy + contract."""

import pandas as pd
import pytest

from creditiq_ai.config import load_config
from creditiq_ai.decision import DecisionEngine, DecisionRequest, UnifiedDecision
from creditiq_ai.decision.policy import DecisionPolicy
from creditiq_ai.exceptions import ArtifactIntegrityError
from creditiq_ai.fraud_intelligence import FraudSignals

ROW = pd.DataFrame([{"monthly_income": 80000.0, "monthly_expenses": 30000.0}])


def _engine(
    pd_value=None, fraud_signals=None, fraud_raises=False, credit_raises=None, with_fraud=True
):
    def credit(_row):
        if credit_raises is not None:
            raise credit_raises
        return pd_value

    def fraud(_row):
        if fraud_raises:
            raise RuntimeError("fraud subsystem down")
        return fraud_signals if fraud_signals is not None else FraudSignals()

    return DecisionEngine(
        load_config(), credit_predictor=credit, fraud_assessor=fraud if with_fraud else None
    )


def _decide(**kw):
    return _engine(**kw).decide(
        DecisionRequest(
            row=ROW,
            correlation_id="c-1",
            model_versions={"credit": "lr-1"},
            feature_version="feat-1",
        )
    )


# --------------------------------------------------------------------------- scenarios
def test_A_strong_credit_low_fraud_approves():
    d = _decide(pd_value=0.0002, fraud_signals=FraudSignals(anomaly_probability=0.05))
    assert d.recommendation == "approve"
    assert d.credit_risk in {"very_low", "low"}
    assert d.fraud_risk == "very_low"


def test_B_weak_credit_rejects():
    d = _decide(pd_value=0.85, fraud_signals=FraudSignals(anomaly_probability=0.05))
    assert d.recommendation == "reject"


def test_C_high_fraud_blocks_auto_approval():
    # strong credit (would approve) but high fraud → must NOT auto-approve
    d = _decide(
        pd_value=0.0002, fraud_signals=FraudSignals(anomaly_probability=1.0, behaviour_risk=1.0)
    )
    assert d.recommendation != "approve"
    assert d.recommendation in {"manual_review", "reject"}
    assert d.fraud_risk in {"high", "critical"}


def test_D_moderate_credit_moderate_fraud_reviews():
    d = _decide(
        pd_value=0.005, fraud_signals=FraudSignals(anomaly_probability=0.8, rule_penalty=0.5)
    )
    assert d.recommendation == "review"
    assert d.credit_risk == "medium"


def test_E_missing_data_is_safe_review():
    engine = _engine(pd_value=0.0002, fraud_signals=FraudSignals(anomaly_probability=0.05))
    bad_row = pd.DataFrame([{"monthly_income": 80000.0}])  # missing required monthly_expenses
    d = engine.decide(DecisionRequest(row=bad_row, correlation_id="c-2"))
    assert d.recommendation == "manual_review"
    assert "incomplete_required_data" in d.decision_reasons


def test_F_fraud_failure_is_non_blocking_but_conservative():
    d = _decide(pd_value=0.0002, fraud_raises=True)  # would approve, but fraud down
    assert d.recommendation == "manual_review"  # conservative fallback, not a crash
    assert "fraud_unavailable" in d.warnings
    assert d.monitoring_status == "degraded"
    assert d.fraud_score is None


def test_G_integrity_failure_blocks_inference():
    engine = _engine(credit_raises=ArtifactIntegrityError("tampered model"))
    with pytest.raises(ArtifactIntegrityError):  # unsafe inference is BLOCKED
        engine.decide(DecisionRequest(row=ROW))


# --------------------------------------------------------------------------- contract
def test_unified_decision_has_all_required_fields():
    d = _decide(pd_value=0.0002, fraud_signals=FraudSignals(anomaly_probability=0.1))
    assert isinstance(d, UnifiedDecision)
    for field in (
        "credit_score",
        "probability_of_default",
        "credit_risk",
        "fraud_score",
        "fraud_probability",
        "fraud_risk",
        "recommendation",
        "confidence",
        "decision_reasons",
        "model_versions",
        "feature_version",
        "correlation_id",
        "timestamp",
        "processing_duration_ms",
        "warnings",
        "monitoring_status",
    ):
        assert hasattr(d, field), field
    assert 0 <= d.probability_of_default <= 1
    assert load_config().scoring.min_score <= d.credit_score <= load_config().scoring.max_score
    assert 0 <= d.confidence <= 1
    assert d.correlation_id == "c-1"
    assert d.model_versions == {"credit": "lr-1"}


# --------------------------------------------------------------------------- policy (unit)
def test_policy_fraud_cannot_upgrade_a_reject():
    policy = DecisionPolicy(load_config().decision)
    rec, _ = policy.recommend(
        credit_band="very_high",
        fraud_level="very_low",
        credit_ok=True,
        fraud_ok=True,
        data_complete=True,
    )
    assert rec == "reject"  # low fraud never rescues weak credit


def test_policy_fraud_reject_override():
    policy = DecisionPolicy(load_config().decision)
    rec, reasons = policy.recommend(
        credit_band="low", fraud_level="critical", credit_ok=True, fraud_ok=True, data_complete=True
    )
    assert rec == "reject"
    assert any("reject_override" in r for r in reasons)
