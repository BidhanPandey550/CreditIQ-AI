from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.shared.enums import DecisionType, LoanStatus


class LoanCreate(BaseModel):
    applicant_id: uuid.UUID
    amount: float = Field(gt=0)
    tenor_months: int = Field(gt=0, le=360)
    purpose: str | None = None
    product_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None


class LoanProductCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    name: str = Field(min_length=2, max_length=150)
    min_amount: float = Field(gt=0)
    max_amount: float = Field(gt=0)
    min_tenor_months: int = Field(ge=1, le=360)
    max_tenor_months: int = Field(ge=1, le=360)
    interest_rate: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_ranges(self) -> "LoanProductCreate":
        if self.min_amount > self.max_amount:
            raise ValueError("Minimum amount cannot exceed maximum amount")
        if self.min_tenor_months > self.max_tenor_months:
            raise ValueError("Minimum tenor cannot exceed maximum tenor")
        return self


class LoanProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    min_amount: float | None = Field(default=None, gt=0)
    max_amount: float | None = Field(default=None, gt=0)
    min_tenor_months: int | None = Field(default=None, ge=1, le=360)
    max_tenor_months: int | None = Field(default=None, ge=1, le=360)
    interest_rate: float | None = Field(default=None, ge=0, le=100)
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")


class LoanProductOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    min_amount: float
    max_amount: float
    min_tenor_months: int
    max_tenor_months: int
    interest_rate: float
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


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


class DisbursementRequest(BaseModel):
    annual_interest_rate: float | None = Field(default=None, ge=0, le=100)
    first_due_date: date | None = None
    external_reference: str | None = Field(default=None, max_length=120)


class InstallmentOut(BaseModel):
    id: uuid.UUID
    sequence_no: int
    due_date: date
    principal_due: float
    interest_due: float
    principal_paid: float
    interest_paid: float
    paid_at: datetime | None
    days_past_due: int = 0
    outstanding: float = 0
    model_config = {"from_attributes": True}


class RepaymentRequest(BaseModel):
    amount: float = Field(gt=0)
    paid_at: datetime | None = None
    external_reference: str | None = Field(default=None, max_length=120)


class RepaymentOut(BaseModel):
    id: uuid.UUID
    amount: float
    paid_at: datetime
    external_reference: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ServicingSummary(BaseModel):
    original_principal: float
    total_due: float
    total_paid: float
    outstanding: float
    overdue_amount: float
    days_past_due: int
    next_due_date: date | None
    installments: list[InstallmentOut]
    repayments: list[RepaymentOut]
