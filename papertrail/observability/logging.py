"""Structured logging configuration and trace event emitter."""

from __future__ import annotations

import structlog
from papertrail.config.loader import get_settings


def configure_logging() -> None:
    """Configure structlog for JSON output."""
    settings = get_settings()
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
            getattr(structlog, settings.log_level.upper(), structlog.INFO)  # type: ignore
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()


async def emit(
    run_id: str,
    stage: str,
    event: str,
    level: str = "info",
    trace_repo=None,
    **payload,
) -> None:
    """Emit an event to structlog and optionally to the trace_events table."""
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
