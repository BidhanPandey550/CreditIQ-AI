"""Redis integration evidence for multi-instance inference telemetry."""

from __future__ import annotations

import os
import uuid

import pytest

from creditiq_ai.config import load_config
from creditiq_ai.model_operations import InferenceEvent

from src.serving.redis_monitor import create_redis_monitor


def test_real_redis_aggregates_across_monitor_instances() -> None:
    url = os.getenv("TEST_REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL is not configured")
    key = f"creditiq:test:inference:{uuid.uuid4()}"
    config = load_config().monitoring.model_copy(update={"retention_events": 10})
    first = create_redis_monitor(url, config, key=key, ttl_seconds=60)
    second = create_redis_monitor(url, config, key=key, ttl_seconds=60)

    first.record(InferenceEvent(correlation_id="replica-a", success=True, duration_ms=10))
    second.record(InferenceEvent(correlation_id="replica-b", success=False, duration_ms=20))

    snapshot = first.snapshot()
    assert snapshot.prediction_count == 2
    assert snapshot.failure_count == 1
    assert snapshot.average_latency_ms == 15
