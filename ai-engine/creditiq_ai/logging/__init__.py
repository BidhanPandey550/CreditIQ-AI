"""creditiq_ai.logging — Loguru-based enterprise logging.

Usage:
    from creditiq_ai.logging import get_logger
    log = get_logger(__name__)
    log.info("hello")

    training_log = get_logger("trainer", channel="training")  # → training.log
"""

from creditiq_ai.logging.logger import (
    CHANNEL_APP,
    CHANNEL_INFERENCE,
    CHANNEL_PIPELINE,
    CHANNEL_TRAINING,
    configure_logging,
    get_logger,
)

__all__ = [
    "get_logger",
    "configure_logging",
    "CHANNEL_APP",
    "CHANNEL_TRAINING",
    "CHANNEL_INFERENCE",
    "CHANNEL_PIPELINE",
]
