"""FastAPI dependencies: current user, tenant context, and permission gating."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import JWTError, decode_token
from app.db.session import tenant_session

bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user_id: uuid.UUID
    org_id: uuid.UUID
    branch_id: uuid.UUID | None
    roles: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)

    def has(self, permission: str) -> bool:
        return "platform:admin" in self.permissions or permission in self.permissions


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    if creds is None:
        raise AuthenticationError("Missing bearer token")
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise AuthenticationError("Wrong token type")
        return CurrentUser(
            user_id=uuid.UUID(payload["sub"]),
            org_id=uuid.UUID(payload["org_id"]),
            branch_id=uuid.UUID(payload["branch_id"])
            if payload.get("branch_id")
            else None,
            roles=payload.get("roles", []),
            permissions=set(payload.get("perms", [])),
        )
    except AuthenticationError:
        raise
    except (JWTError, KeyError, TypeError, ValueError):
        raise AuthenticationError("Invalid or expired token")


def get_db(user: CurrentUser = Depends(get_current_user)) -> Iterator[Session]:
    """Tenant-scoped DB session. RLS is pinned to the caller's organization."""
    with tenant_session(str(user.org_id)) as session:
        yield session


def require(permission: str):
    """Dependency factory enforcing a permission before the route runs."""

    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has(permission):
            raise PermissionDeniedError(f"Requires permission '{permission}'")
        return user

    return _checker
