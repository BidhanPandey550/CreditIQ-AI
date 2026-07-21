"""Applicant management and financial profile."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin
from app.shared.enums import TransactionSource


class Applicant(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "applicants"

    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL")
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(300))
    is_self_employed: Mapped[bool] = mapped_column(Boolean, default=False)


class KycRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "kyc_records"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    national_id: Mapped[str | None] = mapped_column(String(50))  # citizenship no.
    document_type: Mapped[str | None] = mapped_column(String(50))
    verification_status: Mapped[str] = mapped_column(String(30), default="pending")
    # MVP verification is simulated — never claim a real government check happened.
    is_simulated_verification: Mapped[bool] = mapped_column(Boolean, default=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)


class EmploymentRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "employment_records"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    employer_name: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[str | None] = mapped_column(String(120))
    monthly_income: Mapped[float | None] = mapped_column(Numeric(18, 2))
    employment_months: Mapped[int | None] = mapped_column()


class BusinessRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "business_records"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    business_name: Mapped[str | None] = mapped_column(String(200))
    business_type: Mapped[str | None] = mapped_column(String(120))
    monthly_revenue: Mapped[float | None] = mapped_column(Numeric(18, 2))
    years_operating: Mapped[float | None] = mapped_column(Numeric(6, 2))


class IncomeRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "income_records"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    frequency: Mapped[str] = mapped_column(String(30), default="monthly")


class ExpenseRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "expense_records"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    frequency: Mapped[str] = mapped_column(String(30), default="monthly")


class AssetRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "asset_records"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str | None] = mapped_column(String(80))
    value: Mapped[float] = mapped_column(Numeric(18, 2))


class LiabilityRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "liability_records"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    outstanding_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    monthly_payment: Mapped[float | None] = mapped_column(Numeric(18, 2))


class ExistingLoan(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "existing_loans"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    lender: Mapped[str | None] = mapped_column(String(150))
    outstanding_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    monthly_installment: Mapped[float | None] = mapped_column(Numeric(18, 2))
    is_delinquent: Mapped[bool] = mapped_column(Boolean, default=False)


class TransactionRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Bank / wallet / utility transactions. SIMULATED for the MVP (is_simulated=True)."""
    __tablename__ = "transaction_records"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[TransactionSource] = mapped_column(String(20))
    txn_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    amount: Mapped[float] = mapped_column(Numeric(18, 2))  # +credit / -debit
    description: Mapped[str | None] = mapped_column(String(200))
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)


class FinancialDocument(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "financial_documents"
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    doc_type: Mapped[str] = mapped_column(String(80))
    storage_key: Mapped[str] = mapped_column(String(300))
    checksum: Mapped[str | None] = mapped_column(String(128))
    scan_status: Mapped[str] = mapped_column(String(30), default="pending")
