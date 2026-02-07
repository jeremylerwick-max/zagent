from typing import Dict, Any, Tuple

def extract_text(raw: bytes, mime_type: str) -> Tuple[str, Dict[str, Any]]:
    """Converts HTML/PDF/etc to normalized text + metadata."""
    raise NotImplementedError
