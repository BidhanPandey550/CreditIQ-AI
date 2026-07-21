"""Audit logging and notifications."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TenantMixin):
    """Append-only. Never updated or hard-deleted."""
    __tablename__ = "audit_logs"
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(120), index=True)   # e.g. loan.transition
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(60))
    request_id: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Notification(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "notifications"
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_status: Mapped[str] = mapped_column(String(20), default="delivered")
