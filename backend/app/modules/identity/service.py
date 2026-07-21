"""Authentication & user management use cases."""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.base import utcnow
from app.modules.identity.models import Permission, RefreshToken, Role, User
from app.modules.identity.rbac import PERMISSIONS, ROLE_PERMISSIONS


def ensure_rbac(db: Session) -> dict[str, Role]:
    """Idempotently create the permission catalog and the six system roles."""
    existing_perms = {p.code: p for p in db.scalars(select(Permission)).all()}
    for code, desc in PERMISSIONS.items():
        if code not in existing_perms:
            p = Permission(code=code, description=desc)
            db.add(p)
            existing_perms[code] = p
    db.flush()

    roles: dict[str, Role] = {}
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role = db.scalars(
            select(Role).where(Role.name == role_name, Role.organization_id.is_(None))
        ).first()
        if role is None:
            role = Role(name=role_name, is_system=True, organization_id=None)
            db.add(role)
        role.permissions = [existing_perms[c] for c in perm_codes]
        roles[role_name] = role
    db.flush()
    return roles


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _collect_permissions(roles: list[Role]) -> list[str]:
    perms: set[str] = set()
    for r in roles:
        perms.update(p.code for p in r.permissions)
    return sorted(perms)


def authenticate(
    db: Session, email: str, password: str, org_id: uuid.UUID | None
) -> tuple[User, str, str]:
    stmt = select(User).where(User.email == email)
    if org_id:
        stmt = stmt.where(User.organization_id == org_id)
    user = db.scalars(stmt).first()
    if not user or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid credentials")
    if user.status == "disabled":
        raise AuthenticationError("Account disabled")

    user.last_login_at = utcnow()
    return issue_tokens(db, user)


def issue_tokens(db: Session, user: User) -> tuple[User, str, str]:
    role_names = [r.name for r in user.roles]
    permissions = _collect_permissions(user.roles)

    access = create_access_token(
        user_id=str(user.id),
        org_id=str(user.organization_id),
        branch_id=str(user.branch_id) if user.branch_id else None,
        roles=role_names,
        permissions=permissions,
    )
    jti = str(uuid.uuid4())
    refresh, expires = create_refresh_token(user_id=str(user.id), jti=jti)
    db.add(
        RefreshToken(user_id=user.id, jti=jti, token_hash=_hash_token(refresh), expires_at=expires)
    )
    return user, access, refresh


def refresh_tokens(db: Session, refresh_token: str) -> tuple[User, str, str]:
    """Rotate refresh token with reuse detection (revoked token => kill the family)."""
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise AuthenticationError("Invalid refresh token")
    if payload.get("type") != "refresh":
        raise AuthenticationError("Wrong token type")

    jti = payload["jti"]
    record = db.scalars(select(RefreshToken).where(RefreshToken.jti == jti)).first()
    if not record:
        raise AuthenticationError("Unknown refresh token")
    if record.revoked_at is not None:
        # Reuse of an already-rotated token => revoke all sessions for this user.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == record.user_id, RefreshToken.revoked_at.is_(None)
        ).update({"revoked_at": utcnow()})
        raise AuthenticationError("Refresh token reuse detected; sessions revoked")

    user = db.get(User, record.user_id)
    if not user:
        raise AuthenticationError("User not found")

    record.revoked_at = utcnow()
    user, access, new_refresh = issue_tokens(db, user)
    record.replaced_by = _hash_token(new_refresh)[:64]
    return user, access, new_refresh


def create_user(db: Session, org_id: uuid.UUID, data) -> User:
    exists = db.scalars(
        select(User).where(User.organization_id == org_id, User.email == data.email)
    ).first()
    if exists:
        raise ConflictError("A user with this email already exists in the organization")

    roles = db.scalars(
        select(Role).where(
            Role.name.in_(data.role_names),
            ((Role.organization_id == org_id) | (Role.organization_id.is_(None))),
        )
    ).all()
    if not roles:
        raise NotFoundError("None of the requested roles exist")

    user = User(
        organization_id=org_id,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        branch_id=data.branch_id,
    )
    user.roles = list(roles)
    db.add(user)
    db.flush()
    return user
