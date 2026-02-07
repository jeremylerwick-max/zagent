from ..state import ResearchState
from ..tools.search import web_search

def generate_queries(state: ResearchState) -> ResearchState:
    if state.iteration == 0:
        state.search_queries = [state.user_query]
    else:
        state.search_queries = [f"{g} {state.user_query}" for g in state.gaps[:3]] or [state.user_query]
    return state

def run_search(state: ResearchState, *, k: int = 10) -> ResearchState:
    all_candidates = []
    for q in state.search_queries:
        all_candidates.extend(web_search(q, k=k))
    state.candidates = all_candidates
    return state

def select_sources(state: ResearchState, *, max_sources: int = 8) -> ResearchState:
    urls = [c["url"] for c in state.candidates][:max_sources]
    state.selected_urls = urls
    return state
