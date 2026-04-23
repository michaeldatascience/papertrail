"""Pipeline state definition for LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # Identity
    run_id: str
    run_uid: str
    project_id: str
    playbook_id: str

    # Compiled execution plan
    execution_plan: dict[str, Any] | None

    # Legacy compatibility payloads (temporary)
    playbook: dict[str, Any] | None

    # Input
    input_file_uri: str
    input_file_hash: str
    input_file_mime: str

    # Stage results
    preupload_result: dict[str, Any] | None
    classification: dict[str, Any] | None
    layout_output: dict[str, Any] | None
    text_output: dict[str, Any] | None
    extraction_output: dict[str, Any] | None
    validation_result: dict[str, Any] | None

    # Correction loop state
    correction_attempts: int
    correction_history: list[dict[str, Any]]

    # Decision
    decision_result: dict[str, Any] | None
    postprocess_result: dict[str, Any] | None

    # HITL
    awaiting_hitl: bool
    hitl_checkpoint_type: str | None
    hitl_context: dict[str, Any] | None

    # Confidence accumulator
    confidence_budget: float
    warnings: list[dict[str, Any]]

    # Error state
    error: str | None
    failed_stage: str | None
