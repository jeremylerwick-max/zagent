from dataclasses import dataclass

@dataclass(frozen=True)
class ResearchBudgets:
    max_iterations: int = 4
    max_sources_per_iter: int = 8
    max_total_sources: int = 25
    max_total_tokens: int = 250_000
    max_wall_seconds: int = 600  # 10 min
    min_confidence_to_finalize: float = 0.78
