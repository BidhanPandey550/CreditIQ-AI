from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class IncomeIn(BaseModel):
    source: str
    amount: float
    frequency: str = "monthly"


class ExpenseIn(BaseModel):
    category: str
    amount: float
    frequency: str = "monthly"


class AssetIn(BaseModel):
    name: str
    category: str | None = None
    value: float


class LiabilityIn(BaseModel):
    name: str
    outstanding_amount: float
    monthly_payment: float | None = None


class ExistingLoanIn(BaseModel):
    lender: str | None = None
    outstanding_amount: float
    monthly_installment: float | None = None
    is_delinquent: bool = False


class EmploymentIn(BaseModel):
    employer_name: str | None = None
    position: str | None = None
    monthly_income: float | None = None
    employment_months: int | None = None


class ApplicantCreate(BaseModel):
    full_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    is_self_employed: bool = False
    branch_id: uuid.UUID | None = None
    national_id: str | None = None
    employment: EmploymentIn | None = None
    incomes: list[IncomeIn] = []
    expenses: list[ExpenseIn] = []
    assets: list[AssetIn] = []
    liabilities: list[LiabilityIn] = []
    existing_loans: list[ExistingLoanIn] = []


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
