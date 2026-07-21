"""Auth + user management endpoints."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, get_db, require
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.db.session import admin_session
from app.modules.identity import service
from app.modules.identity.models import User
from app.modules.identity.rbac import PERMISSIONS
from app.modules.identity.schemas import (
    LoginRequest,
    MeOut,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserOut,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _auth_db() -> Iterator[Session]:
    # Auth flows run before tenant context exists; users/roles tables are app-scoped (no RLS).
    with admin_session() as session:
        yield session


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth-login", settings.auth_login_rate_limit))],
)
def login(body: LoginRequest, db: Session = Depends(_auth_db)) -> TokenResponse:
    _, access, refresh = service.authenticate(db, body.email, body.password, body.organization_id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth-refresh", settings.auth_refresh_rate_limit))],
)
def refresh(body: RefreshRequest, db: Session = Depends(_auth_db)) -> TokenResponse:
    _, access, new_refresh = service.refresh_tokens(db, body.refresh_token)
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@auth_router.get("/me", response_model=MeOut)
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> MeOut:
    record = db.get(User, user.user_id)
    return MeOut(
        id=record.id,
        email=record.email,
        full_name=record.full_name,
        organization_id=record.organization_id,
        branch_id=record.branch_id,
        roles=user.roles,
        permissions=sorted(user.permissions),
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
        )
        for u in rows
    ]


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    user: CurrentUser = Depends(require("user:manage")),
    db: Session = Depends(get_db),
) -> UserOut:
    created = service.create_user(db, user.org_id, body)
    return UserOut(
        id=created.id,
        email=created.email,
        full_name=created.full_name,
        status=created.status,
        roles=[r.name for r in created.roles],
    )


@users_router.get("/permissions", response_model=dict)
def catalog(user: CurrentUser = Depends(require("role:manage"))) -> dict:
    return PERMISSIONS
