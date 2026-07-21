"""Audit metadata follows each async-safe request context and is reset afterward."""

from __future__ import annotations

from app.core.request_context import (
    bind_request_context,
    current_client_ip,
    current_request_id,
    reset_request_context,
)
from app.modules.audit.service import record

import uuid


def test_request_context_binds_and_resets_metadata() -> None:
    assert current_request_id() is None
    tokens = bind_request_context("request-123", "192.0.2.10")
    try:
        assert current_request_id() == "request-123"
        assert current_client_ip() == "192.0.2.10"
    finally:
        reset_request_context(tokens)
    assert current_request_id() is None
    assert current_client_ip() is None


def test_audit_record_inherits_request_metadata() -> None:
    captured = []

    class Session:
        def add(self, value) -> None:
            captured.append(value)

    tokens = bind_request_context("request-456", "198.51.100.7")
    try:
        record(
            Session(),
            org_id=uuid.uuid4(),
            actor_user_id=uuid.uuid4(),
            action="loan.test",
        )
    finally:
        reset_request_context(tokens)

    assert captured[0].request_id == "request-456"
    assert captured[0].ip_address == "198.51.100.7"
