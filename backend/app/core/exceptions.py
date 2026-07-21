"""Domain/application exceptions mapped to RFC 7807 problem+json responses."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error."""

    status_code = 400
    title = "Bad Request"

    def __init__(self, detail: str, *, errors: list[dict] | None = None):
        self.detail = detail
        self.errors = errors or []
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = 404
    title = "Not Found"


class ConflictError(AppError):
    status_code = 409
    title = "Conflict"


class AuthenticationError(AppError):
    status_code = 401
    title = "Unauthorized"


class PermissionDeniedError(AppError):
    status_code = 403
    title = "Forbidden"


class ValidationError(AppError):
    status_code = 422
    title = "Unprocessable Entity"


class ServiceUnavailableError(AppError):
    """A required downstream service cannot safely fulfill the request."""

    status_code = 503
    title = "Service Unavailable"


class RateLimitExceededError(AppError):
    """A caller exceeded an abuse-control policy."""

    status_code = 429
    title = "Too Many Requests"

    def __init__(self, detail: str, *, retry_after: int):
        self.retry_after = retry_after
        super().__init__(detail)


class DomainRuleError(AppError):
    """A business invariant was violated (e.g. illegal loan state transition)."""

    status_code = 409
    title = "Business Rule Violation"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    headers = {}
    if isinstance(exc, RateLimitExceededError):
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"about:blank#{exc.__class__.__name__}",
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "errors": exc.errors,
            "request_id": getattr(request.state, "request_id", None),
        },
        media_type="application/problem+json",
        headers=headers,
    )
