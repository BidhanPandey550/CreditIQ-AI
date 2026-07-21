"""Configuration loader — the ONLY place that reads config from disk.

Flow:
    1. Detect environment from CREDITIQ_ENV (development | testing | production).
    2. Load config/base.yaml (shared defaults).
    3. Deep-merge config/environments/<env>.yaml (environment overrides).
    4. Apply CREDITIQ_* environment-variable overrides (highest precedence).
    5. Validate into a typed, immutable EngineConfig (records the effective environment).

Every module receives EngineConfig (or a slice of it) via dependency injection. No component
loads YAML on its own.
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from creditiq_ai.config.models import EngineConfig
from creditiq_ai.core.enums import Environment
from creditiq_ai.core.exceptions import ConfigurationError
from creditiq_ai.core.logging import get_logger

logger = get_logger("creditiq_ai.config")

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
ENV_PREFIX = "CREDITIQ_"
ENV_SELECTOR = "CREDITIQ_ENV"


def detect_environment() -> Environment:
    """Resolve the active environment from CREDITIQ_ENV (defaults to development)."""
    raw = os.environ.get(ENV_SELECTOR, Environment.DEVELOPMENT.value).lower()
    try:
        return Environment(raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"Unknown environment '{raw}'", context={"allowed": [e.value for e in Environment]}
        ) from exc


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ConfigurationError(f"{path} must contain a mapping at top level")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """CREDITIQ_RUNTIME__LOG_LEVEL=DEBUG -> config['runtime']['log_level'] = 'DEBUG'."""
    for env_key, raw in os.environ.items():
        if not env_key.startswith(ENV_PREFIX) or env_key == ENV_SELECTOR:
            continue
        path = env_key[len(ENV_PREFIX) :].lower().split("__")
        cursor = config
        for part in path[:-1]:
            cursor = cursor.setdefault(part, {})
            if not isinstance(cursor, dict):
                raise ConfigurationError(
                    f"Env override {env_key} conflicts with a non-mapping node"
                )
        cursor[path[-1]] = _coerce(raw)
    return config


def _coerce(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            continue
    return value


def config_hash(config: EngineConfig) -> str:
    """Deterministic hash of the effective config — recorded with each model version."""
    payload = json.dumps(config.model_dump(mode="json"), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def load_config(
    config_dir: str | Path | None = None, environment: Environment | None = None
) -> EngineConfig:
    """Build a validated EngineConfig from base + environment YAML + env overrides."""
    directory = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    env = environment or detect_environment()

    merged = _read_yaml(directory / "base.yaml")
    merged = _deep_merge(merged, _read_yaml(directory / "environments" / f"{env.value}.yaml"))
    merged = _apply_env_overrides(merged)
    merged["environment"] = env.value

    try:
        return EngineConfig(**merged)
    except Exception as exc:  # pydantic ValidationError et al.
        raise ConfigurationError(
            "Invalid engine configuration", context={"environment": env.value, "error": str(exc)}
        ) from exc


@lru_cache(maxsize=1)
def get_config() -> EngineConfig:
    """Cached default-config accessor (tests call load_config directly for isolation)."""
    return load_config()
