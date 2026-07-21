from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(min_length=1)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def expiration_is_future(self) -> "APIKeyCreate":
        from app.db.base import utcnow

        if self.expires_at is not None and self.expires_at <= utcnow():
            raise ValueError("expires_at must be in the future")
        return self


class APIKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class APIKeyCreated(APIKeyOut):
    key: str
