"""Internal pipeline executor for the current V2 transition."""

from __future__ import annotations

from papertrail.models.pipeline_state import PipelineState
from papertrail.orchestration.nodes import (
    act_node,
    classify_node,
    correction_node,
    decide_node,
    layout_extract_node,
    preupload_node,
    schema_extract_node,
    suggestion_node,
    text_extract_node,
    validate_node,
)
from papertrail.orchestration.routing import route_after_classify, route_after_validation


class PipelineExecutor:
    """A tiny compiled executor that runs the current stage sequence."""

    async def ainvoke(self, state: PipelineState) -> PipelineState:
        state = await preupload_node(state)
        if state.get("error"):
            return state

        state = await classify_node(state)
        route = route_after_classify(state)
        if route == "hitl":
            state["awaiting_hitl"] = True
            state["hitl_checkpoint_type"] = "classification_low_confidence"
            state["hitl_context"] = {
                "summary": "Classification confidence fell below the compiled threshold.",
                "suggestions": [],
            }
            return state
        if route == "error":
            state["failed_stage"] = state.get("failed_stage") or "classify"
            return state

        state = await layout_extract_node(state)
        if state.get("error"):
            return state

        state = await text_extract_node(state)
        if state.get("error"):
            return state

        state = await schema_extract_node(state)
        if state.get("error"):
            return state

        state = await validate_node(state)
        if state.get("error"):
            return state

        while True:
            route = route_after_validation(state)
            if route == "proceed":
                break
            if route == "retry":
                state = await correction_node(state)
                if state.get("error"):
                    return state
                state = await schema_extract_node(state)
                if state.get("error"):
                    return state
                state = await validate_node(state)
                if state.get("error"):
                    return state
                continue
            if route == "exhausted":
                state = await suggestion_node(state)
                return state
            state["failed_stage"] = state.get("failed_stage") or "validate"
            return state

        state = await decide_node(state)
        if state.get("error"):
            return state

        state = await act_node(state)
        return state


class PipelineGraph:
    """Compatibility wrapper that mirrors the old build_graph().compile() API."""

    def compile(self) -> PipelineExecutor:
        return PipelineExecutor()


def build_graph() -> PipelineGraph:
    """Build the current executor wrapper."""
    return PipelineGraph()
