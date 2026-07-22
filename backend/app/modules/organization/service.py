"""Tenant provisioning."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.identity.models import User
from app.modules.identity.service import ensure_rbac
from app.modules.organization.models import Branch, Organization
from app.modules.organization.schemas import (
    BranchCreate,
    BranchUpdate,
    OrganizationUpdate,
)


def require_branch(db: Session, org_id: uuid.UUID, branch_id: uuid.UUID | None) -> None:
    """Validate that a requested branch belongs to the active organization."""
    if branch_id is None:
        return
    exists = db.scalars(
        select(Branch.id).where(
            Branch.id == branch_id,
            Branch.organization_id == org_id,
            Branch.status == "active",
        )
    ).first()
    if exists is None:
        raise NotFoundError("Branch not found in this organization")


def update_organization(db: Session, org_id: uuid.UUID, data: OrganizationUpdate) -> Organization:
    organization = db.get(Organization, org_id)
    if organization is None or organization.id != org_id:
        raise NotFoundError("Organization not found")
    organization.name = data.name.strip()
    organization.nrb_license_no = data.nrb_license_no.strip() if data.nrb_license_no else None
    organization.settings = data.settings.model_dump()
    db.flush()
    return organization


def create_branch(db: Session, org_id: uuid.UUID, data: BranchCreate) -> Branch:
    duplicate = db.scalars(
        select(Branch.id).where(Branch.organization_id == org_id, Branch.code == data.code)
    ).first()
    if duplicate is not None:
        raise ConflictError("Branch code already exists in this organization")
    branch = Branch(
        organization_id=org_id,
        name=data.name.strip(),
        code=data.code,
        address=data.address.strip() if data.address else None,
        status="active",
    )
    db.add(branch)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Branch code already exists in this organization") from exc
    return branch


def update_branch(
    db: Session, org_id: uuid.UUID, branch_id: uuid.UUID, data: BranchUpdate
) -> Branch:
    branch = db.get(Branch, branch_id)
    if branch is None or branch.organization_id != org_id:
        raise NotFoundError("Branch not found in this organization")
    branch.name = data.name.strip()
    branch.address = data.address.strip() if data.address else None
    branch.status = data.status
    db.flush()
    return branch


def onboard_organization(db: Session, data) -> tuple[Organization, User]:
    """Create a tenant, ensure system roles exist, and create its first Administrator."""
    roles = ensure_rbac(db)

    org = Organization(name=data.organization_name, type=data.organization_type)
    db.add(org)
    db.flush()

    branch = Branch(organization_id=org.id, name="Head Office", code="HO")
    db.add(branch)
    db.flush()

    exists = db.scalars(
        select(User).where(User.email == data.admin_email, User.organization_id == org.id)
    ).first()
    if exists:
        raise ConflictError("Admin email already used in this organization")

    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        email=data.admin_email,
        full_name=data.admin_full_name,
        password_hash=hash_password(data.admin_password),
    )
    admin.roles = [roles["Administrator"]]
    db.add(admin)
    db.flush()
    return org, admin
