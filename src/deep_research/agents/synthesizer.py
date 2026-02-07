from ..state import ResearchState

def synthesize(state: ResearchState) -> ResearchState:
    # TODO: replace with synthesizer model; enforce citations mapping to ledger
    state.final_outline = "1) Summary 2) Evidence 3) Caveats"
    state.final_answer = (
        f"Answer for: {state.user_query}\n\n"
        f"Sources used: {len(state.ingested_sources)}\n"
        f"Confidence: {state.confidence}\n"
        f"Verification findings: {len(state.verification)}\n"
    )
    return state
