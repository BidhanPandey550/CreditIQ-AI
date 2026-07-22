"""Loan products, applications, workflow events, decisions."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin
from app.shared.enums import DecisionType, LoanStatus


class LoanProduct(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "loan_products"
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(150))
    min_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    max_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    min_tenor_months: Mapped[int] = mapped_column(Integer, default=3)
    max_tenor_months: Mapped[int] = mapped_column(Integer, default=60)
    interest_rate: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_loan_product_org_code"),)


class LoanApplication(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "loan_applications"

    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL")
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicants.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_products.id", ondelete="SET NULL")
    )
    reference_no: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    tenor_months: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[LoanStatus] = mapped_column(String(30), default=LoanStatus.draft, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class LoanWorkflowEvent(Base, UUIDMixin, TenantMixin):
    __tablename__ = "loan_workflow_events"
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoanDecision(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "loan_decisions"
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    decision: Mapped[DecisionType] = mapped_column(String(30))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    rationale: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[str | None] = mapped_column(Text)


class LoanDisbursement(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "loan_disbursements"

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    annual_interest_rate: Mapped[float] = mapped_column(Numeric(8, 5), nullable=False)
    disbursed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(120))
    disbursed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class LoanInstallment(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "loan_installments"

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    principal_due: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    interest_due: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    principal_paid: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    interest_paid: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("loan_id", "sequence_no", name="uq_installment_loan_sequence"),
    )


class LoanRepayment(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "loan_repayments"

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(120))
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "external_reference",
            name="uq_repayment_org_external_reference",
        ),
    )
