from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    organization_id: uuid.UUID | None = None  # optional disambiguation for multi-org emails


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)
    role_names: list[str] = ["Loan Officer"]
    branch_id: uuid.UUID | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    status: str
    roles: list[str]
    model_config = {"from_attributes": True}


class MeOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    organization_id: uuid.UUID
    branch_id: uuid.UUID | None
    roles: list[str]
    permissions: list[str]
