"""Multi-instance monitoring adapter contract tests without a live Redis dependency."""

from __future__ import annotations

from creditiq_ai.config import load_config
from creditiq_ai.model_operations import InferenceEvent

from src.serving.redis_monitor import RedisDecisionMonitor


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, list[str]] = {}
        self.operations: list[tuple] = []

    def pipeline(self, *, transaction: bool = True) -> "FakeRedis":
        assert transaction
        self.operations = []
        return self

    def rpush(self, key: str, value: str) -> "FakeRedis":
        self.operations.append(("rpush", key, value))
        return self

    def ltrim(self, key: str, start: int, end: int) -> "FakeRedis":
        self.operations.append(("ltrim", key, start, end))
        return self

    def expire(self, key: str, seconds: int) -> "FakeRedis":
        self.operations.append(("expire", key, seconds))
        return self

    def execute(self) -> None:
        for operation in self.operations:
            if operation[0] == "rpush":
                self.values.setdefault(operation[1], []).append(operation[2])
            elif operation[0] == "ltrim":
                key, start = operation[1], operation[2]
                self.values[key] = self.values.get(key, [])[start:]

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.values.get(key, [])
        return values[start:] if end == -1 else values[start : end + 1]


def test_redis_monitor_aggregates_events_shared_by_instances() -> None:
    client = FakeRedis()
    config = load_config().monitoring.model_copy(update={"retention_events": 2})
    first = RedisDecisionMonitor(client, config, key="events", ttl_seconds=3600)
    second = RedisDecisionMonitor(client, config, key="events", ttl_seconds=3600)

    first.record(InferenceEvent(correlation_id="one", success=True, duration_ms=10))
    second.record(InferenceEvent(correlation_id="two", success=False, duration_ms=30))
    first.record(InferenceEvent(correlation_id="three", success=True, duration_ms=20))

    snapshot = second.snapshot()
    assert snapshot.prediction_count == 2
    assert snapshot.failure_count == 1
    assert snapshot.average_latency_ms == 25
    assert len(client.values["events"]) == 2


def test_redis_monitor_serializes_only_privacy_safe_contract_fields() -> None:
    client = FakeRedis()
    monitor = RedisDecisionMonitor(client, load_config().monitoring, key="events", ttl_seconds=3600)

    monitor.record(InferenceEvent(correlation_id="safe", success=True, duration_ms=5))

    payload = client.values["events"][0]
    assert "applicant" not in payload
    assert "features" not in payload
    assert "safe" in payload
