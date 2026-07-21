"""Branch authorization is defense-in-depth beneath organization-level RLS."""

from __future__ import annotations

import uuid

import pytest

from app.core.data_scope import (
    has_org_wide_scope,
    require_applicant_ownership,
    require_branch_access,
    resolve_creation_branch,
)
from app.core.deps import CurrentUser
from app.core.exceptions import PermissionDeniedError


def _user(role: str, branch_id: uuid.UUID | None = None) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        branch_id=branch_id,
        roles=[role],
        permissions=set(),
    )


def test_loan_officer_is_limited_to_assigned_branch() -> None:
    branch = uuid.uuid4()
    user = _user("Loan Officer", branch)
    require_branch_access(user, branch)
    with pytest.raises(PermissionDeniedError, match="branch scope"):
        require_branch_access(user, uuid.uuid4())


@pytest.mark.parametrize("role", ["Administrator", "Risk Analyst", "Super Admin"])
def test_org_wide_roles_can_review_all_tenant_branches(role: str) -> None:
    user = _user(role, uuid.uuid4())
    assert has_org_wide_scope(user)
    require_branch_access(user, uuid.uuid4())


def test_branch_role_cannot_create_for_another_branch() -> None:
    branch = uuid.uuid4()
    user = _user("Branch Manager", branch)
    assert resolve_creation_branch(user, None) == branch
    with pytest.raises(PermissionDeniedError, match="another branch"):
        resolve_creation_branch(user, uuid.uuid4())


def test_applicant_role_cannot_use_tenant_wide_staff_endpoints() -> None:
    user = _user("Applicant", uuid.uuid4())
    with pytest.raises(PermissionDeniedError):
        require_branch_access(user, user.branch_id)
    with pytest.raises(PermissionDeniedError):
        resolve_creation_branch(user, user.branch_id)


def test_applicant_ownership_allows_only_the_linked_profile() -> None:
    owned = uuid.uuid4()
    user = _user("Applicant")
    user.applicant_id = owned

    require_applicant_ownership(user, owned)
    with pytest.raises(PermissionDeniedError, match="ownership scope"):
        require_applicant_ownership(user, uuid.uuid4())


def test_staff_users_are_not_constrained_by_applicant_ownership() -> None:
    require_applicant_ownership(_user("Loan Officer"), uuid.uuid4())
