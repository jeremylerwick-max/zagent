from ..state import ResearchState

def plan_research(state: ResearchState) -> ResearchState:
    """Output: objective, subquestions, stopping_criteria. Replace with model call."""
    state.objective = state.user_query
    state.subquestions = [state.user_query]
    state.stopping_criteria = {
        "min_confidence": 0.78,
        "max_iterations": 4,
        "must_have_source_diversity": True,
    }
    return state
