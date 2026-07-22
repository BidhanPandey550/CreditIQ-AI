"""Authentication & user management use cases."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
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
    return complete_login(db, verify_credentials(db, email, password, org_id))


def verify_credentials(db: Session, email: str, password: str, org_id: uuid.UUID | None) -> User:
    """Verify the first authentication factor without issuing a session."""
    stmt = select(User).where(User.email == email)
    if org_id:
        stmt = stmt.where(User.organization_id == org_id)
    users = list(db.scalars(stmt).all())
    if len(users) != 1 or not verify_password(password, users[0].password_hash):
        raise AuthenticationError("Invalid credentials")
    user = users[0]
    if user.status == "disabled":
        raise AuthenticationError("Account disabled")
    return user


def issue_tokens(db: Session, user: User) -> tuple[User, str, str]:
    role_names = [r.name for r in user.roles]
    permissions = _collect_permissions(user.roles)

    access = create_access_token(
        user_id=str(user.id),
        org_id=str(user.organization_id),
        branch_id=str(user.branch_id) if user.branch_id else None,
        applicant_id=str(user.applicant_id) if user.applicant_id else None,
        roles=role_names,
        permissions=permissions,
    )
    jti = str(uuid.uuid4())
    refresh, expires = create_refresh_token(user_id=str(user.id), jti=jti)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=_hash_token(refresh),
            expires_at=expires,
        )
    )
    return user, access, refresh


def complete_login(db: Session, user: User) -> tuple[User, str, str]:
    user.last_login_at = utcnow()
    return issue_tokens(db, user)


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
    if not hmac.compare_digest(record.token_hash, _hash_token(refresh_token)):
        raise AuthenticationError("Refresh token does not match its session")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise AuthenticationError("Refresh token expired")
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


def revoke_refresh_token(db: Session, refresh_token: str) -> User | None:
    """Revoke one valid refresh session; invalid input is deliberately idempotent."""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            return None
        record = db.scalars(select(RefreshToken).where(RefreshToken.jti == payload["jti"])).first()
    except Exception:
        return None
    if record is None or not hmac.compare_digest(record.token_hash, _hash_token(refresh_token)):
        return None
    if record.revoked_at is None:
        record.revoked_at = utcnow()
    return db.get(User, record.user_id)


def _mfa_cipher() -> Fernet:
    try:
        return Fernet(settings.mfa_encryption_key.encode())
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("MFA encryption is not configured") from exc


def _decrypt_mfa_secret(user: User) -> str:
    if not user.mfa_secret_encrypted:
        raise AuthenticationError("MFA enrollment is incomplete")
    try:
        return _mfa_cipher().decrypt(user.mfa_secret_encrypted.encode()).decode()
    except InvalidToken as exc:
        raise AuthenticationError("MFA secret cannot be decrypted") from exc


def begin_mfa_enrollment(user: User) -> tuple[str, str]:
    """Replace any unconfirmed enrollment and return its one-time provisioning material."""
    if user.mfa_enabled:
        raise ConflictError("Disable the existing MFA enrollment before replacing it")
    secret = pyotp.random_base32()
    user.mfa_secret_encrypted = _mfa_cipher().encrypt(secret.encode()).decode()
    user.mfa_enabled = False
    user.mfa_last_verified_step = None
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.mfa_issuer)
    return secret, uri


def verify_mfa_code_once(user: User, code: str) -> None:
    """Verify a TOTP and reject reuse of the same or an older time step."""
    secret = _decrypt_mfa_secret(user)
    totp = pyotp.TOTP(secret)
    current_step = int(datetime.now(timezone.utc).timestamp()) // totp.interval
    matched_step = next(
        (
            step
            for step in (current_step - 1, current_step, current_step + 1)
            if hmac.compare_digest(totp.at(step * totp.interval), code)
        ),
        None,
    )
    if matched_step is None:
        raise AuthenticationError("Invalid MFA code")
    if user.mfa_last_verified_step is not None and matched_step <= user.mfa_last_verified_step:
        raise AuthenticationError("MFA code has already been used")
    user.mfa_last_verified_step = matched_step


def confirm_mfa_enrollment(user: User, code: str) -> None:
    verify_mfa_code_once(user, code)
    user.mfa_enabled = True


def disable_mfa(user: User, code: str) -> None:
    if not user.mfa_enabled:
        raise ConflictError("MFA is not enabled")
    verify_mfa_code_once(user, code)
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_last_verified_step = None


def validate_role_assignment(actor: CurrentUser, role_names: list[str]) -> None:
    """Prevent tenant administrators from granting platform-wide authority."""
    if "Super Admin" in role_names and not actor.has("platform:admin"):
        raise PermissionDeniedError("Only a platform administrator can assign Super Admin")


def assignable_role_names(actor: CurrentUser) -> list[str]:
    """Return system roles the current actor may safely assign."""
    names = list(ROLE_PERMISSIONS)
    if not actor.has("platform:admin"):
        names.remove("Super Admin")
    return names


def create_user(db: Session, org_id: uuid.UUID, data, *, actor: CurrentUser) -> User:
    validate_role_assignment(actor, data.role_names)
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

    is_applicant_account = "Applicant" in data.role_names
    if is_applicant_account and set(data.role_names) != {"Applicant"}:
        raise ConflictError("Applicant accounts cannot be combined with staff roles")
    if is_applicant_account and data.applicant_id is None:
        raise ConflictError("Applicant accounts require an applicant ownership link")
    if not is_applicant_account and data.applicant_id is not None:
        raise ConflictError("Only Applicant accounts may have an applicant ownership link")

    linked_applicant = None
    if data.applicant_id is not None:
        from app.modules.applicant.models import Applicant

        linked_applicant = db.get(Applicant, data.applicant_id)
        if linked_applicant is None or linked_applicant.organization_id != org_id:
            raise NotFoundError("Applicant ownership target not found")
    elif data.branch_id is not None:
        from app.modules.organization.service import require_branch

        require_branch(db, org_id, data.branch_id)

    user = User(
        organization_id=org_id,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        branch_id=linked_applicant.branch_id if linked_applicant else data.branch_id,
        applicant_id=data.applicant_id,
    )
    user.roles = list(roles)
    db.add(user)
    db.flush()
    return user
