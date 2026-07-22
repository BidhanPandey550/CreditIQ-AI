"""Platform organization switching preserves home identity and never weakens tenant scope."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.deps import CurrentUser, get_active_current_user
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import create_access_token, decode_token
from app.modules.organization.schemas import OnboardRequest


def _record(user_id: uuid.UUID, home_org_id: uuid.UUID, permissions: set[str]):
    return SimpleNamespace(
        id=user_id,
        organization_id=home_org_id,
        branch_id=uuid.uuid4(),
        applicant_id=None,
        status="active",
        roles=[
            SimpleNamespace(
                name="Super Admin" if "platform:admin" in permissions else "Administrator",
                permissions=[SimpleNamespace(code=code) for code in permissions],
            )
        ],
    )


def _install_session(monkeypatch, record, *, organization_status: str = "active") -> None:
    class Result:
        def first(self):
            return record

    @contextmanager
    def session(_org_id):
        yield SimpleNamespace(
            scalars=lambda _statement: Result(),
            get=lambda _model, _record_id: SimpleNamespace(status=organization_status),
        )

    monkeypatch.setattr("app.db.session.tenant_session", session)


def test_access_token_carries_home_and_effective_organization() -> None:
    home = uuid.uuid4()
    effective = uuid.uuid4()
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        org_id=str(effective),
        home_org_id=str(home),
        branch_id=None,
        applicant_id=None,
        roles=["Super Admin"],
        permissions=["platform:admin"],
    )

    payload = decode_token(token)

    assert payload["org_id"] == str(effective)
    assert payload["home_org_id"] == str(home)


def test_live_super_admin_permission_allows_effective_tenant_scope(monkeypatch) -> None:
    user_id, home, target = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    record = _record(user_id, home, {"platform:admin", "loan:read"})
    _install_session(monkeypatch, record)

    resolved = get_active_current_user(
        CurrentUser(
            user_id=user_id,
            org_id=target,
            home_org_id=home,
            branch_id=None,
        )
    )

    assert resolved.org_id == target
    assert resolved.home_org_id == home
    assert resolved.branch_id is None
    assert resolved.has("loan:read")


def test_role_revocation_immediately_blocks_switched_tenant_scope(monkeypatch) -> None:
    user_id, home, target = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    record = _record(user_id, home, {"org:configure"})
    _install_session(monkeypatch, record)

    with pytest.raises(PermissionDeniedError, match="platform administrator"):
        get_active_current_user(
            CurrentUser(
                user_id=user_id,
                org_id=target,
                home_org_id=home,
                branch_id=None,
            )
        )


def test_suspended_effective_tenant_rejects_existing_access_token(monkeypatch) -> None:
    user_id, home, target = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    record = _record(user_id, home, {"platform:admin"})
    _install_session(monkeypatch, record, organization_status="suspended")

    with pytest.raises(AuthenticationError, match="Organization is not active"):
        get_active_current_user(
            CurrentUser(
                user_id=user_id,
                org_id=target,
                home_org_id=home,
                branch_id=None,
            )
        )


def test_onboarding_requires_a_strong_temporary_password() -> None:
    with pytest.raises(ValidationError, match="at least 12 characters"):
        OnboardRequest(
            organization_name="Example MFI",
            admin_email="admin@example.test",
            admin_full_name="Tenant Administrator",
            admin_password="too-short",
        )
