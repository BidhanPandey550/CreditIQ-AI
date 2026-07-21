from __future__ import annotations

import uuid

import pyotp
import pytest

from app.core.exceptions import AuthenticationError
from app.modules.identity.models import User
from app.modules.identity.service import (
    begin_mfa_enrollment,
    confirm_mfa_enrollment,
    verify_mfa_code_once,
)


def _user() -> User:
    return User(
        organization_id=uuid.uuid4(),
        email="mfa@example.com",
        full_name="MFA User",
        password_hash="not-used",
    )


def test_mfa_secret_is_encrypted_and_totp_cannot_be_replayed() -> None:
    user = _user()
    secret, uri = begin_mfa_enrollment(user)

    assert user.mfa_secret_encrypted
    assert secret not in user.mfa_secret_encrypted
    assert uri.startswith("otpauth://totp/")

    code = pyotp.TOTP(secret).now()
    confirm_mfa_enrollment(user, code)
    assert user.mfa_enabled

    with pytest.raises(AuthenticationError, match="already been used"):
        verify_mfa_code_once(user, code)


def test_invalid_mfa_code_fails_closed() -> None:
    user = _user()
    begin_mfa_enrollment(user)
    with pytest.raises(AuthenticationError, match="Invalid MFA code"):
        confirm_mfa_enrollment(user, "invalid")
    assert not user.mfa_enabled
