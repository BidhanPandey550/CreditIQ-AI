from __future__ import annotations

import uuid

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Response

from app.core.config import INSECURE_DEFAULT_SECRET, Settings
from app.core.deps import get_current_user
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_mfa_challenge_token,
    decode_token,
)
from app.modules.identity.router import _clear_refresh_cookie, _set_refresh_cookie

TEST_MFA_KEY = "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="


def test_access_token_has_verified_issuer_audience_and_type():
    applicant_id = uuid.uuid4()
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        org_id=str(uuid.uuid4()),
        branch_id=None,
        applicant_id=str(applicant_id),
        roles=["Risk Analyst"],
        permissions=["risk:view"],
    )
    payload = decode_token(token)
    assert payload["iss"] == "creditiq-backend"
    assert payload["aud"] == "creditiq-platform"
    assert payload["type"] == "access"
    assert payload["applicant_id"] == str(applicant_id)


def test_malformed_signed_claims_return_authentication_error(monkeypatch):
    monkeypatch.setattr("app.core.deps.decode_token", lambda _: {"type": "access", "sub": "bad"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with pytest.raises(AuthenticationError):
        get_current_user(credentials)


def test_mfa_challenge_cannot_be_used_as_an_access_token():
    challenge = create_mfa_challenge_token(user_id=str(uuid.uuid4()))
    assert decode_token(challenge)["type"] == "mfa_challenge"
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=challenge)
    with pytest.raises(AuthenticationError, match="Wrong token type"):
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
        {
            "jwt_secret_key": "x" * 32,
            "seed_on_startup": False,
            "auto_migrate_on_startup": True,
            "backend_cors_origins": "https://app.example",
        },
    ],
)
def test_production_rejects_insecure_boot_configuration(overrides):
    with pytest.raises(ValueError):
        Settings(environment="production", mfa_encryption_key=TEST_MFA_KEY, **overrides)


def test_production_accepts_external_migration_configuration():
    configured = Settings(
        environment="production",
        jwt_secret_key="x" * 32,
        seed_on_startup=False,
        auto_migrate_on_startup=False,
        expose_refresh_token_in_body=False,
        mfa_encryption_key=TEST_MFA_KEY,
        document_scan_required=True,
        clamav_host="clamav.internal",
        backend_cors_origins="https://app.example",
    )
    assert configured.is_production


def test_refresh_cookie_is_http_only_strict_and_path_scoped():
    response = Response()
    _set_refresh_cookie(response, "opaque-refresh-token")
    header = response.headers["set-cookie"]
    assert "HttpOnly" in header
    assert "SameSite=strict" in header
    assert "Path=/api/v1/auth" in header

    cleared = Response()
    _clear_refresh_cookie(cleared)
    clear_header = cleared.headers["set-cookie"]
    assert "Max-Age=0" in clear_header
    assert "HttpOnly" in clear_header
