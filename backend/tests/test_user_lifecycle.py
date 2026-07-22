from __future__ import annotations

import uuid
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app.core.deps import CurrentUser, get_active_current_user
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    PermissionDeniedError,
)
from app.modules.identity.service import update_user_status
from app.shared.enums import UserStatus


def _actor(*permissions: str) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        branch_id=None,
        roles=["Administrator"],
        permissions=set(permissions),
    )


def test_disabled_account_invalidates_existing_access_claim(monkeypatch) -> None:
    actor = _actor("loan:read")

    class Result:
        def first(self):
            return SimpleNamespace(status="disabled")

    @contextmanager
    def disabled_session(_org_id):
        yield SimpleNamespace(scalars=lambda _statement: Result())

    monkeypatch.setattr("app.db.session.tenant_session", disabled_session)
    with pytest.raises(AuthenticationError, match="not active"):
        get_active_current_user(actor)


def test_active_account_keeps_existing_access_claim(monkeypatch) -> None:
    actor = _actor("loan:read")

    record = SimpleNamespace(
        id=actor.user_id,
        organization_id=actor.org_id,
        branch_id=uuid.uuid4(),
        applicant_id=None,
        status="active",
        roles=[
            SimpleNamespace(
                name="Risk Analyst",
                permissions=[SimpleNamespace(code="risk:read")],
            )
        ],
    )

    class Result:
        def first(self):
            return record

    @contextmanager
    def active_session(_org_id):
        yield SimpleNamespace(
            scalars=lambda _statement: Result(),
            get=lambda _model, _record_id: SimpleNamespace(status="active"),
        )

    monkeypatch.setattr("app.db.session.tenant_session", active_session)
    resolved = get_active_current_user(actor)
    assert resolved is not actor
    assert resolved.branch_id == record.branch_id
    assert resolved.roles == ["Risk Analyst"]
    assert resolved.permissions == {"risk:read"}


class _Database:
    def __init__(self, target, *, active_admins: int = 2):
        self.target = target
        self.active_admins = active_admins

    def get(self, _model, _identifier):
        return self.target

    def scalar(self, _statement):
        return self.active_admins


def test_administrator_cannot_disable_self() -> None:
    actor = _actor("user:manage")
    target = SimpleNamespace(
        id=actor.user_id,
        organization_id=actor.org_id,
        roles=[SimpleNamespace(name="Administrator")],
        status="active",
    )
    with pytest.raises(ConflictError, match="own account"):
        update_user_status(_Database(target), actor, actor.user_id, UserStatus.disabled)  # type: ignore[arg-type]


def test_last_tenant_administrator_cannot_be_disabled() -> None:
    actor = _actor("user:manage")
    target = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=actor.org_id,
        roles=[SimpleNamespace(name="Administrator")],
        status="active",
    )
    with pytest.raises(ConflictError, match="last active"):
        update_user_status(  # type: ignore[arg-type]
            _Database(target, active_admins=1), actor, target.id, UserStatus.disabled
        )


def test_tenant_administrator_cannot_manage_super_admin() -> None:
    actor = _actor("user:manage")
    target = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=actor.org_id,
        roles=[SimpleNamespace(name="Super Admin")],
        status="active",
    )
    with pytest.raises(PermissionDeniedError, match="platform administrator"):
        update_user_status(_Database(target), actor, target.id, UserStatus.disabled)  # type: ignore[arg-type]
