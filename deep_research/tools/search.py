from typing import List
from ..state import SourceCandidate

def web_search(query: str, *, k: int = 10) -> List[SourceCandidate]:
    """Execute a web search via your chosen provider."""
    raise NotImplementedError
