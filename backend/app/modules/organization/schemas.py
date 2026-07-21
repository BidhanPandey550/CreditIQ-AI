from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr

from app.shared.enums import OrgType


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    type: OrgType
    status: str
    model_config = {"from_attributes": True}


class BranchOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    model_config = {"from_attributes": True}


class OnboardRequest(BaseModel):
    """Provision a new tenant + its first Administrator (super-admin operation)."""

    organization_name: str
    organization_type: OrgType = OrgType.mfi
    admin_email: EmailStr
    admin_full_name: str
    admin_password: str


class OnboardResponse(BaseModel):
    organization_id: uuid.UUID
    admin_user_id: uuid.UUID
