from __future__ import annotations

import uuid

import pytest

from app.core.deps import CurrentUser
from app.core.exceptions import PermissionDeniedError
from app.modules.identity.service import assignable_role_names, validate_role_assignment


def _actor(*permissions: str) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        branch_id=None,
        roles=["Super Admin" if "platform:admin" in permissions else "Administrator"],
        permissions=set(permissions),
    )


def test_tenant_administrator_cannot_assign_super_admin() -> None:
    actor = _actor("user:manage")

    with pytest.raises(PermissionDeniedError, match="platform administrator"):
        validate_role_assignment(actor, ["Super Admin"])

    assert "Super Admin" not in assignable_role_names(actor)


def test_platform_administrator_can_assign_super_admin() -> None:
    actor = _actor("platform:admin")

    validate_role_assignment(actor, ["Super Admin"])

    assert "Super Admin" in assignable_role_names(actor)


def test_tenant_administrator_can_assign_tenant_roles() -> None:
    actor = _actor("user:manage")

    validate_role_assignment(actor, ["Loan Officer", "Risk Analyst"])

    assert "Applicant" in assignable_role_names(actor)
