from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.shared.enums import TransactionSource

FREQUENCY_PATTERN = r"^(daily|weekly|monthly|quarterly|yearly)$"


class IncomeIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source: str = Field(min_length=1, max_length=120)
    amount: float = Field(ge=0)
    frequency: str = Field(default="monthly", pattern=FREQUENCY_PATTERN)


class ExpenseIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: str = Field(min_length=1, max_length=120)
    amount: float = Field(ge=0)
    frequency: str = Field(default="monthly", pattern=FREQUENCY_PATTERN)


class AssetIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = Field(min_length=1, max_length=150)
    category: str | None = None
    value: float = Field(ge=0)


class LiabilityIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = Field(min_length=1, max_length=150)
    outstanding_amount: float = Field(ge=0)
    monthly_payment: float | None = Field(default=None, ge=0)


class ExistingLoanIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    lender: str | None = None
    outstanding_amount: float = Field(ge=0)
    monthly_installment: float | None = Field(default=None, ge=0)
    is_delinquent: bool = False


class EmploymentIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employer_name: str | None = None
    position: str | None = None
    monthly_income: float | None = Field(default=None, ge=0)
    employment_months: int | None = Field(default=None, ge=0, le=1200)


class BusinessIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_name: str | None = Field(default=None, max_length=200)
    business_type: str | None = Field(default=None, max_length=120)
    monthly_revenue: float | None = Field(default=None, ge=0)
    years_operating: float | None = Field(default=None, ge=0, le=200)


class ApplicantCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    date_of_birth: date | None = None
    gender: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    is_self_employed: bool = False
    branch_id: uuid.UUID | None = None
    national_id: str | None = None
    employment: EmploymentIn | None = None
    business: BusinessIn | None = None
    incomes: list[IncomeIn] = Field(default_factory=list)
    expenses: list[ExpenseIn] = Field(default_factory=list)
    assets: list[AssetIn] = Field(default_factory=list)
    liabilities: list[LiabilityIn] = Field(default_factory=list)
    existing_loans: list[ExistingLoanIn] = Field(default_factory=list)


class ApplicantProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=300)
    is_self_employed: bool | None = None
    branch_id: uuid.UUID | None = None
    national_id: str | None = Field(default=None, max_length=50)
    employment: EmploymentIn | None = None
    business: BusinessIn | None = None
    incomes: list[IncomeIn] | None = None
    expenses: list[ExpenseIn] | None = None
    assets: list[AssetIn] | None = None
    liabilities: list[LiabilityIn] | None = None
    existing_loans: list[ExistingLoanIn] | None = None

    @model_validator(mode="after")
    def protect_required_fields(self) -> "ApplicantProfileUpdate":
        if "full_name" in self.model_fields_set and self.full_name is None:
            raise ValueError("Full name cannot be cleared")
        if "is_self_employed" in self.model_fields_set and self.is_self_employed is None:
            raise ValueError("Employment type cannot be cleared")
        return self


class ApplicantProfileOut(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID | None
    full_name: str
    date_of_birth: date | None
    gender: str | None
    phone: str | None
    email: EmailStr | None
    address: str | None
    is_self_employed: bool
    national_id: str | None
    kyc_verification_status: str | None
    employment: EmploymentIn | None
    business: BusinessIn | None
    incomes: list[IncomeIn]
    expenses: list[ExpenseIn]
    assets: list[AssetIn]
    liabilities: list[LiabilityIn]
    existing_loans: list[ExistingLoanIn]


class ApplicantOut(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None
    email: str | None
    is_self_employed: bool
    model_config = {"from_attributes": True}


class FinancialSummary(BaseModel):
    monthly_income: float
    monthly_expenses: float
    monthly_debt_payments: float
    total_assets: float
    total_liabilities: float
    debt_to_income: float
    savings_ratio: float
    net_worth: float


class TransactionOut(BaseModel):
    id: uuid.UUID
    source_type: TransactionSource
    txn_date: datetime
    amount: float
    description: str | None
    is_simulated: bool
    model_config = ConfigDict(from_attributes=True)


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int = Field(ge=0)
    total_credits: float
    total_debits: float
    net_cashflow: float
    simulated_count: int = Field(ge=0)


class FinancialDocumentOut(BaseModel):
    id: uuid.UUID
    applicant_id: uuid.UUID
    doc_type: str
    original_filename: str | None
    content_type: str | None
    size_bytes: int | None
    checksum: str | None
    scan_status: str
    created_at: datetime
    model_config = {"from_attributes": True}
