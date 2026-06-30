"""
Logger — standardised JSON-structured logging for CareerPilot AI.

Uses loguru for rich console + file output.
Configures one rotating file sink (logs/careerpilot.log) and
one console sink (stderr) at the level set by LOG_LEVEL env var.

Usage:
    from src.monitoring.logger import get_logger
    log = get_logger(__name__)
    log.info("Agent invoked", agent="resume_agent", latency=0.42)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger as _loguru_logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "careerpilot.log"

_configured = False


def _configure_logger() -> None:
    global _configured
    if _configured:
        return

    # Remove default sink
    _loguru_logger.remove()

    # Console sink — colourised for development
    _loguru_logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File sink — JSON-structured for log aggregators
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _loguru_logger.add(
        str(LOG_FILE),
        level=LOG_LEVEL,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        serialize=True,  # JSON output
        enqueue=True,    # thread-safe async write
    )

    _configured = True


def get_logger(name: str = "careerpilot"):
    """Return a bound loguru logger with the module name pre-attached."""
    _configure_logger()
    return _loguru_logger.bind(module=name)


# Auto-configure on import
_configure_logger()
