from __future__ import annotations

import sys

import structlog


def configure() -> None:
    if sys.stderr.isatty():
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.BoundLogger:
    return structlog.get_logger()  # type: ignore[no-any-return]
