"""Audit and notification contracts preserve typed compliance metadata."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.modules.audit.schemas import AuditLogOut, NotificationOut


def test_audit_contract_is_machine_readable() -> None:
    event_id = uuid.uuid4()
    result = AuditLogOut(
        id=event_id,
        actor_user_id=None,
        action="loan.transition",
        entity_type="loan",
        entity_id=uuid.uuid4(),
        before={"status": "submitted"},
        after={"status": "under_review"},
        request_id="request-1",
        created_at=datetime.now(UTC),
    )
    assert result.id == event_id
    assert result.after == {"status": "under_review"}


def test_notification_contract_exposes_delivery_and_read_state() -> None:
    result = NotificationOut(
        id=uuid.uuid4(),
        channel="in_app",
        title="Review required",
        body="A high-risk application needs review.",
        is_read=False,
        delivery_status="delivered",
        created_at=datetime.now(UTC),
    )
    assert result.is_read is False
    assert result.delivery_status == "delivered"
