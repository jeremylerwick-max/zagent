from typing import List
import hashlib

def content_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def canonical_source_id(url: str, content_hash_hex: str) -> str:
    base = f"{url}|{content_hash_hex}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()

def dedupe_urls(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out
