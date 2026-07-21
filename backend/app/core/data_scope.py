"""Centralized intra-tenant branch authorization policy."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import false

from app.core.deps import CurrentUser
from app.core.exceptions import PermissionDeniedError

ORG_WIDE_ROLES = frozenset({"Administrator", "Risk Analyst", "Super Admin"})


def has_org_wide_scope(user: CurrentUser) -> bool:
    return "platform:admin" in user.permissions or bool(ORG_WIDE_ROLES.intersection(user.roles))


def is_applicant_user(user: CurrentUser) -> bool:
    return "Applicant" in user.roles


def require_applicant_ownership(user: CurrentUser, applicant_id: uuid.UUID) -> None:
    """Reject applicant accounts attempting to access another applicant's records."""
    if is_applicant_user(user) and user.applicant_id != applicant_id:
        raise PermissionDeniedError("Record is outside your applicant ownership scope")


def branch_predicate(user: CurrentUser, branch_column: Any) -> Any:
    """Return a SQL predicate limiting a model to the caller's authorized branch."""
    if has_org_wide_scope(user):
        return True
    if user.branch_id is None or is_applicant_user(user):
        return false()
    return branch_column == user.branch_id


def require_branch_access(user: CurrentUser, branch_id: uuid.UUID | None) -> None:
    """Reject access to a record outside the caller's branch scope."""
    if has_org_wide_scope(user):
        return
    if user.branch_id is None or branch_id != user.branch_id or is_applicant_user(user):
        raise PermissionDeniedError("Record is outside your authorized branch scope")


def resolve_creation_branch(
    user: CurrentUser, requested_branch_id: uuid.UUID | None
) -> uuid.UUID | None:
    """Resolve the new record's branch without allowing branch impersonation."""
    if has_org_wide_scope(user):
        return requested_branch_id or user.branch_id
    if user.branch_id is None or is_applicant_user(user):
        raise PermissionDeniedError("A staff branch assignment is required")
    if requested_branch_id is not None and requested_branch_id != user.branch_id:
        raise PermissionDeniedError("Cannot create records for another branch")
    return user.branch_id
