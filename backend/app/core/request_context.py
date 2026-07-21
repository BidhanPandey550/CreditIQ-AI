"""Async-safe request metadata available to application and audit services."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)


@dataclass(frozen=True)
class RequestContextTokens:
    request_id: Token[str | None]
    client_ip: Token[str | None]


def bind_request_context(request_id: str, client_ip: str | None) -> RequestContextTokens:
    return RequestContextTokens(_request_id.set(request_id), _client_ip.set(client_ip))


def reset_request_context(tokens: RequestContextTokens) -> None:
    _request_id.reset(tokens.request_id)
    _client_ip.reset(tokens.client_ip)


def current_request_id() -> str | None:
    return _request_id.get()


def current_client_ip() -> str | None:
    return _client_ip.get()
