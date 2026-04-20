"""LangGraph state machine definition."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from papertrail.models.pipeline_state import PipelineState
from papertrail.orchestration.nodes import (
    act_node,
    classify_node,
    correction_node,
    decide_node,
    pass_a_node,
    pass_b_node,
    pass_c_node,
    pass_d_node,
    preupload_node,
    suggestion_node,
)
from papertrail.orchestration.routing import (
    route_after_classify,
    route_after_validation,
)


def build_graph() -> StateGraph:
    """Build and return the compiled pipeline graph."""
    g = StateGraph(PipelineState)

    # Register nodes
    g.add_node("preupload", preupload_node)
    g.add_node("classify", classify_node)
    g.add_node("pass_a", pass_a_node)
    g.add_node("pass_b", pass_b_node)
    g.add_node("pass_c", pass_c_node)
    g.add_node("pass_d", pass_d_node)
    g.add_node("correction", correction_node)
    g.add_node("suggestion", suggestion_node)
    g.add_node("decide", decide_node)
    g.add_node("act", act_node)

    # Set entry point
    g.set_entry_point("preupload")

    # Linear edges
    g.add_edge("preupload", "classify")

    # Conditional: after classify
    g.add_conditional_edges(
        "classify",
        route_after_classify,
        {"proceed": "pass_a", "hitl": END, "error": END},
    )

    # Linear extraction pipeline
    g.add_edge("pass_a", "pass_b")
    g.add_edge("pass_b", "pass_c")
    g.add_edge("pass_c", "pass_d")

    # Conditional: after validation
    g.add_conditional_edges(
        "pass_d",
        route_after_validation,
        {"proceed": "decide", "retry": "correction", "exhausted": "suggestion", "error": END},
    )

    # Correction loops back to pass_c
    g.add_edge("correction", "pass_c")

    # Suggestion ends (HITL pause)
    g.add_edge("suggestion", END)

    # Decision to action
    g.add_edge("decide", "act")
    g.add_edge("act", END)

    return g
