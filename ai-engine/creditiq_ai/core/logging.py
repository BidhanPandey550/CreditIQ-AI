"""Compatibility shim. Canonical logging now lives in ``creditiq_ai.logging`` (Loguru).

Kept so existing imports (``from creditiq_ai.core.logging import get_logger``) keep working
after the Sprint 1 restructure. New code should import from ``creditiq_ai.logging``.
"""

from creditiq_ai.logging import configure_logging, get_logger  # noqa: F401

__all__ = ["get_logger", "configure_logging"]
