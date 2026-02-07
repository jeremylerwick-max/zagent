from langgraph.graph import StateGraph, END
from .state import ResearchState
from .agents.planner import plan_research
from .agents.searcher import generate_queries, run_search, select_sources
from .agents.reader import fetch_and_parse, extract_notes
from .agents.verifier import verify
from .agents.synthesizer import synthesize
from .config import ResearchBudgets

def _gap_check(state: ResearchState, budgets: ResearchBudgets) -> str:
    state.iteration += 1
    if state.iteration >= budgets.max_iterations:
        state.should_continue = False
        return "synthesize"
    if state.confidence >= budgets.min_confidence_to_finalize and not state.gaps:
        state.should_continue = False
        return "synthesize"
    if state.gaps:
        return "generate_queries"
    return "synthesize"

def build_graph(budgets: ResearchBudgets | None = None):
    budgets = budgets or ResearchBudgets()
    g = StateGraph(ResearchState)
    g.add_node("plan", plan_research)
    g.add_node("generate_queries", generate_queries)
    g.add_node("search", lambda s: run_search(s, k=10))
    g.add_node("select_sources", lambda s: select_sources(s, max_sources=budgets.max_sources_per_iter))
    g.add_node("fetch_and_parse", fetch_and_parse)
    g.add_node("extract_notes", extract_notes)
    g.add_node("verify", verify)
    g.add_node("synthesize", synthesize)
    g.set_entry_point("plan")
    g.add_edge("plan", "generate_queries")
    g.add_edge("generate_queries", "search")
    g.add_edge("search", "select_sources")
    g.add_edge("select_sources", "fetch_and_parse")
    g.add_edge("fetch_and_parse", "extract_notes")
    g.add_edge("extract_notes", "verify")
    g.add_conditional_edges(
        "verify",
        lambda s: _gap_check(s, budgets),
        {"generate_queries": "generate_queries", "synthesize": "synthesize"},
    )
    g.add_edge("synthesize", END)
    return g.compile()
