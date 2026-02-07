from __future__ import annotations
from langgraph.graph import StateGraph, END
from deep_research.nodes.db_nodes import (
    db_create_job, db_update_plan, db_persist_sources,
    db_persist_extractions, db_persist_findings, db_finalize,
)
from deep_research.nodes.citation_enforcer import citation_enforce
from deep_research.nodes.react_nodes import react_think, react_act, react_synthesize


def route_after_act(state: dict) -> str:
    if state.get("done"):
        return "react_synthesize"
    max_iters = int(state.get("max_iterations", 8))
    if int(state.get("iteration", 0)) >= max_iters:
        return "react_synthesize"
    return "react_think"


def route_after_enforce(state: dict) -> str:
    if state.get("gaps"):
        return "react_think"
    return "react_synthesize"


def build_graph():
    g = StateGraph(dict)
    g.add_node("db_create_job", db_create_job)
    g.add_node("db_update_plan", db_update_plan)
    g.add_node("react_think", react_think)
    g.add_node("react_act", react_act)
    g.add_node("db_persist_sources", db_persist_sources)
    g.add_node("db_persist_extractions", db_persist_extractions)
    g.add_node("citation_enforce", citation_enforce)
    g.add_node("db_persist_findings", db_persist_findings)
    g.add_node("react_synthesize", react_synthesize)
    g.add_node("db_finalize", db_finalize)

    g.set_entry_point("db_create_job")
    g.add_edge("db_create_job", "db_update_plan")
    g.add_edge("db_update_plan", "react_think")
    g.add_edge("react_think", "react_act")
    g.add_conditional_edges(
        "react_act", route_after_act,
        {"react_think": "react_think", "react_synthesize": "react_synthesize"},
    )
    g.add_edge("react_synthesize", "db_finalize")
    g.add_edge("db_finalize", END)
    return g.compile()
