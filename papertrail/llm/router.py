"""Per-stage model selection."""

from __future__ import annotations

from papertrail.config.loader import load_json_config


def get_model_for_stage(stage: str) -> tuple[str, str]:
    """Return (primary, fallback) model names for a stage."""
    config = load_json_config("llm.json")
    stage_config = config["stages"].get(stage, config["stages"]["extract"])
    return stage_config["primary"], stage_config["fallback"]
