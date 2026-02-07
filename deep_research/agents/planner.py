from ..state import ResearchState
from typing import Dict, Any, List

def plan_research(state: ResearchState) -> ResearchState:
    """Output: objective, subquestions, stopping_criteria. Replace with model call."""
    # TODO: call planner model
    state.objective = state.user_query
    state.subquestions = [state.user_query]  # naive placeholder
    state.stopping_criteria = {
        "min_confidence": 0.78,
        "max_iterations": 4,
        "must_have_source_diversity": True,
    }
    return state
