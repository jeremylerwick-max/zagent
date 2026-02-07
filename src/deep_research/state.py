from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict, Literal

ClaimType = Literal["fact", "estimate", "opinion"]

class SourceCandidate(TypedDict):
    url: str
    title: str
    snippet: str
    rank: int
    provider: str
    retrieved_at: str

class IngestedSource(TypedDict):
    source_id: str
    url: str
    content_hash: str
    mime_type: str
    retrieved_at: str
    text: str
    metadata: Dict[str, Any]

class ExtractedClaim(TypedDict):
    text: str
    claim_type: ClaimType
    confidence: float
    entities: List[str]
    numbers: List[str]

class Citation(TypedDict):
    quote: str
    location: str
    source_id: str

class VerificationFinding(TypedDict):
    severity: Literal["low", "med", "high"]
    finding: str
    related_source_ids: List[str]
    recommended_action: str

@dataclass
class ResearchState:
    user_query: str
    objective: Optional[str] = None
    subquestions: List[str] = field(default_factory=list)
    stopping_criteria: Dict[str, Any] = field(default_factory=dict)
    iteration: int = 0
    should_continue: bool = True
    confidence: float = 0.0
    gaps: List[str] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    candidates: List[SourceCandidate] = field(default_factory=list)
    selected_urls: List[str] = field(default_factory=list)
    ingested_sources: List[IngestedSource] = field(default_factory=list)
    extracted_claims: Dict[str, List[ExtractedClaim]] = field(default_factory=dict)
    citations: List[Citation] = field(default_factory=list)
    verification: List[VerificationFinding] = field(default_factory=list)
    final_answer: Optional[str] = None
    final_outline: Optional[str] = None
    job_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
