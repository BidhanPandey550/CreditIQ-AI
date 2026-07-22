from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.shared.enums import UserStatus


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    organization_id: uuid.UUID | None = None  # optional disambiguation for multi-org emails


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class LoginResponse(TokenResponse):
    access_token: str | None = None
    mfa_required: bool = False
    challenge_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class MfaVerifyRequest(BaseModel):
    challenge_token: str
    code: str = Field(pattern=r"^\d{6}$")


class MfaCodeRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class MfaEnrollmentOut(BaseModel):
    secret: str
    provisioning_uri: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)
    role_names: list[str] = Field(default_factory=lambda: ["Loan Officer"])
    branch_id: uuid.UUID | None = None
    applicant_id: uuid.UUID | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    status: str
    roles: list[str]
    branch_id: uuid.UUID | None = None
    applicant_id: uuid.UUID | None = None
    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: uuid.UUID | None = None
    name: str
    assignable: bool = True
    is_system: bool = True
    permissions: list[str] = Field(default_factory=list)


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    permissions: list[str] = Field(min_length=1)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    permissions: list[str] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_change(self) -> "RoleUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one role field must be supplied")
        return self


class UserStatusUpdate(BaseModel):
    status: UserStatus


class MeOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    organization_id: uuid.UUID
    branch_id: uuid.UUID | None
    applicant_id: uuid.UUID | None
    roles: list[str]
    permissions: list[str]
