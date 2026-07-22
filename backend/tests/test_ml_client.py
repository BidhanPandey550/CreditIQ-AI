"""The backend must fail closed when governed ML inference is unavailable."""

import httpx
import pytest

from app.core.exceptions import ServiceUnavailableError
from app.modules.credit_intelligence.ml_client import MLClient


def _prediction() -> dict:
    return {
        "model_version": "verified-v1",
        "risk": {"band": "low", "probability": 0.1},
        "credit_score": {"score": 780, "subscores": {}},
        "default": {"probability": 0.1, "horizon_months": 12},
        "fraud": {
            "severity": "low",
            "level": "very_low",
            "reasons": [],
            "anomaly_score": 0.03,
            "score": 80,
        },
        "explanation": {
            "contributions": [{"feature": "savings_ratio", "impact": -0.2, "value": 0.3}],
            "narrative": "Stable savings reduced estimated risk.",
        },
        "decision": {
            "credit_score": 780,
            "probability_of_default": 0.1,
            "credit_risk": "low",
            "fraud_score": 80,
            "fraud_probability": 0.03,
            "fraud_risk": "very_low",
            "recommendation": "approve",
            "confidence": 0.9,
            "decision_reasons": ["credit_risk=low->approve"],
            "model_versions": {"credit": "verified-v1"},
            "feature_version": "features-v1",
            "correlation_id": "decision-123",
            "timestamp": "2026-07-22T11:00:00Z",
            "processing_duration_ms": 12.5,
            "warnings": [],
            "monitoring_status": "ok",
        },
    }


def test_ml_client_returns_valid_service_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=_prediction()))
    client = MLClient(httpx.Client(transport=transport, base_url="http://ml-engine"))
    result = client.predict({"debt_to_income": 0.3})
    assert result["model_version"] == "verified-v1"
    assert result["decision"]["recommendation"] == "approve"
    assert result["decision"]["correlation_id"] == "decision-123"


def test_ml_client_fails_closed_on_network_error() -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = MLClient(httpx.Client(transport=httpx.MockTransport(unavailable)))
    with pytest.raises(ServiceUnavailableError, match="No unverified result"):
        client.predict({"debt_to_income": 0.3})


@pytest.mark.parametrize(
    "mutation",
    [
        lambda body: body.pop("explanation"),
        lambda body: body["default"].update(probability=1.4),
        lambda body: body.update(unexpected="unsafe"),
    ],
)
def test_ml_client_fails_closed_on_invalid_downstream_contract(mutation) -> None:
    body = _prediction()
    mutation(body)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    client = MLClient(httpx.Client(transport=transport))

    with pytest.raises(ServiceUnavailableError, match="No unverified result"):
        client.predict({"debt_to_income": 0.3})


def test_ml_client_forwards_request_id(monkeypatch) -> None:
    observed: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["request_id"] = request.headers.get("X-Request-ID")
        return httpx.Response(200, json=_prediction())

    monkeypatch.setattr(
        "app.modules.credit_intelligence.ml_client.current_request_id", lambda: "request-123"
    )
    client = MLClient(
        httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ml-engine")
    )
    client.predict({"debt_to_income": 0.3})

    assert observed["request_id"] == "request-123"


def test_model_operations_status_validates_both_downstream_contracts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/models":
            return httpx.Response(
                200,
                json={
                    "version": "credit-v7",
                    "algorithm": "logistic_regression",
                    "features_used": 5,
                    "metrics": {"roc_auc": 0.82},
                    "stage": "production",
                    "data_source": "repayment-2026-07",
                    "feature_version": "features-v3",
                },
            )
        return httpx.Response(
            200,
            json={
                "prediction_count": 120,
                "failure_count": 1,
                "failure_rate": 1 / 120,
                "average_latency_ms": 18.5,
                "p95_latency_ms": 31.2,
                "status": "healthy",
                "reasons": [],
                "generated_at": "2026-07-22T11:00:00Z",
            },
        )

    client = MLClient(
        httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ml-engine")
    )

    status = client.operations_status()

    assert status.model.version == "credit-v7"
    assert status.monitoring.prediction_count == 120


def test_model_operations_status_rejects_malformed_telemetry() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/models":
            return httpx.Response(
                200,
                json={
                    "version": "v1",
                    "algorithm": "lr",
                    "features_used": 5,
                    "metrics": {},
                    "stage": "production",
                    "data_source": "dataset-v1",
                    "feature_version": "features-v1",
                },
            )
        return httpx.Response(200, json={"prediction_count": -1})

    client = MLClient(
        httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ml-engine")
    )
    with pytest.raises(ServiceUnavailableError, match="No unverified result"):
        client.operations_status()
