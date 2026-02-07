from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from db.models import (
    ResearchJob, SourceDocument, SourceClaim, SourceCitation,
    VerificationFinding, FinalReport, ClaimCitationLink,
)


@dataclass
class PersistResult:
    unsupported_claims: List[str]


class EvidenceRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, query: str, budgets: Dict[str, Any], user_id: Optional[str] = None) -> str:
        job = ResearchJob(query=query, budgets=budgets, user_id=user_id, status="running")
        self.session.add(job)
        await self.session.flush()
        return str(job.job_id)

    async def update_job_plan(self, job_id: str, objective: Optional[str],
                              subquestions: List[str], stopping_criteria: Dict[str, Any]) -> None:
        await self.session.execute(
            sa.update(ResearchJob)
            .where(ResearchJob.job_id == sa.cast(job_id, sa.dialects.postgresql.UUID))
            .values(objective=objective, subquestions=subquestions, stopping_criteria=stopping_criteria)
        )

    async def insert_sources(self, job_id: str, sources: List[Dict[str, Any]]) -> None:
        if not sources:
            return
        stmt = insert(SourceDocument).values([{
            "source_id": s["source_id"], "job_id": job_id, "url": s["url"],
            "retrieved_at": s.get("retrieved_at") or sa.func.now(),
            "mime_type": s["mime_type"], "content_hash": s["content_hash"],
            "text": s["text"], "metadata": s.get("metadata", {}),
            "provider": s.get("provider"), "reliability_score": s.get("reliability_score", 0.5),
            "used_in_final": False,
        } for s in sources]).on_conflict_do_nothing(index_elements=["source_id"])
        await self.session.execute(stmt)

    async def _upsert_citation_get_id(self, job_id: str, source_id: str, quote: str, location: str) -> int:
        stmt = (
            insert(SourceCitation)
            .values(job_id=job_id, source_id=source_id, quote=quote, location=location)
            .on_conflict_do_update(
                index_elements=["source_id", "quote", "location"],
                set_={"quote": sa.text("EXCLUDED.quote")},
            )
            .returning(SourceCitation.citation_id)
        )
        res = await self.session.execute(stmt)
        return int(res.scalar_one())

    async def insert_claims_citations_and_links(self, job_id: str, source_id: str,
                                                 extracted_claims: List[Dict[str, Any]], *,
                                                 min_conf_for_citations: float = 0.60) -> PersistResult:
        unsupported: List[str] = []
        for c in extracted_claims:
            claim_type = c["claim_type"]
            conf = float(c["confidence"])
            supporting = c.get("supporting_citations") or []
            needs_cites = (claim_type in ("fact", "estimate")) and (conf >= min_conf_for_citations)
            if needs_cites and not supporting:
                unsupported.append(c["claim_text"])
                continue
            claim = SourceClaim(
                job_id=job_id, source_id=source_id, claim_text=c["claim_text"],
                claim_type=claim_type, confidence=conf,
                entities=c.get("entities", []), numbers=c.get("numbers", []),
            )
            self.session.add(claim)
            await self.session.flush()
            for sc in supporting:
                citation_id = await self._upsert_citation_get_id(job_id, source_id, sc["quote"], sc["location"])
                link_stmt = insert(ClaimCitationLink).values(
                    claim_id=claim.claim_id, citation_id=citation_id,
                ).on_conflict_do_nothing(index_elements=["claim_id", "citation_id"])
                await self.session.execute(link_stmt)
        return PersistResult(unsupported_claims=unsupported)

    async def insert_findings(self, job_id: str, findings: List[Dict[str, Any]]) -> None:
        if not findings:
            return
        stmt = insert(VerificationFinding).values([{
            "job_id": job_id, "severity": f["severity"], "finding": f["finding"],
            "related_source_ids": f.get("related_source_ids", []),
            "recommended_action": f["recommended_action"],
        } for f in findings])
        await self.session.execute(stmt)

    async def citation_enforcement_query(self, job_id: str, *, min_conf: float = 0.60) -> List[Tuple[int, str]]:
        q = sa.text("""
            SELECT sc.claim_id, sc.claim_text FROM source_claim sc
            LEFT JOIN claim_citation_link ccl ON sc.claim_id = ccl.claim_id
            WHERE sc.job_id = :job_id AND sc.claim_type IN ('fact','estimate') AND sc.confidence >= :min_conf
            GROUP BY sc.claim_id, sc.claim_text HAVING COUNT(ccl.citation_id) = 0 ORDER BY sc.claim_id;
        """)
        res = await self.session.execute(q, {"job_id": job_id, "min_conf": min_conf})
        return [(int(r[0]), str(r[1])) for r in res.fetchall()]

    async def mark_sources_used(self, job_id: str, used_source_ids: List[str]) -> None:
        if not used_source_ids:
            return
        await self.session.execute(
            sa.update(SourceDocument)
            .where(SourceDocument.job_id == sa.cast(job_id, sa.dialects.postgresql.UUID))
            .where(SourceDocument.source_id.in_(used_source_ids))
            .values(used_in_final=True)
        )

    async def finalize(self, job_id: str, answer: str, outline: Optional[str],
                       confidence: float, used_source_ids: List[str]) -> None:
        stmt = insert(FinalReport).values(
            job_id=job_id, answer=answer, outline=outline,
            confidence=confidence, used_source_ids=used_source_ids,
        ).on_conflict_do_update(index_elements=["job_id"], set_={
            "answer": sa.text("EXCLUDED.answer"), "outline": sa.text("EXCLUDED.outline"),
            "confidence": sa.text("EXCLUDED.confidence"), "used_source_ids": sa.text("EXCLUDED.used_source_ids"),
        })
        await self.session.execute(stmt)
        await self.session.execute(
            sa.update(ResearchJob)
            .where(ResearchJob.job_id == sa.cast(job_id, sa.dialects.postgresql.UUID))
            .values(status="completed")
        )
