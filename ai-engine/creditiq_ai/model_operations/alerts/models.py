"""Alert contracts independent of notification delivery vendors."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class ModelAlert(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_ref: str
    severity: str
    code: str
    message: str
    status: str = "open"
    metadata: dict[str, str | float | int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
