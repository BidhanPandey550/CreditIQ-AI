"""Redis-backed, multi-instance inference monitoring adapter."""

from __future__ import annotations

from typing import Protocol

from creditiq_ai.config.models import MonitoringConfig
from creditiq_ai.model_operations import InferenceEvent, MonitoringSnapshot
from creditiq_ai.model_operations.monitoring import aggregate_events


class RedisPipeline(Protocol):
    def rpush(self, key: str, value: str) -> "RedisPipeline": ...

    def ltrim(self, key: str, start: int, end: int) -> "RedisPipeline": ...

    def expire(self, key: str, seconds: int) -> "RedisPipeline": ...

    def execute(self) -> object: ...


class RedisClient(Protocol):
    def pipeline(self, *, transaction: bool = True) -> RedisPipeline: ...

    def lrange(self, key: str, start: int, end: int) -> list[bytes | str]: ...


class DecisionMonitor(Protocol):
    def record(self, event: InferenceEvent) -> None: ...

    def snapshot(self) -> MonitoringSnapshot: ...


class RedisDecisionMonitor:
    """Persist a bounded, privacy-safe event window shared by all serving replicas."""

    def __init__(
        self,
        client: RedisClient,
        config: MonitoringConfig,
        *,
        key: str,
        ttl_seconds: int,
    ) -> None:
        self._client = client
        self._config = config
        self._key = key
        self._ttl_seconds = ttl_seconds

    def record(self, event: InferenceEvent) -> None:
        """Atomically append, bound, and expire one serialized event."""
        if not self._config.enabled:
            return
        pipeline = self._client.pipeline(transaction=True)
        pipeline.rpush(self._key, event.model_dump_json())
        pipeline.ltrim(self._key, -self._config.retention_events, -1)
        pipeline.expire(self._key, self._ttl_seconds)
        pipeline.execute()

    def snapshot(self) -> MonitoringSnapshot:
        """Aggregate the current shared event window."""
        raw_events = self._client.lrange(self._key, 0, -1)
        events = [
            InferenceEvent.model_validate_json(
                item.decode("utf-8") if isinstance(item, bytes) else item
            )
            for item in raw_events
        ]
        return aggregate_events(events, self._config)


def create_redis_monitor(
    url: str, config: MonitoringConfig, *, key: str, ttl_seconds: int
) -> RedisDecisionMonitor:
    """Create the production adapter while keeping Redis optional for library consumers."""
    from redis import Redis

    client = Redis.from_url(url, decode_responses=False)
    client.ping()
    return RedisDecisionMonitor(client, config, key=key, ttl_seconds=ttl_seconds)
