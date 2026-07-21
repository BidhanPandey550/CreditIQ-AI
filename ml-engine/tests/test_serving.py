"""Contract tests for the canonical ML serving adapter."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.serving.main import app
from src.serving.runtime import CanonicalRuntime


@pytest.fixture(scope="module")
def runtime() -> CanonicalRuntime:
    """Train the deterministic development runtime once for this module."""
    return CanonicalRuntime.train()


def test_runtime_prediction_uses_enterprise_contract(runtime: CanonicalRuntime) -> None:
    result = runtime.predict(
        {
            "debt_to_income": 0.3,
            "savings_ratio": 0.2,
            "income_stability": 0.8,
            "cashflow_volatility": 0.2,
            "has_delinquency": False,
        }
    )

    assert 300 <= result["credit_score"]["score"] <= 850
    assert 0.0 <= result["default"]["probability"] <= 1.0
    assert 0 <= result["fraud"]["score"] <= 1000
    assert result["fraud"]["severity"] in {
        "very_low",
        "low",
        "moderate",
        "high",
        "critical",
    }
    assert result["model_version"].startswith("logistic-")
    assert result["explanation"]["contributions"]
    assert result["explanation"]["narrative"]


def test_http_contract_and_model_disclosure(runtime: CanonicalRuntime, monkeypatch) -> None:
    monkeypatch.setattr("src.serving.main.runtime", runtime)
    with TestClient(app) as client:
        health = client.get("/health")
        models = client.get("/models")
        prediction = client.post(
            "/predict",
            json={
                "features": {
                    "debt_to_income": 0.4,
                    "savings_ratio": 0.1,
                    "income_stability": 0.6,
                    "cashflow_volatility": 0.3,
                    "has_delinquency": False,
                }
            },
        )

    assert health.status_code == 200
    assert models.status_code == 200
    assert models.json()["stage"] == "development"
    assert models.json()["data_source"] == "synthetic"
    assert prediction.status_code == 200
    assert 300 <= prediction.json()["credit_score"]["score"] <= 850


def test_predict_rejects_empty_and_unknown_request_fields(runtime, monkeypatch) -> None:
    monkeypatch.setattr("src.serving.main.runtime", runtime)
    with TestClient(app) as client:
        assert client.post("/predict", json={"features": {}}).status_code == 422
        assert (
            client.post(
                "/predict",
                json={"features": {"debt_to_income": 0.4}, "unexpected": True},
            ).status_code
            == 422
        )
