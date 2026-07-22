"""Tenancy: organizations, settings, branches."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.shared.enums import OrgStatus, OrgType


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[OrgType] = mapped_column(String(30), nullable=False)
    status: Mapped[OrgStatus] = mapped_column(String(20), default=OrgStatus.active, nullable=False)
    nrb_license_no: Mapped[str | None] = mapped_column(String(100))
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    branches: Mapped[list["Branch"]] = relationship(back_populates="organization")


class Branch(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "branches"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    address: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="branches")
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_branch_org_code"),)
