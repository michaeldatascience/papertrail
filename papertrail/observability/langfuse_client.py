"""Langfuse client wrapper for LLM tracing."""

from __future__ import annotations

from papertrail.config.loader import get_settings


_langfuse = None


def get_langfuse():
    """Get or create the Langfuse client. Returns None if not configured."""
    global _langfuse
    settings = get_settings()
    if not settings.langfuse_secret_key:
        return None
    if _langfuse is None:
        try:
            from langfuse import Langfuse

            _langfuse = Langfuse(
                secret_key=settings.langfuse_secret_key,
                public_key=settings.langfuse_public_key,
                host=settings.langfuse_host,
            )
        except Exception:
            return None
    return _langfuse
