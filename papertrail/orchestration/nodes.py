"""Pipeline node registrations — stub implementations for Week 1."""

from __future__ import annotations

from papertrail.models.pipeline_state import PipelineState
from papertrail.observability.logging import emit
from papertrail.passes.preupload import preupload_node


async def classify_node(state: PipelineState) -> PipelineState:
    """Classify document type using LLM."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "classify", "stage_enter")

    try:
        # TODO: Implement real LLM classification
        playbook = state.get("playbook", {})
        state["classification"] = {
            "type": playbook.get("meta", {}).get("document_type", "unknown"),
            "confidence": 0.95,
            "reasoning": "Stub classification — matched playbook document type.",
        }
        await emit(
            run_id, "classify", "classification_result",
            type=state["classification"]["type"],
            confidence=state["classification"]["confidence"],
        )
        await emit(run_id, "classify", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "classify"
        await emit(run_id, "classify", "stage_failed", level="error", error=str(e))

    return state


async def pass_a_node(state: PipelineState) -> PipelineState:
    """Pass A — Layout analysis via Docling."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "pass_a", "stage_enter")

    try:
        # TODO: Implement Docling layout analysis
        state["pass_a_output"] = {
            "pages": 1,
            "regions": [
                {"id": "r1", "type": "text", "page": 1, "bbox": [0, 0, 1, 1], "confidence": 0.9}
            ],
            "confidence": 0.9,
        }
        await emit(run_id, "pass_a", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "pass_a"
        await emit(run_id, "pass_a", "stage_failed", level="error", error=str(e))

    return state


async def pass_b_node(state: PipelineState) -> PipelineState:
    """Pass B — Raw text/OCR extraction via engine dispatcher."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "pass_b", "stage_enter")

    try:
        # TODO: Implement engine dispatcher for raw extraction
        state["pass_b_output"] = {
            "regions": [
                {
                    "region_id": "r1",
                    "text": "Stub extracted text from region r1",
                    "confidence": 0.85,
                    "engine_used": "stub",
                }
            ],
            "full_page_ocr": None,
        }
        await emit(run_id, "pass_b", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "pass_b"
        await emit(run_id, "pass_b", "stage_failed", level="error", error=str(e))

    return state


async def pass_c_node(state: PipelineState) -> PipelineState:
    """Pass C — Schema extraction via LLM + Instructor."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "pass_c", "stage_enter")

    try:
        # TODO: Implement LLM schema extraction with Instructor
        state["pass_c_output"] = {
            "elements": [
                {
                    "name": "stub_field",
                    "value": "stub_value",
                    "llm_confidence": 0.9,
                    "ocr_confidence": 0.85,
                    "source_region": "r1",
                }
            ],
            "model_used": "stub",
            "attempt_number": state.get("correction_attempts", 0),
        }
        await emit(run_id, "pass_c", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "pass_c"
        await emit(run_id, "pass_c", "stage_failed", level="error", error=str(e))

    return state


async def pass_d_node(state: PipelineState) -> PipelineState:
    """Pass D — Validation (hard rules, soft rules, cross-field checks)."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "pass_d", "stage_enter")

    try:
        # TODO: Implement validation runner
        state["pass_d_output"] = {
            "passed": True,
            "element_results": [],
            "cross_field_results": [],
            "aggregate_confidence": 0.88,
            "failed_elements": [],
        }
        await emit(run_id, "pass_d", "stage_exit")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "pass_d"
        await emit(run_id, "pass_d", "stage_failed", level="error", error=str(e))

    return state


async def correction_node(state: PipelineState) -> PipelineState:
    """Correction loop — targeted hints and re-extraction."""
    run_id = state.get("run_id", "unknown")
    attempt = state.get("correction_attempts", 0) + 1
    await emit(run_id, "correction", "correction_started", attempt=attempt)

    try:
        # TODO: Implement correction with targeted hints
        state["correction_attempts"] = attempt
        history = state.get("correction_history", [])
        history.append({"attempt": attempt, "status": "stub"})
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
        # TODO: Implement LLM diagnostic suggestion
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
    """Decision engine — evaluate conditions, run transformations, resolve precedence."""
    run_id = state.get("run_id", "unknown")
    await emit(run_id, "decide", "stage_enter")

    try:
        # TODO: Implement decision engine
        state["decision_result"] = {
            "action": "approve",
            "conditions_evaluated": [],
            "transformations_applied": [],
            "enriched_data": {},
            "reasons": [],
        }
        await emit(
            run_id, "decide", "decision_final",
            action=state["decision_result"]["action"],
        )
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
        # TODO: Implement post-processing and output serialization
        await emit(run_id, "act", "run_completed")
    except Exception as e:
        state["error"] = str(e)
        state["failed_stage"] = "act"
        await emit(run_id, "act", "stage_failed", level="error", error=str(e))

    return state
