"""Password hashing (argon2) and JWT token creation/verification."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError as JWTError
from passlib.context import CryptContext

from app.core.config import settings

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


# --- Passwords ---
def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd.verify(plain, hashed)
    except Exception:
        return False


# --- Tokens ---
def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    *,
    user_id: str,
    org_id: str,
    branch_id: str | None,
    applicant_id: str | None,
    roles: list[str],
    permissions: list[str],
) -> str:
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "branch_id": str(branch_id) if branch_id else None,
        "applicant_id": str(applicant_id) if applicant_id else None,
        "roles": roles,
        "perms": permissions,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, user_id: str, jti: str) -> tuple[str, datetime]:
    expires = _now() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(_now().timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires


def decode_token(token: str) -> dict:
    """Raises JWTError on invalid/expired token."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "JWTError",
]
