"""Abuse controls must be atomic, explicit, and fail closed."""

from __future__ import annotations

import pytest
from redis.exceptions import ConnectionError

from app.core.exceptions import RateLimitExceededError, ServiceUnavailableError
from app.core.rate_limit import RedisRateLimiter


class FakeRedis:
    def __init__(self, results: list[tuple[int, int]] | None = None, error=None) -> None:
        self.results = list(results or [])
        self.error = error

    def eval(self, script, key_count, key, window):
        if self.error:
            raise self.error
        return self.results.pop(0)


def test_rate_limit_allows_requests_within_policy() -> None:
    limiter = RedisRateLimiter(FakeRedis(results=[(1, 60), (10, 42)]))
    limiter.enforce("login:ip", 10, 60)
    limiter.enforce("login:ip", 10, 60)


def test_rate_limit_exposes_retry_delay() -> None:
    limiter = RedisRateLimiter(FakeRedis(results=[(11, 37)]))
    with pytest.raises(RateLimitExceededError) as captured:
        limiter.enforce("login:ip", 10, 60)
    assert captured.value.retry_after == 37


def test_rate_limit_fails_closed_when_redis_is_unavailable() -> None:
    limiter = RedisRateLimiter(FakeRedis(error=ConnectionError("offline")))
    with pytest.raises(ServiceUnavailableError, match="protection"):
        limiter.enforce("login:ip", 10, 60)
