from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.deps import CurrentUser
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.modules.identity.service import _resolve_custom_permissions, create_role, update_role
from app.modules.identity.schemas import RoleUpdate


def _actor(*permissions: str) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        branch_id=None,
        roles=["Administrator"],
        permissions=set(permissions),
    )


class Result:
    def __init__(self, values):
        self.values = list(values)

    def all(self):
        return self.values

    def first(self):
        return self.values[0] if self.values else None


class Database:
    def __init__(self, results):
        self.results = iter(results)
        self.added = []
        self.flushed = False

    def scalars(self, _statement):
        return Result(next(self.results))

    def add(self, value):
        self.added.append(value)
        if getattr(value, "id", None) is None:
            value.id = uuid.uuid4()

    def flush(self):
        self.flushed = True


def test_custom_role_cannot_grant_permission_actor_does_not_hold() -> None:
    actor = _actor("role:manage")
    permission = SimpleNamespace(code="loan:approve")
    with pytest.raises(PermissionDeniedError, match="do not possess"):
        _resolve_custom_permissions(
            Database([[permission]]),  # type: ignore[arg-type]
            actor,
            ["loan:approve"],
        )


def test_custom_role_rejects_unknown_and_duplicate_permissions() -> None:
    actor = _actor("role:manage")
    with pytest.raises(NotFoundError, match="do not exist"):
        _resolve_custom_permissions(Database([[]]), actor, ["missing:permission"])  # type: ignore[arg-type]
    with pytest.raises(ConflictError, match="duplicates"):
        _resolve_custom_permissions(  # type: ignore[arg-type]
            Database([]), actor, ["role:manage", "role:manage"]
        )


def test_tenant_custom_role_is_created_with_normalized_name_and_permissions() -> None:
    actor = _actor("role:manage", "audit:read")
    permissions = [SimpleNamespace(code="audit:read")]
    database = Database([[], permissions])

    role = create_role(
        database,  # type: ignore[arg-type]
        actor,
        "  Compliance   Reviewer ",
        ["audit:read"],
    )

    assert role.organization_id == actor.org_id
    assert role.name == "Compliance Reviewer"
    assert role.is_system is False
    assert role.permissions == permissions
    assert database.flushed


def test_system_role_cannot_be_modified_through_tenant_endpoint() -> None:
    actor = _actor("role:manage")
    system_role = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=actor.org_id,
        name="Administrator",
        is_system=True,
        permissions=[],
    )
    with pytest.raises(PermissionDeniedError, match="System roles"):
        update_role(
            Database([[system_role]]),  # type: ignore[arg-type]
            actor,
            system_role.id,
            name="Changed",
        )


def test_empty_role_update_is_rejected() -> None:
    with pytest.raises(ValidationError, match="At least one"):
        RoleUpdate()
