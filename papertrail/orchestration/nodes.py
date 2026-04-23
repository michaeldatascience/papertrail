"""Pipeline node registrations for the V2 execution plan."""

from __future__ import annotations

from typing import Any

from papertrail.models.pipeline_state import PipelineState
from papertrail.observability.logging import emit
from papertrail.passes.preupload import preupload_node
from papertrail.validation import validate_execution_plan


def _plan(state: PipelineState) -> dict[str, Any]:
    return state.get("execution_plan", {})


async def classify_node(state: PipelineState) -> PipelineState:
    """Classify document type using the compiled plan."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "classify", "stage_enter")

    try:
        plan = _plan(state)
        classification = plan.get("classification", {})
        state["classification"] = {
            "type": plan.get("document_type", "unknown"),
            "confidence": 0.95,
            "reasoning": f"Stub classification using compiled plan for {classification.get('candidate_labels', [])}.",
        }
        await emit(
            run_id,
            "classify",
            "classification_result",
            type=state["classification"]["type"],
            confidence=state["classification"]["confidence"],
        )
        await emit(run_id, "classify", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "classify"
        await emit(run_id, "classify", "stage_failed", level="error", error=str(e))

    return state


async def layout_extract_node(state: PipelineState) -> PipelineState:
    """Layout extraction scaffold driven by the compiled plan."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "layout_extract", "stage_enter")

    try:
        plan = _plan(state)
        schema_fields = plan.get("extraction", {}).get("schema", [])
        state["layout_output"] = {
            "pages": 1,
            "regions": [
                {
                    "id": "r1",
                    "type": "text",
                    "page": 1,
                    "bbox": [0, 0, 1, 1],
                    "confidence": 0.9,
                    "schema_field_count": len(schema_fields),
                }
            ],
            "confidence": 0.9,
        }
        await emit(run_id, "layout_extract", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "layout_extract"
        await emit(run_id, "layout_extract", "stage_failed", level="error", error=str(e))

    return state


async def text_extract_node(state: PipelineState) -> PipelineState:
    """Text/OCR extraction scaffold driven by the compiled plan."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "text_extract", "stage_enter")

    try:
        plan = _plan(state)
        engine_routing = plan.get("engine_routing", {})
        state["text_output"] = {
            "regions": [
                {
                    "region_id": "r1",
                    "text": "Stub extracted text from region r1",
                    "confidence": 0.85,
                    "engine_used": engine_routing.get("ocr", {}).get("name", "stub"),
                }
            ],
            "full_page_ocr": None,
        }
        await emit(run_id, "text_extract", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "text_extract"
        await emit(run_id, "text_extract", "stage_failed", level="error", error=str(e))

    return state


async def schema_extract_node(state: PipelineState) -> PipelineState:
    """Schema extraction scaffold driven by the compiled plan."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "schema_extract", "stage_enter")

    try:
        plan = _plan(state)
        elements = []
        for field in plan.get("extraction", {}).get("schema", []):
            elements.append(
                {
                    "name": field.get("name", "unknown"),
                    "value": None,
                    "llm_confidence": 0.9,
                    "ocr_confidence": 0.85,
                    "source_region": "r1",
                }
            )
        state["extraction_output"] = {
            "elements": elements,
            "model_used": plan.get("llm_routing", {}).get("extract", {}).get("model", "stub"),
            "attempt_number": state.get("correction_attempts", 0),
        }
        await emit(run_id, "schema_extract", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "schema_extract"
        await emit(run_id, "schema_extract", "stage_failed", level="error", error=str(e))

    return state


async def validate_node(state: PipelineState) -> PipelineState:
    """Validation driven by the compiled execution plan."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "validate", "stage_enter")

    try:
        plan = _plan(state)
        extracted_elements = (state.get("extraction_output") or {}).get("elements", [])
        validation_result = validate_execution_plan(plan, extracted_elements)
        state["validation_result"] = validation_result.model_dump()
        await emit(
            run_id,
            "validate",
            "stage_exit",
            passed=validation_result.passed,
            failed_elements=validation_result.failed_elements,
        )
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "validate"
        await emit(run_id, "validate", "stage_failed", level="error", error=str(e))

    return state


async def correction_node(state: PipelineState) -> PipelineState:
    """Correction loop scaffold driven by the compiled plan."""
    run_id = state.get("run_id", "unknown")
    attempt = state.get("correction_attempts", 0) + 1
    await emit(run_id, "correction", "correction_started", attempt=attempt)

    try:
        state["correction_attempts"] = attempt
        plan = _plan(state)
        history = state.get("correction_history", [])
        history.append({"attempt": attempt, "status": "stub", "max_retries": plan.get("correction", {}).get("max_retries", 0)})
        state["correction_history"] = history
        await emit(run_id, "correction", "correction_completed", attempt=attempt)
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "correction"
        await emit(run_id, "correction", "stage_failed", level="error", error=str(e))

    return state


async def suggestion_node(state: PipelineState) -> PipelineState:
    """Generate diagnostic suggestion after correction exhaustion."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "suggestion", "stage_enter")

    try:
        state["awaiting_hitl"] = True
        state["hitl_checkpoint_type"] = "correction_exhausted"
        state["hitl_context"] = {
            "summary": "Stub: correction exhausted, human review needed.",
            "suggestions": [],
        }
        await emit(run_id, "suggestion", "hitl_triggered", checkpoint="correction_exhausted")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "suggestion"
        await emit(run_id, "suggestion", "stage_failed", level="error", error=str(e))

    return state


async def decide_node(state: PipelineState) -> PipelineState:
    """Decision engine scaffold driven by the compiled plan."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "decide", "stage_enter")

    try:
        plan = _plan(state)
        conditions = plan.get("business_rules", {}).get("conditions", [])
        state["decision_result"] = {
            "action": "approve",
            "conditions_evaluated": [condition.get("name") for condition in conditions],
            "transformations_applied": [],
            "enriched_data": {},
            "reasons": [condition.get("reason") for condition in conditions if condition.get("reason")],
        }
        await emit(run_id, "decide", "decision_final", action=state["decision_result"]["action"])
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "decide"
        await emit(run_id, "decide", "stage_failed", level="error", error=str(e))

    return state


async def act_node(state: PipelineState) -> PipelineState:
    """Act — post-processing, output serialization, run finalization."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "act", "stage_enter")

    try:
        plan = _plan(state)
        state["postprocess_result"] = {
            "output_format": plan.get("postprocess", {}).get("output_format", "json"),
            "included_fields": plan.get("postprocess", {}).get("fields_to_include", []),
            "include_trace": plan.get("postprocess", {}).get("include_trace", False),
        }
        await emit(run_id, "act", "run_completed")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "act"
        await emit(run_id, "act", "stage_failed", level="error", error=str(e))

    return state
