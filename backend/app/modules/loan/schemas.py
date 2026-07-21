from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.enums import DecisionType, LoanStatus


class LoanCreate(BaseModel):
    applicant_id: uuid.UUID
    amount: float = Field(gt=0)
    tenor_months: int = Field(gt=0, le=360)
    purpose: str | None = None
    product_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None


class LoanOut(BaseModel):
    id: uuid.UUID
    reference_no: str
    applicant_id: uuid.UUID
    amount: float
    tenor_months: int
    status: LoanStatus
    created_at: datetime
    model_config = {"from_attributes": True}


class TransitionRequest(BaseModel):
    to_status: LoanStatus
    reason: str | None = None


class DecisionRequest(BaseModel):
    decision: DecisionType
    rationale: str | None = None
    conditions: str | None = None


class WorkflowEventOut(BaseModel):
    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime
    model_config = {"from_attributes": True}
