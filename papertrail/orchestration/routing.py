"""Conditional routing logic for the pipeline state machine."""

from __future__ import annotations

from papertrail.models.pipeline_state import PipelineState


def route_after_classify(state: PipelineState) -> str:
    """Route after classification: proceed, hitl, or error."""
    classification = state.get("classification")
    if not classification:
        return "error"

    playbook = state.get("playbook", {})
    hitl_threshold = (
        playbook.get("classify", {}).get("hitl_threshold", 0.6)
    )

    if classification.get("confidence", 0) < hitl_threshold:
        return "hitl"
    return "proceed"


def route_after_validation(state: PipelineState) -> str:
    """Route after Pass D validation: proceed, retry, or exhausted."""
    result = state.get("pass_d_output")
    if not result:
        return "error"

    if result.get("passed", False):
        return "proceed"

    playbook = state.get("playbook", {})
    max_attempts = (
        playbook.get("validate", {})
        .get("correction", {})
        .get("max_attempts", 3)
    )
    current_attempts = state.get("correction_attempts", 0)

    if current_attempts >= max_attempts:
        return "exhausted"
    return "retry"
