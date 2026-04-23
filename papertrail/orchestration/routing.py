"""Conditional routing logic for the pipeline state machine."""

from __future__ import annotations

from papertrail.models.pipeline_state import PipelineState


def route_after_classify(state: PipelineState) -> str:
    """Route after classification: proceed, hitl, or error."""
    classification = state.get("classification")
    if not classification:
        return "error"

    plan = state.get("execution_plan", {})
    hitl_threshold = plan.get("classification", {}).get("confidence_threshold", 0.6)

    if classification.get("confidence", 0) < hitl_threshold:
        return "hitl"
    return "proceed"


def route_after_validation(state: PipelineState) -> str:
    """Route after validation: proceed, retry, or exhausted."""
    result = state.get("validation_result")
    if not result:
        return "error"

    if result.get("passed", False):
        return "proceed"

    plan = state.get("execution_plan", {})
    max_attempts = plan.get("correction", {}).get("max_retries", 3)
    current_attempts = state.get("correction_attempts", 0)

    if current_attempts >= max_attempts:
        return "exhausted"
    return "retry"
