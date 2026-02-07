from .graph import build_graph
from .state import ResearchState
from .config import ResearchBudgets

def run_research(query: str):
    app = build_graph(ResearchBudgets())
    state = ResearchState(user_query=query)
    final_state = app.invoke(state)
    return final_state
