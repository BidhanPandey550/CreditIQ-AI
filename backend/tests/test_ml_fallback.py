"""The local ML fallback must produce sane, monotonic-ish outputs (pure, no DB / no network)."""

from app.modules.credit_intelligence.ml_client import MLClient


def _predict(**overrides):
    features = {
        "debt_to_income": 0.3,
        "savings_ratio": 0.2,
        "income_stability": 0.8,
        "cashflow_volatility": 0.2,
        "has_delinquency": False,
    }
    features.update(overrides)
    return MLClient()._local_fallback(features)


def test_healthy_profile_is_low_risk():
    r = _predict()
    assert r["risk"]["band"] == "low"
    assert r["credit_score"]["score"] >= 70


def test_delinquency_increases_risk():
    clean = _predict(has_delinquency=False)["default"]["probability"]
    dirty = _predict(has_delinquency=True)["default"]["probability"]
    assert dirty > clean


def test_high_dti_lowers_score():
    low_dti = _predict(debt_to_income=0.1)["credit_score"]["score"]
    high_dti = _predict(debt_to_income=0.9)["credit_score"]["score"]
    assert high_dti < low_dti


def test_explanation_is_present():
    r = _predict()
    assert r["explanation"]["narrative"]
    assert len(r["explanation"]["contributions"]) >= 3


def test_fallback_is_labelled():
    assert _predict()["model_version"] == "local-fallback"
