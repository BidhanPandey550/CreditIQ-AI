from __future__ import annotations

import hashlib
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.db.base import utcnow
from app.modules.identity.rbac import PERMISSIONS
from app.modules.integration.models import APIKey
from app.modules.integration.schemas import APIKeyCreate

KEY_PREFIX = "ciq_live_"


def validate_scopes(actor: CurrentUser, requested: list[str]) -> list[str]:
    """Return normalized scopes after enforcing catalog and delegation boundaries."""
    scopes = sorted(set(requested))
    unknown = set(scopes).difference(PERMISSIONS)
    if unknown:
        raise PermissionDeniedError(f"Unknown API key scopes: {', '.join(sorted(unknown))}")
    if not actor.has("platform:admin"):
        forbidden = set(scopes).difference(actor.permissions)
        if forbidden:
            raise PermissionDeniedError(
                f"Cannot delegate scopes not held by the current user: {', '.join(sorted(forbidden))}"
            )
    return scopes


def assignable_scopes(actor: CurrentUser) -> dict[str, str]:
    """Expose only permissions the actor can delegate to a machine credential."""
    if actor.has("platform:admin"):
        return dict(PERMISSIONS)
    return {
        code: description for code, description in PERMISSIONS.items() if code in actor.permissions
    }


def _generate_key() -> tuple[str, str, str]:
    visible_prefix = secrets.token_hex(6)
    raw_key = f"{KEY_PREFIX}{visible_prefix}.{secrets.token_urlsafe(32)}"
    return raw_key, visible_prefix, hashlib.sha256(raw_key.encode()).hexdigest()


def create_api_key(db: Session, actor: CurrentUser, data: APIKeyCreate) -> tuple[APIKey, str]:
    scopes = validate_scopes(actor, data.scopes)
    raw_key, prefix, key_hash = _generate_key()
    api_key = APIKey(
        organization_id=actor.org_id,
        name=data.name,
        prefix=prefix,
        key_hash=key_hash,
        scopes=scopes,
        created_by_user_id=actor.user_id,
        expires_at=data.expires_at,
    )
    db.add(api_key)
    db.flush()
    return api_key, raw_key


def list_api_keys(db: Session, org_id: uuid.UUID) -> list[APIKey]:
    return list(
        db.scalars(
            select(APIKey)
            .where(APIKey.organization_id == org_id)
            .order_by(APIKey.created_at.desc())
        ).all()
    )


def revoke_api_key(db: Session, org_id: uuid.UUID, key_id: uuid.UUID) -> APIKey:
    api_key = db.get(APIKey, key_id)
    if api_key is None or api_key.organization_id != org_id:
        raise NotFoundError("API key not found")
    if api_key.revoked_at is None:
        api_key.revoked_at = utcnow()
        db.flush()
    return api_key
