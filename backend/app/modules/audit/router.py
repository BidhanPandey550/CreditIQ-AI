"""Tenant-scoped compliance audit and in-app notification APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.core.exceptions import NotFoundError
from app.modules.audit.models import AuditLog, Notification
from app.modules.audit.schemas import AuditLogOut, NotificationOut

audit_router = APIRouter(prefix="/audit", tags=["audit"])
notification_router = APIRouter(prefix="/notifications", tags=["notifications"])


@audit_router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    action: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(require("audit:read")),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    statement = select(AuditLog).where(AuditLog.organization_id == user.org_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    rows = db.scalars(
        statement.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return [AuditLogOut.model_validate(row) for row in rows]


@notification_router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    user: CurrentUser = Depends(require("notification:read")),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    statement = select(Notification).where(
        Notification.organization_id == user.org_id,
        (Notification.user_id == user.user_id) | (Notification.user_id.is_(None)),
    )
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))
    rows = db.scalars(statement.order_by(Notification.created_at.desc()).limit(100)).all()
    return [NotificationOut.model_validate(row) for row in rows]


@notification_router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    user: CurrentUser = Depends(require("notification:read")),
    db: Session = Depends(get_db),
) -> NotificationOut:
    notification = db.scalars(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == user.org_id,
            (Notification.user_id == user.user_id) | (Notification.user_id.is_(None)),
        )
    ).first()
    if not notification:
        raise NotFoundError("Notification not found")
    notification.is_read = True
    db.flush()
    return NotificationOut.model_validate(notification)
