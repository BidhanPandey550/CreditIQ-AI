"""API contracts for fraud alert investigation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.shared.enums import FraudSeverity, FraudStatus


class FraudAlertResolution(BaseModel):
    status: Literal[FraudStatus.confirmed, FraudStatus.dismissed]
    note: str = Field(min_length=10, max_length=2000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 10:
            raise ValueError(
                "Resolution rationale must contain at least 10 non-whitespace characters"
            )
        return normalized


class FraudAlertOut(BaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    loan_reference: str
    applicant_id: uuid.UUID
    applicant_name: str
    severity: FraudSeverity
    status: FraudStatus
    reasons: list[str]
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    resolution_note: str | None
    created_at: datetime
