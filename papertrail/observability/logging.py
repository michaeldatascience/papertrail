"""Structured logging configuration and trace event emitter."""

from __future__ import annotations

import logging
from typing import Any

try:
    import structlog
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    structlog = None  # type: ignore[assignment]

from papertrail.config.loader import get_settings


def configure_logging() -> None:
    """Configure structured logging when structlog is available."""
    settings = get_settings()
    if structlog is None:
        logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
        return

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, settings.log_level.upper(), structlog.INFO)  # type: ignore[attr-defined]
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


if structlog is None:
    logger = logging.getLogger("papertrail")
else:
    logger = structlog.get_logger()


async def emit(
    run_id: str,
    stage: str,
    event: str,
    level: str = "info",
    trace_repo: Any = None,
    **payload: Any,
) -> None:
    """Emit an event to structured logging and optionally to the trace_events table."""
    if structlog is None:
        message = {"run_id": run_id, "stage": stage, "event": event, **payload}
        getattr(logger, level if hasattr(logger, level) else "info")(message)
    else:
        bound = logger.bind(run_id=run_id, stage=stage, event=event)
        log_method = getattr(bound, level, bound.info)
        log_method(event, **payload)

    if trace_repo is not None:
        await trace_repo.emit(
            run_id=run_id,
            stage=stage,
            event_type=event,
            level=level,
            payload=payload if payload else None,
        )
