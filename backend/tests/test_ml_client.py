"""The backend must fail closed when governed ML inference is unavailable."""

from __future__ import annotations

import httpx
import pytest

from app.core.exceptions import ServiceUnavailableError
from app.modules.credit_intelligence.ml_client import MLClient


def test_ml_client_returns_valid_service_response(monkeypatch) -> None:
    expected = {"model_version": "verified-v1"}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return expected

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response())
    assert MLClient().predict({"debt_to_income": 0.3}) == expected


def test_ml_client_fails_closed_on_network_error(monkeypatch) -> None:
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "post", unavailable)
    with pytest.raises(ServiceUnavailableError, match="no lending decision"):
        MLClient().predict({"debt_to_income": 0.3})
