from ..state import ResearchState, IngestedSource, ExtractedClaim, Citation
from ..tools.fetch import fetch_url
from ..tools.parse import extract_text
from ..tools.dedupe import content_hash, canonical_source_id

def fetch_and_parse(state: ResearchState) -> ResearchState:
    for url in state.selected_urls:
        try:
            raw, mime = fetch_url(url)
            ch = content_hash(raw)
            sid = canonical_source_id(url, ch)
            text, meta = extract_text(raw, mime)
            state.ingested_sources.append({
                "source_id": sid, "url": url, "content_hash": ch,
                "mime_type": mime, "retrieved_at": meta.get("retrieved_at") or "",
                "text": text, "metadata": meta,
            })
        except Exception as e:
            state.errors.append(f"fetch/parse failed for {url}: {e}")
    return state

def extract_notes(state: ResearchState) -> ResearchState:
    """For each ingested source, call extractor model to produce structured claims and citations."""
    for src in state.ingested_sources:
        sid = src["source_id"]
        # TODO: replace with model extraction
        claims: list[ExtractedClaim] = [{
            "text": f"Placeholder claim from {src['url']}",
            "claim_type": "estimate", "confidence": 0.4,
            "entities": [], "numbers": [],
        }]
        cites: list[Citation] = [{
            "quote": "Placeholder quote within 25 words.",
            "location": "n/a", "source_id": sid,
        }]
        state.extracted_claims[sid] = claims
        state.citations.extend(cites)
    return state
