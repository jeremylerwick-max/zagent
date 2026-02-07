from __future__ import annotations
import os
import asyncio
import httpx
from typing import Dict, Tuple
from urllib.parse import urlparse


class FetchError(Exception):
    pass


BLOCKED_SCHEMES = {"file", "ftp", "gopher", "javascript", "data"}
DEFAULT_USER_AGENT = os.getenv("FETCH_USER_AGENT", "agent-zileas-research-bot/1.0")


def _validate_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme not in {"http", "https"}:
        raise FetchError(f"Unsupported URL scheme: {p.scheme}")
    if not p.netloc:
        raise FetchError("Invalid URL")


async def fetch_url(url: str, *, timeout_s: int = 25, max_bytes: int = 10_000_000,
                    retries: int = 2) -> Tuple[bytes, str, Dict[str, str]]:
    _validate_url(url)
    headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "*/*"}
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
                r = await client.get(url, headers=headers)
            if r.status_code >= 400:
                raise FetchError(f"HTTP {r.status_code}")
            raw = r.content
            if len(raw) > max_bytes:
                raw = raw[:max_bytes]
            ctype = (r.headers.get("content-type") or "application/octet-stream").split(";")[0].strip().lower()
            meta = {"final_url": str(r.url), "status_code": str(r.status_code),
                    "content_length": str(len(raw))}
            return raw, ctype, meta
        except Exception as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(0.4 * (attempt + 1))
    raise FetchError(f"fetch failed for {url}: {last_err}")
