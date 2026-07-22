"""Auth + user management endpoints."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_active_current_user, get_db, require
from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, create_mfa_challenge_token, decode_token
from app.db.session import admin_session, tenant_session
from app.modules.identity import service
from app.modules.audit import service as audit
from app.modules.identity.models import Role, User
from app.modules.identity.rbac import PERMISSIONS
from app.modules.identity.schemas import (
    LoginRequest,
    LoginResponse,
    MeOut,
    MfaCodeRequest,
    MfaEnrollmentOut,
    MfaVerifyRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserOut,
    UserStatusUpdate,
    RoleOut,
    RoleCreate,
    RoleUpdate,
    OrganizationSwitchRequest,
    OrganizationSwitchResponse,
)
from app.modules.organization.models import Organization

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])
roles_router = APIRouter(prefix="/roles", tags=["roles"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path=f"{settings.api_v1_prefix}/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path=f"{settings.api_v1_prefix}/auth",
    )


def _token_response(access: str, refresh: str) -> TokenResponse:
    return TokenResponse(
        access_token=access,
        refresh_token=refresh if settings.expose_refresh_token_in_body else None,
    )


def _auth_db() -> Iterator[Session]:
    # Auth flows run before tenant context exists; users/roles tables are app-scoped (no RLS).
    with admin_session() as session:
        yield session


def _identity_db(
    user: CurrentUser = Depends(get_active_current_user),
) -> Iterator[Session]:
    """Keep platform-user security settings and their audit evidence in the home tenant."""
    with tenant_session(str(user.home_org_id or user.org_id)) as session:
        yield session


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit("auth-login", settings.auth_login_rate_limit))],
)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(_auth_db),
) -> LoginResponse:
    authenticated = service.verify_credentials(db, body.email, body.password, body.organization_id)
    db.execute(
        text("SELECT set_config('app.current_org', :org, true)"),
        {"org": str(authenticated.organization_id)},
    )
    if authenticated.mfa_enabled:
        audit.record(
            db,
            org_id=authenticated.organization_id,
            actor_user_id=authenticated.id,
            action="auth.mfa.challenge",
            entity_type="user",
            entity_id=authenticated.id,
        )
        return LoginResponse(
            mfa_required=True,
            challenge_token=create_mfa_challenge_token(user_id=str(authenticated.id)),
        )

    authenticated, access, refresh = service.complete_login(db, authenticated)
    audit.record(
        db,
        org_id=authenticated.organization_id,
        actor_user_id=authenticated.id,
        action="auth.login.success",
        entity_type="user",
        entity_id=authenticated.id,
    )
    _set_refresh_cookie(response, refresh)
    return LoginResponse(**_token_response(access, refresh).model_dump())


@auth_router.post(
    "/mfa/verify",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth-mfa", settings.auth_mfa_rate_limit))],
)
def verify_mfa(
    body: MfaVerifyRequest,
    response: Response,
    db: Session = Depends(_auth_db),
) -> TokenResponse:
    try:
        payload = decode_token(body.challenge_token)
        if payload.get("type") != "mfa_challenge":
            raise AuthenticationError("Wrong challenge type")
        authenticated = db.get(User, payload["sub"])
    except AuthenticationError:
        raise
    except Exception as exc:
        raise AuthenticationError("Invalid or expired MFA challenge") from exc
    if authenticated is None or not authenticated.mfa_enabled:
        raise AuthenticationError("MFA challenge is no longer valid")
    service.verify_mfa_code_once(authenticated, body.code)
    authenticated, access, refresh = service.complete_login(db, authenticated)
    db.execute(
        text("SELECT set_config('app.current_org', :org, true)"),
        {"org": str(authenticated.organization_id)},
    )
    audit.record(
        db,
        org_id=authenticated.organization_id,
        actor_user_id=authenticated.id,
        action="auth.mfa.success",
        entity_type="user",
        entity_id=authenticated.id,
    )
    _set_refresh_cookie(response, refresh)
    return _token_response(access, refresh)


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth-refresh", settings.auth_refresh_rate_limit))],
)
def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: Session = Depends(_auth_db),
) -> TokenResponse:
    token = request.cookies.get(settings.refresh_cookie_name) or (body and body.refresh_token)
    if not token:
        raise AuthenticationError("Missing refresh token")
    _, access, new_refresh = service.refresh_tokens(db, token)
    _set_refresh_cookie(response, new_refresh)
    return _token_response(access, new_refresh)


@auth_router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(_auth_db),
) -> None:
    token = request.cookies.get(settings.refresh_cookie_name)
    if token:
        revoked_user = service.revoke_refresh_token(db, token)
        if revoked_user:
            db.execute(
                text("SELECT set_config('app.current_org', :org, true)"),
                {"org": str(revoked_user.organization_id)},
            )
            audit.record(
                db,
                org_id=revoked_user.organization_id,
                actor_user_id=revoked_user.id,
                action="auth.logout",
                entity_type="user",
                entity_id=revoked_user.id,
            )
    _clear_refresh_cookie(response)


@auth_router.get("/me", response_model=MeOut)
def me(
    user: CurrentUser = Depends(get_active_current_user), db: Session = Depends(get_db)
) -> MeOut:
    record = db.get(User, user.user_id)
    return MeOut(
        id=record.id,
        email=record.email,
        full_name=record.full_name,
        organization_id=user.org_id,
        home_organization_id=user.home_org_id or record.organization_id,
        branch_id=user.branch_id,
        applicant_id=record.applicant_id,
        roles=user.roles,
        permissions=sorted(user.permissions),
    )


@auth_router.post("/switch-organization", response_model=OrganizationSwitchResponse)
def switch_organization(
    body: OrganizationSwitchRequest,
    user: CurrentUser = Depends(require("platform:admin")),
) -> OrganizationSwitchResponse:
    """Issue a short-lived access token scoped to one active tenant; refresh returns home scope."""
    with admin_session() as control_db:
        organization = control_db.get(Organization, body.organization_id)
        if organization is None:
            raise AuthenticationError("Organization not found")
        if organization.status != "active":
            raise AuthenticationError("Organization is not active")

    home_org_id = user.home_org_id or user.org_id
    access = create_access_token(
        user_id=str(user.user_id),
        org_id=str(organization.id),
        home_org_id=str(home_org_id),
        branch_id=None,
        applicant_id=None,
        roles=user.roles,
        permissions=sorted(user.permissions),
    )
    with tenant_session(str(organization.id)) as audit_db:
        audit.record(
            audit_db,
            org_id=organization.id,
            actor_user_id=user.user_id,
            action="platform.organization_context.switch",
            entity_type="organization",
            entity_id=organization.id,
            after={"home_organization_id": str(home_org_id)},
        )
    return OrganizationSwitchResponse(access_token=access, organization_id=organization.id)


@auth_router.get("/mfa/status")
def mfa_status(
    user: CurrentUser = Depends(get_active_current_user), db: Session = Depends(_identity_db)
) -> dict:
    record = db.get(User, user.user_id)
    return {"enabled": bool(record and record.mfa_enabled)}


@auth_router.post("/mfa/enroll", response_model=MfaEnrollmentOut)
def enroll_mfa(
    user: CurrentUser = Depends(get_active_current_user), db: Session = Depends(_identity_db)
) -> MfaEnrollmentOut:
    record = db.get(User, user.user_id)
    if record is None:
        raise AuthenticationError("User not found")
    secret, provisioning_uri = service.begin_mfa_enrollment(record)
    audit.record(
        db,
        org_id=user.home_org_id or user.org_id,
        actor_user_id=user.user_id,
        action="auth.mfa.enrollment.started",
        entity_type="user",
        entity_id=user.user_id,
    )
    return MfaEnrollmentOut(secret=secret, provisioning_uri=provisioning_uri)


@auth_router.post("/mfa/confirm", status_code=204)
def confirm_mfa(
    body: MfaCodeRequest,
    user: CurrentUser = Depends(get_active_current_user),
    db: Session = Depends(_identity_db),
) -> None:
    record = db.get(User, user.user_id)
    if record is None:
        raise AuthenticationError("User not found")
    service.confirm_mfa_enrollment(record, body.code)
    audit.record(
        db,
        org_id=user.home_org_id or user.org_id,
        actor_user_id=user.user_id,
        action="auth.mfa.enabled",
        entity_type="user",
        entity_id=user.user_id,
    )


@auth_router.post("/mfa/disable", status_code=204)
def disable_mfa(
    body: MfaCodeRequest,
    user: CurrentUser = Depends(get_active_current_user),
    db: Session = Depends(_identity_db),
) -> None:
    record = db.get(User, user.user_id)
    if record is None:
        raise AuthenticationError("User not found")
    service.disable_mfa(record, body.code)
    audit.record(
        db,
        org_id=user.home_org_id or user.org_id,
        actor_user_id=user.user_id,
        action="auth.mfa.disabled",
        entity_type="user",
        entity_id=user.user_id,
    )


@users_router.get("", response_model=list[UserOut])
def list_users(
    user: CurrentUser = Depends(require("user:manage")), db: Session = Depends(get_db)
) -> list[UserOut]:
    rows = db.scalars(select(User).where(User.organization_id == user.org_id)).all()
    return [
        UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            status=u.status,
            roles=[r.name for r in u.roles],
            branch_id=u.branch_id,
            applicant_id=u.applicant_id,
        )
        for u in rows
    ]


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    user: CurrentUser = Depends(require("user:manage")),
    db: Session = Depends(get_db),
) -> UserOut:
    created = service.create_user(db, user.org_id, body, actor=user)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="user.create",
        entity_type="user",
        entity_id=created.id,
        after={"email": created.email, "roles": [role.name for role in created.roles]},
    )
    return UserOut(
        id=created.id,
        email=created.email,
        full_name=created.full_name,
        status=created.status,
        roles=[r.name for r in created.roles],
        branch_id=created.branch_id,
        applicant_id=created.applicant_id,
    )


@users_router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: uuid.UUID,
    body: UserStatusUpdate,
    user: CurrentUser = Depends(require("user:manage")),
    db: Session = Depends(get_db),
) -> UserOut:
    current = db.get(User, user_id)
    before_status = (
        current.status.value if current and current.organization_id == user.org_id else None
    )
    updated = service.update_user_status(db, user, user_id, body.status)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="user.status.update",
        entity_type="user",
        entity_id=updated.id,
        before={"status": before_status},
        after={"status": updated.status.value},
    )
    return UserOut(
        id=updated.id,
        email=updated.email,
        full_name=updated.full_name,
        status=updated.status,
        roles=[role.name for role in updated.roles],
        branch_id=updated.branch_id,
        applicant_id=updated.applicant_id,
    )


@users_router.get("/roles", response_model=list[RoleOut])
def assignable_roles(
    user: CurrentUser = Depends(require("user:manage")),
    db: Session = Depends(get_db),
) -> list[RoleOut]:
    return [
        RoleOut(
            id=role.id,
            name=role.name,
            is_system=role.is_system,
            permissions=[permission.code for permission in role.permissions],
        )
        for role in service.list_roles(db, user)
    ]


@users_router.get("/permissions", response_model=dict)
def catalog(user: CurrentUser = Depends(require("role:manage"))) -> dict:
    return PERMISSIONS


@roles_router.get("", response_model=list[RoleOut])
def list_roles(
    user: CurrentUser = Depends(require("role:manage")),
    db: Session = Depends(get_db),
) -> list[RoleOut]:
    return [
        RoleOut(
            id=role.id,
            name=role.name,
            is_system=role.is_system,
            permissions=[permission.code for permission in role.permissions],
        )
        for role in service.list_roles(db, user)
    ]


@roles_router.post("", response_model=RoleOut, status_code=201)
def create_role(
    body: RoleCreate,
    user: CurrentUser = Depends(require("role:manage")),
    db: Session = Depends(get_db),
) -> RoleOut:
    role = service.create_role(db, user, body.name, body.permissions)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="role.create",
        entity_type="role",
        entity_id=role.id,
        after={"name": role.name, "permissions": sorted(body.permissions)},
    )
    return RoleOut(
        id=role.id,
        name=role.name,
        is_system=False,
        permissions=sorted(body.permissions),
    )


@roles_router.patch("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    user: CurrentUser = Depends(require("role:manage")),
    db: Session = Depends(get_db),
) -> RoleOut:
    current = db.get(Role, role_id)
    before = (
        {"name": current.name, "permissions": sorted(p.code for p in current.permissions)}
        if current and current.organization_id == user.org_id
        else None
    )
    role = service.update_role(
        db,
        user,
        role_id,
        name=body.name,
        permission_codes=body.permissions,
    )
    after = {"name": role.name, "permissions": sorted(p.code for p in role.permissions)}
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="role.update",
        entity_type="role",
        entity_id=role.id,
        before=before,
        after=after,
    )
    return RoleOut(
        id=role.id,
        name=role.name,
        is_system=False,
        permissions=after["permissions"],
    )
