from __future__ import annotations
from pathlib import Path
from deep_research.graph import build_graph
from deep_research.runtime import Deps
from db.session import SessionLocal


def load_prompt() -> str:
    return Path("deep_research/prompts/react_system.txt").read_text(encoding="utf-8")


async def run_research(query: str) -> dict:
    app = build_graph()
    deps = Deps(sessionmaker=SessionLocal)
    state = {
        "user_query": query,
        "react_system_prompt": load_prompt(),
        "react_trace": [],
        "observation_log": [],
        "iteration": 0,
        "max_iterations": 8,
        "done": False,
        "gaps": [],
        "budgets": {"max_iterations": 8, "min_confidence_to_finalize": 0.78},
        "min_conf_for_citations": 0.60,
    }
    return await app.ainvoke(state, config={"configurable": {"deps": deps}})
