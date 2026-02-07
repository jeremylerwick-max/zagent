from __future__ import annotations
from langchain_core.runnables import RunnableConfig
from deep_research.runtime import Deps
from deep_research.db.evidence_repo import EvidenceRepo


async def citation_enforce(state: dict, config: RunnableConfig) -> dict:
    deps: Deps = config["configurable"]["deps"]
    async with deps.sessionmaker() as session:
        repo = EvidenceRepo(session)
        missing = await repo.citation_enforcement_query(
            job_id=state["job_id"],
            min_conf=float(state.get("min_conf_for_citations", 0.60)),
        )
    if missing:
        gaps = state.get("gaps", []) or []
        gaps.append(f"{len(missing)} persisted claims still have 0 citation links (strict fail).")
        for _, claim_text in missing[:5]:
            gaps.append(f"Unsupported claim in DB: {claim_text}")
        state["gaps"] = gaps
        state["confidence"] = min(float(state.get("confidence", 0.0)), 0.50)
    return state
