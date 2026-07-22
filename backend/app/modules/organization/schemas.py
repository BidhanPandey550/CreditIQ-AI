from __future__ import annotations

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.shared.enums import OrgType
from app.modules.loan.workflow import LoanWorkflowSettings


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    type: OrgType
    status: str
    nrb_license_no: str | None
    settings: dict
    model_config = {"from_attributes": True}


class BranchOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    address: str | None
    status: str
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


class OrganizationSettings(BaseModel):
    currency: str = Field(default="NPR", min_length=3, max_length=3)
    timezone: str = Field(default="Asia/Kathmandu", max_length=80)
    fiscal_year_start_month: int = Field(default=4, ge=1, le=12)
    loan_workflow: LoanWorkflowSettings = Field(default_factory=LoanWorkflowSettings)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Timezone must be a valid IANA identifier") from exc
        return value


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    nrb_license_no: str | None = Field(default=None, max_length=100)
    settings: OrganizationSettings


class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=1, max_length=30)
    address: str | None = Field(default=None, max_length=300)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Branch code may contain letters, numbers, hyphens, and underscores")
        return normalized


class BranchUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    address: str | None = Field(default=None, max_length=300)
    status: str = Field(pattern="^(active|inactive)$")
