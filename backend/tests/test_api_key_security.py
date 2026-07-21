from __future__ import annotations

import uuid

import pytest

from app.core.deps import CurrentUser
from app.core.exceptions import PermissionDeniedError
from app.modules.integration.service import assignable_scopes, validate_scopes


def _actor(*permissions: str) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        branch_id=None,
        roles=["Administrator"],
        permissions=set(permissions),
    )


def test_api_key_scopes_are_deduplicated_and_normalized() -> None:
    actor = _actor("loan:read", "applicant:read")
    assert validate_scopes(actor, ["loan:read", "applicant:read", "loan:read"]) == [
        "applicant:read",
        "loan:read",
    ]


def test_api_key_cannot_delegate_unheld_permission() -> None:
    with pytest.raises(PermissionDeniedError, match="Cannot delegate"):
        validate_scopes(_actor("loan:read"), ["loan:approve"])


def test_api_key_rejects_unknown_scope() -> None:
    with pytest.raises(PermissionDeniedError, match="Unknown API key scopes"):
        validate_scopes(_actor("loan:read"), ["bank:transfer"])


def test_platform_admin_can_delegate_catalog_permissions() -> None:
    assert validate_scopes(_actor("platform:admin"), ["loan:approve"]) == ["loan:approve"]


def test_assignable_scope_catalog_does_not_disclose_unheld_scopes() -> None:
    assert set(assignable_scopes(_actor("org:configure", "loan:read"))) == {
        "org:configure",
        "loan:read",
    }
