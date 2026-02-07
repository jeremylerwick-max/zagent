from __future__ import annotations
from deep_research.graph import build_graph
from deep_research.runtime import Deps
from db.session import SessionLocal


async def run_research(user_query: str) -> dict:
    app = build_graph()
    state = {
        "user_query": user_query,
        "iteration": 0,
        "confidence": 0.0,
        "gaps": [],
        "budgets": {
            "max_iterations": 4,
            "min_confidence_to_finalize": 0.78,
        },
        "min_conf_for_citations": 0.60,
    }
    deps = Deps(sessionmaker=SessionLocal)
    final_state = await app.ainvoke(
        state, config={"configurable": {"deps": deps}},
    )
    return final_state
