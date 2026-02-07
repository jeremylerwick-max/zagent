from typing import Tuple

def fetch_url(url: str, *, timeout_s: int = 20) -> Tuple[bytes, str]:
    """Returns (raw_bytes, mime_type). Enforce allowlists at orchestrator layer."""
    raise NotImplementedError
