"""Enterprise logging built on Loguru.

Purpose:  A single place to configure logging sinks and hand out bound loggers. Sinks:
            - console (colourised, level-filtered)
            - rotating application file  (all records)
            - error file                (ERROR+)
            - training / inference / pipeline files (filtered by bound ``channel``)
Inputs:   log directory, level, rotation/retention (from config; sane defaults otherwise).
Outputs:  configured global logger; per-module bound loggers via get_logger().
Deps:     loguru.
Extend:   add another channel by adding a sink with a channel filter + a Channel constant.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Final

from loguru import logger

# --- Named defaults (no magic values inline) ---
DEFAULT_LEVEL: Final[str] = "INFO"
DEFAULT_ROTATION: Final[str] = "10 MB"
DEFAULT_RETENTION: Final[str] = "14 days"
DEFAULT_COMPRESSION: Final[str] = "zip"
DEFAULT_LOG_DIR: Final[str] = "logs"

_CONSOLE_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
    "<cyan>{extra[name]}</cyan> | {message}"
)
_FILE_FORMAT: Final[str] = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[channel]} | {extra[name]} | {message}"
)

# Domain channels get their own log file.
CHANNEL_APP: Final[str] = "app"
CHANNEL_TRAINING: Final[str] = "training"
CHANNEL_INFERENCE: Final[str] = "inference"
CHANNEL_PIPELINE: Final[str] = "pipeline"

_configured: bool = False


def _channel_filter(channel: str) -> Callable[[Any], bool]:
    """Sink filter: only records bound to ``channel`` pass."""

    def _f(record: Any) -> bool:
        return record["extra"].get("channel") == channel

    return _f


def configure_logging(
    *,
    log_dir: str | Path = DEFAULT_LOG_DIR,
    level: str = DEFAULT_LEVEL,
    rotation: str = DEFAULT_ROTATION,
    retention: str = DEFAULT_RETENTION,
    compression: str = DEFAULT_COMPRESSION,
    console: bool = True,
    enqueue: bool = True,
) -> None:
    """(Re)configure all logging sinks. Idempotent — safe to call again with new settings.

    ``enqueue`` makes writes async/process-safe in production; pass False for synchronous
    writes (e.g. in tests that assert on file contents immediately).
    """
    global _configured
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)

    logger.remove()
    # Default bound context so format placeholders never KeyError.
    logger.configure(extra={"name": "creditiq_ai", "channel": CHANNEL_APP})

    if console:
        logger.add(sys.stdout, level=level, format=_CONSOLE_FORMAT, colorize=True, enqueue=enqueue)

    common: dict[str, Any] = dict(
        rotation=rotation,
        retention=retention,
        compression=compression,
        format=_FILE_FORMAT,
        enqueue=enqueue,
        backtrace=True,
        diagnose=False,
    )

    logger.add(directory / "app.log", level=level, **common)
    logger.add(directory / "errors.log", level="ERROR", **common)
    logger.add(
        directory / "training.log", level=level, filter=_channel_filter(CHANNEL_TRAINING), **common
    )
    logger.add(
        directory / "inference.log",
        level=level,
        filter=_channel_filter(CHANNEL_INFERENCE),
        **common,
    )
    logger.add(
        directory / "pipeline.log", level=level, filter=_channel_filter(CHANNEL_PIPELINE), **common
    )

    _configured = True


def get_logger(name: str, channel: str = CHANNEL_APP) -> Any:
    """Return a Loguru logger bound with a component ``name`` and log ``channel``.

    Lazily configures defaults on first use so importing modules never crashes.
    """
    if not _configured:
        configure_logging()
    return logger.bind(name=name, channel=channel)
