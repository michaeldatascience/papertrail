"""Pipeline state definition for LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # Identity
    run_id: str
    run_uid: str
    playbook_id: str

    # Playbook (merged with _base)
    playbook: dict[str, Any]

    # Input
    input_file_uri: str
    input_file_hash: str
    input_file_mime: str

    # Pass results
    preupload_result: dict[str, Any] | None
    classification: dict[str, Any] | None
    pass_a_output: dict[str, Any] | None
    pass_b_output: dict[str, Any] | None
    pass_c_output: dict[str, Any] | None
    pass_d_output: dict[str, Any] | None

    # Correction loop state
    correction_attempts: int
    correction_history: list[dict[str, Any]]

    # Decision
    decision_result: dict[str, Any] | None

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
