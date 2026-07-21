from __future__ import annotations

import uuid

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import INSECURE_DEFAULT_SECRET, Settings
from app.core.deps import get_current_user
from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, decode_token


def test_access_token_has_verified_issuer_audience_and_type():
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        org_id=str(uuid.uuid4()),
        branch_id=None,
        roles=["Risk Analyst"],
        permissions=["risk:view"],
    )
    payload = decode_token(token)
    assert payload["iss"] == "creditiq-backend"
    assert payload["aud"] == "creditiq-platform"
    assert payload["type"] == "access"


def test_malformed_signed_claims_return_authentication_error(monkeypatch):
    monkeypatch.setattr("app.core.deps.decode_token", lambda _: {"type": "access", "sub": "bad"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with pytest.raises(AuthenticationError):
        get_current_user(credentials)


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "jwt_secret_key": INSECURE_DEFAULT_SECRET,
            "seed_on_startup": False,
            "backend_cors_origins": "https://app.example",
        },
        {
            "jwt_secret_key": "x" * 32,
            "seed_on_startup": True,
            "backend_cors_origins": "https://app.example",
        },
        {
            "jwt_secret_key": "x" * 32,
            "seed_on_startup": False,
            "backend_cors_origins": "http://localhost:5173",
        },
    ],
)
def test_production_rejects_insecure_boot_configuration(overrides):
    with pytest.raises(ValueError):
        Settings(environment="production", **overrides)
