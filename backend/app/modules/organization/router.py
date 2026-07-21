"""Organization + branch endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.db.session import admin_session
from app.modules.organization import service
from app.modules.organization.models import Branch, Organization
from app.modules.organization.schemas import (
    BranchOut,
    OnboardRequest,
    OnboardResponse,
    OrganizationOut,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/onboard", response_model=OnboardResponse, status_code=201)
def onboard(body: OnboardRequest,
            user: CurrentUser = Depends(require("platform:admin"))) -> OnboardResponse:
    # Platform-owner operation; runs outside a single tenant's RLS scope.
    with admin_session() as db:
        org, admin = service.onboard_organization(db, body)
        db.flush()
        return OnboardResponse(organization_id=org.id, admin_user_id=admin.id)


@router.get("/me", response_model=OrganizationOut)
def my_org(user: CurrentUser = Depends(require("analytics:read")),
           db: Session = Depends(get_db)) -> OrganizationOut:
    org = db.get(Organization, user.org_id)
    return OrganizationOut.model_validate(org)


@router.get("/branches", response_model=list[BranchOut])
def branches(user: CurrentUser = Depends(require("analytics:read")),
             db: Session = Depends(get_db)) -> list[BranchOut]:
    rows = db.scalars(select(Branch).where(Branch.organization_id == user.org_id)).all()
    return [BranchOut.model_validate(b) for b in rows]
