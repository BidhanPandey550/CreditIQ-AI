"""FastAPI application factory."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler
from app.core.logging import configure_logging, get_logger
from app.core.request_context import bind_request_context, reset_request_context

log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    from app.db import bootstrap  # imported here so table metadata is registered first

    try:
        bootstrap.run(do_seed=settings.seed_on_startup)
    except Exception as exc:  # pragma: no cover
        log.exception("Bootstrap failed: %s", exc)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CreditIQ AI — API",
        version="0.1.0",
        description="Loan Management & Credit Intelligence Platform (MVP). "
        "Multi-tenant, RLS-isolated. External integrations are simulated.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        tokens = bind_request_context(
            request.state.request_id,
            request.client.host if request.client else None,
        )
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request.state.request_id
            return response
        finally:
            reset_request_context(tokens)

    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    def root() -> dict:
        return {
            "service": "CreditIQ AI",
            "docs": "/docs",
            "api": settings.api_v1_prefix,
        }

    return app


app = create_app()
