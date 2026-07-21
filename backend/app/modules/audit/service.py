"""Append-only audit logging."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.request_context import current_client_ip, current_request_id
from app.modules.audit.models import AuditLog


def record(
    db: Session,
    *,
    org_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
    request_id: str | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=org_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            request_id=request_id or current_request_id(),
            ip_address=ip or current_client_ip(),
        )
    )
