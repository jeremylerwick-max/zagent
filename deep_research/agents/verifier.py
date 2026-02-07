from ..state import ResearchState, VerificationFinding

def verify(state: ResearchState) -> ResearchState:
    """Cross-check claims across sources and decide gaps/contradictions."""
    findings: list[VerificationFinding] = []

    # TODO: replace with verifier model + deterministic checks
    if len(state.ingested_sources) < 2:
        findings.append({
            "severity": "high",
            "finding": "Insufficient independent sources.",
            "related_source_ids": [s["source_id"] for s in state.ingested_sources],
            "recommended_action": "Add at least 2 more independent sources.",
        })

    state.verification = findings
    state.gaps = [f["finding"] for f in findings if f["severity"] in ("med", "high")]
    state.confidence = 0.4 if findings else 0.8
    return state
