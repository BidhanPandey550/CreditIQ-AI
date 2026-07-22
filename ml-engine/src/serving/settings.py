"""Validated environment configuration for the ML serving process."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServingSettings(BaseModel):
    """Startup policy for development and production model loading."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: Literal["development", "testing", "production"] = "development"
    registry_path: Path | None = None
    model_name: str = Field(default="credit-risk", min_length=1)
    model_environment: str = Field(default="production", min_length=1)
    monitoring_backend: Literal["memory", "redis"] = "memory"
    redis_url: str | None = None
    monitoring_key: str = Field(default="creditiq:ml:inference-events", min_length=1)
    monitoring_ttl_seconds: int = Field(default=604800, ge=60)

    @model_validator(mode="after")
    def require_production_registry(self) -> "ServingSettings":
        if self.environment == "production" and self.registry_path is None:
            raise ValueError("ML_SERVING_REGISTRY_PATH is required in production")
        if self.environment == "production" and self.monitoring_backend != "redis":
            raise ValueError("ML_SERVING_MONITORING_BACKEND=redis is required in production")
        if self.monitoring_backend == "redis" and not self.redis_url:
            raise ValueError("ML_SERVING_REDIS_URL is required for Redis monitoring")
        return self

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "ServingSettings":
        """Build settings from the process environment without global mutable state."""
        source = os.environ if environ is None else environ
        registry = source.get("ML_SERVING_REGISTRY_PATH")
        return cls(
            environment=source.get("ML_SERVING_ENVIRONMENT", "development").lower(),
            registry_path=Path(registry) if registry else None,
            model_name=source.get("ML_SERVING_MODEL_NAME", "credit-risk"),
            model_environment=source.get("ML_SERVING_MODEL_ENVIRONMENT", "production"),
            monitoring_backend=source.get("ML_SERVING_MONITORING_BACKEND", "memory").lower(),
            redis_url=source.get("ML_SERVING_REDIS_URL"),
            monitoring_key=source.get("ML_SERVING_MONITORING_KEY", "creditiq:ml:inference-events"),
            monitoring_ttl_seconds=int(source.get("ML_SERVING_MONITORING_TTL_SECONDS", "604800")),
        )
