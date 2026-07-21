"""Tenant provisioning."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.modules.identity.models import User
from app.modules.identity.service import ensure_rbac
from app.modules.organization.models import Branch, Organization


def onboard_organization(db: Session, data) -> tuple[Organization, User]:
    """Create a tenant, ensure system roles exist, and create its first Administrator."""
    roles = ensure_rbac(db)

    org = Organization(name=data.organization_name, type=data.organization_type)
    db.add(org)
    db.flush()

    branch = Branch(organization_id=org.id, name="Head Office", code="HO")
    db.add(branch)
    db.flush()

    exists = db.scalars(select(User).where(User.email == data.admin_email,
                                           User.organization_id == org.id)).first()
    if exists:
        raise ConflictError("Admin email already used in this organization")

    admin = User(
        organization_id=org.id, branch_id=branch.id, email=data.admin_email,
        full_name=data.admin_full_name, password_hash=hash_password(data.admin_password),
    )
    admin.roles = [roles["Administrator"]]
    db.add(admin)
    db.flush()
    return org, admin
