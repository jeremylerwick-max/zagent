from __future__ import annotations
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from deep_research.runtime import Deps
from deep_research.db.evidence_repo import EvidenceRepo


async def db_create_job(state: dict, config: RunnableConfig) -> dict:
    deps: Deps = config["configurable"]["deps"]
    async with deps.sessionmaker() as session:
        repo = EvidenceRepo(session)
        job_id = await repo.create_job(state["user_query"], budgets=state.get("budgets", {}), user_id=state.get("user_id"))
        await session.commit()
    state["job_id"] = job_id
    return state


async def db_update_plan(state: dict, config: RunnableConfig) -> dict:
    deps: Deps = config["configurable"]["deps"]
    async with deps.sessionmaker() as session:
        repo = EvidenceRepo(session)
        await repo.update_job_plan(
            job_id=state["job_id"], objective=state.get("objective"),
            subquestions=state.get("subquestions", []), stopping_criteria=state.get("stopping_criteria", {}),
        )
        await session.commit()
    return state


async def db_persist_sources(state: dict, config: RunnableConfig) -> dict:
    deps: Deps = config["configurable"]["deps"]
    sources = state.get("ingested_sources", []) or []
    if not sources:
        return state
    async with deps.sessionmaker() as session:
        repo = EvidenceRepo(session)
        await repo.insert_sources(state["job_id"], sources)
        await session.commit()
    return state


async def db_persist_extractions(state: dict, config: RunnableConfig) -> dict:
    deps: Deps = config["configurable"]["deps"]
    extracted_by_source = state.get("extracted_claims", {}) or {}
    if not extracted_by_source:
        return state
    unsupported_all: list[str] = []
    async with deps.sessionmaker() as session:
        repo = EvidenceRepo(session)
        for source_id, claims in extracted_by_source.items():
            result = await repo.insert_claims_citations_and_links(
                job_id=state["job_id"], source_id=source_id,
                extracted_claims=[{
                    "claim_text": c["text"], "claim_type": c["claim_type"],
                    "confidence": c["confidence"], "entities": c.get("entities", []),
                    "numbers": c.get("numbers", []),
                    "supporting_citations": c.get("supporting_citations", []),
                } for c in claims],
                min_conf_for_citations=state.get("min_conf_for_citations", 0.60),
            )
            unsupported_all.extend(result.unsupported_claims)
        await session.commit()
    if unsupported_all:
        gaps = state.get("gaps", []) or []
        gaps.append(f"{len(unsupported_all)} high-confidence claims lacked citations.")
        for t in unsupported_all[:5]:
            gaps.append(f"Need citations for: {t}")
        state["gaps"] = gaps
        state["confidence"] = min(float(state.get("confidence", 0.0)), 0.55)
    return state


async def db_persist_findings(state: dict, config: RunnableConfig) -> dict:
    deps: Deps = config["configurable"]["deps"]
    findings = state.get("verification", []) or []
    if not findings:
        return state
    async with deps.sessionmaker() as session:
        repo = EvidenceRepo(session)
        await repo.insert_findings(state["job_id"], findings)
        await session.commit()
    return state


async def db_finalize(state: dict, config: RunnableConfig) -> dict:
    deps: Deps = config["configurable"]["deps"]
    used_source_ids = state.get("used_source_ids") or [s["source_id"] for s in state.get("ingested_sources", [])]
    async with deps.sessionmaker() as session:
        repo = EvidenceRepo(session)
        await repo.mark_sources_used(state["job_id"], used_source_ids)
        await repo.finalize(
            job_id=state["job_id"], answer=state.get("final_answer", ""),
            outline=state.get("final_outline"), confidence=float(state.get("confidence", 0.0)),
            used_source_ids=used_source_ids,
        )
        await session.commit()
    return state
