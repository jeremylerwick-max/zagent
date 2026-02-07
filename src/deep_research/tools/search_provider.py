from __future__ import annotations
import os
import httpx
from typing import Any, Dict, List, Literal

Provider = Literal["brave", "bing"]


class SearchError(Exception):
    pass


async def _brave_search(query: str, k: int = 8, timeout_s: int = 20) -> List[Dict[str, Any]]:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        raise SearchError("Missing BRAVE_API_KEY")
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": query, "count": k}
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
        r = await client.get(url, headers=headers, params=params)
        if r.status_code != 200:
            raise SearchError(f"Brave search failed: {r.status_code} {r.text[:200]}")
        data = r.json()
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(data.get("web", {}).get("results", [])[:k], start=1):
        out.append({"rank": i, "url": item.get("url", ""), "title": item.get("title", ""),
                     "snippet": item.get("description", ""), "provider": "brave"})
    return out


async def _bing_search(query: str, k: int = 8, timeout_s: int = 20) -> List[Dict[str, Any]]:
    api_key = os.getenv("BING_API_KEY")
    endpoint = os.getenv("BING_ENDPOINT", "https://api.bing.microsoft.com")
    if not api_key:
        raise SearchError("Missing BING_API_KEY")
    url = f"{endpoint}/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": k, "textDecorations": False, "textFormat": "Raw"}
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
        r = await client.get(url, headers=headers, params=params)
        if r.status_code != 200:
            raise SearchError(f"Bing search failed: {r.status_code} {r.text[:200]}")
        data = r.json()
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(data.get("webPages", {}).get("value", [])[:k], start=1):
        out.append({"rank": i, "url": item.get("url", ""), "title": item.get("name", ""),
                     "snippet": item.get("snippet", ""), "provider": "bing"})
    return out


async def search_web(query: str, *, provider: Provider = "brave", k: int = 8) -> List[Dict[str, Any]]:
    q = query.strip()
    if not q:
        raise SearchError("query is required")
    if provider == "brave":
        return await _brave_search(q, k=k)
    if provider == "bing":
        return await _bing_search(q, k=k)
    raise SearchError(f"Unsupported provider: {provider}")
