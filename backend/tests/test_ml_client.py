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
    }


def test_ml_client_returns_valid_service_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=_prediction()))
    client = MLClient(httpx.Client(transport=transport, base_url="http://ml-engine"))
    assert client.predict({"debt_to_income": 0.3}) == _prediction()


def test_ml_client_fails_closed_on_network_error() -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = MLClient(httpx.Client(transport=httpx.MockTransport(unavailable)))
    with pytest.raises(ServiceUnavailableError, match="no lending decision"):
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

    with pytest.raises(ServiceUnavailableError, match="no lending decision"):
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
