"""Redis-backed fixed-window abuse controls for sensitive and expensive endpoints."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError, ServiceUnavailableError
from app.core.logging import get_logger

log = get_logger("rate_limit")

_INCREMENT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


class RedisRateLimiter:
    """Atomic fixed-window counter with fail-closed behavior for protected operations."""

    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or Redis.from_url(settings.redis_url, decode_responses=True)

    def enforce(self, key: str, limit: int, window_seconds: int) -> None:
        try:
            count, ttl = self._client.eval(_INCREMENT_SCRIPT, 1, key, window_seconds)
        except RedisError as exc:
            log.error("Rate-limit store unavailable: %s", exc)
            raise ServiceUnavailableError(
                "Request protection is temporarily unavailable; retry shortly."
            ) from exc
        if int(count) > limit:
            retry_after = max(1, int(ttl))
            raise RateLimitExceededError(
                "Request rate limit exceeded. Retry after the indicated delay.",
                retry_after=retry_after,
            )


limiter = RedisRateLimiter()


def rate_limit(scope: str, limit: int) -> Callable[[Request], None]:
    """Build a FastAPI dependency keyed by trusted client address and policy scope."""

    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        limiter.enforce(
            f"creditiq:rate:{scope}:{client_ip}",
            limit,
            settings.rate_limit_window_seconds,
        )

    return dependency
