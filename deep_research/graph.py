from __future__ import annotations
from langgraph.graph import StateGraph, END
from deep_research.agents.planner import plan_research
from deep_research.agents.searcher import generate_queries, run_search, select_sources
from deep_research.agents.reader import fetch_and_parse, extract_notes
from deep_research.agents.verifier import verify
from deep_research.agents.synthesizer import synthesize
from deep_research.nodes.db_nodes import (
    db_create_job, db_update_plan, db_persist_sources,
    db_persist_extractions, db_persist_findings, db_finalize,
)
from deep_research.nodes.citation_enforcer import citation_enforce


def gap_check(state: dict) -> str:
    state["iteration"] = int(state.get("iteration", 0)) + 1
    max_iterations = int(state.get("budgets", {}).get("max_iterations", 4))
    min_conf = float(state.get("budgets", {}).get("min_confidence_to_finalize", 0.78))

    if state["iteration"] >= max_iterations:
        return "synthesize"
    if float(state.get("confidence", 0.0)) >= min_conf and not (state.get("gaps") or []):
        return "synthesize"
    if state.get("gaps"):
        return "generate_queries"
    return "synthesize"


def build_graph():
    g = StateGraph(dict)

    g.add_node("db_create_job", db_create_job)
    g.add_node("plan", plan_research)
    g.add_node("db_update_plan", db_update_plan)
    g.add_node("generate_queries", generate_queries)
    g.add_node("search", run_search)
    g.add_node("select_sources", select_sources)
    g.add_node("fetch_and_parse", fetch_and_parse)
    g.add_node("db_persist_sources", db_persist_sources)
    g.add_node("extract_notes", extract_notes)
    g.add_node("db_persist_extractions", db_persist_extractions)
    g.add_node("citation_enforce", citation_enforce)
    g.add_node("verify", verify)
    g.add_node("db_persist_findings", db_persist_findings)
    g.add_node("synthesize", synthesize)
    g.add_node("db_finalize", db_finalize)

    g.set_entry_point("db_create_job")
    g.add_edge("db_create_job", "plan")
    g.add_edge("plan", "db_update_plan")
    g.add_edge("db_update_plan", "generate_queries")
    g.add_edge("generate_queries", "search")
    g.add_edge("search", "select_sources")
    g.add_edge("select_sources", "fetch_and_parse")
    g.add_edge("fetch_and_parse", "db_persist_sources")
    g.add_edge("db_persist_sources", "extract_notes")
    g.add_edge("extract_notes", "db_persist_extractions")
    g.add_edge("db_persist_extractions", "citation_enforce")
    g.add_edge("citation_enforce", "verify")
    g.add_edge("verify", "db_persist_findings")

    g.add_conditional_edges(
        "db_persist_findings", gap_check,
        {"generate_queries": "generate_queries", "synthesize": "synthesize"},
    )

    g.add_edge("synthesize", "db_finalize")
    g.add_edge("db_finalize", END)

    return g.compile()
