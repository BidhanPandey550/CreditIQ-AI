"""Organization + branch endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require, require_any
from app.core.exceptions import NotFoundError
from app.db.session import admin_session
from app.modules.audit import service as audit
from app.modules.organization import service
from app.modules.organization.models import Branch, Organization
from app.modules.organization.schemas import (
    BranchCreate,
    BranchOut,
    BranchUpdate,
    OnboardRequest,
    OnboardResponse,
    OrganizationOut,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/onboard", response_model=OnboardResponse, status_code=201)
def onboard(
    body: OnboardRequest, user: CurrentUser = Depends(require("platform:admin"))
) -> OnboardResponse:
    # Platform-owner operation; runs outside a single tenant's RLS scope.
    with admin_session() as db:
        org, admin = service.onboard_organization(db, body)
        db.flush()
        return OnboardResponse(organization_id=org.id, admin_user_id=admin.id)


@router.get("/me", response_model=OrganizationOut)
def my_org(
    user: CurrentUser = Depends(require_any("analytics:read", "org:configure")),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    org = db.get(Organization, user.org_id)
    return OrganizationOut.model_validate(org)


@router.get("/branches", response_model=list[BranchOut])
def branches(
    user: CurrentUser = Depends(require_any("analytics:read", "org:configure")),
    db: Session = Depends(get_db),
) -> list[BranchOut]:
    rows = db.scalars(select(Branch).where(Branch.organization_id == user.org_id)).all()
    return [BranchOut.model_validate(b) for b in rows]


@router.put("/me", response_model=OrganizationOut)
def update_my_org(
    body: OrganizationUpdate,
    user: CurrentUser = Depends(require("org:configure")),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    before = db.get(Organization, user.org_id)
    if before is None:
        raise NotFoundError("Organization not found")
    before_snapshot = {
        "name": before.name,
        "nrb_license_no": before.nrb_license_no,
        "settings": before.settings,
    }
    updated = service.update_organization(db, user.org_id, body)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="organization.update",
        entity_type="organization",
        entity_id=updated.id,
        before=before_snapshot,
        after={
            "name": updated.name,
            "nrb_license_no": updated.nrb_license_no,
            "settings": updated.settings,
        },
    )
    return OrganizationOut.model_validate(updated)


@router.post("/branches", response_model=BranchOut, status_code=201)
def create_branch(
    body: BranchCreate,
    user: CurrentUser = Depends(require("org:configure")),
    db: Session = Depends(get_db),
) -> BranchOut:
    branch = service.create_branch(db, user.org_id, body)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="branch.create",
        entity_type="branch",
        entity_id=branch.id,
        after={"name": branch.name, "code": branch.code, "status": branch.status},
    )
    return BranchOut.model_validate(branch)


@router.put("/branches/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: uuid.UUID,
    body: BranchUpdate,
    user: CurrentUser = Depends(require("org:configure")),
    db: Session = Depends(get_db),
) -> BranchOut:
    current = db.get(Branch, branch_id)
    if current is None or current.organization_id != user.org_id:
        raise NotFoundError("Branch not found in this organization")
    before = {"name": current.name, "address": current.address, "status": current.status}
    branch = service.update_branch(db, user.org_id, branch_id, body)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="branch.update",
        entity_type="branch",
        entity_id=branch.id,
        before=before,
        after={"name": branch.name, "address": branch.address, "status": branch.status},
    )
    return BranchOut.model_validate(branch)
