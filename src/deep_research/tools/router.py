from __future__ import annotations
from typing import Any, Dict
from deep_research.react_schema import Observation, ActionName


class ToolExecutionError(Exception):
    pass


async def tool_search_web(args: Dict[str, Any]) -> Observation:
    q = str(args.get("query", "")).strip()
    if not q:
        raise ToolExecutionError("query is required")
    # TODO: wire real search provider (Brave API)
    content = f"MOCK_SEARCH_RESULTS for query={q}"
    return Observation(ok=True, tool="search_web", content=content, metadata={"count": 3})


async def tool_open_url(args: Dict[str, Any]) -> Observation:
    url = str(args.get("url", "")).strip()
    if not url.startswith("http"):
        raise ToolExecutionError("valid url required")
    # TODO: real fetch
    content = f"MOCK_URL_CONTENT for url={url}"
    return Observation(ok=True, tool="open_url", content=content, metadata={"url": url})


async def tool_extract_text(args: Dict[str, Any]) -> Observation:
    raw = str(args.get("raw", "")).strip()
    if not raw:
        raise ToolExecutionError("raw content required")
    content = raw[:4000]
    return Observation(ok=True, tool="extract_text", content=content, metadata={})


async def tool_run_python(args: Dict[str, Any]) -> Observation:
    code = str(args.get("code", "")).strip()
    if not code:
        raise ToolExecutionError("code required")
    # IMPORTANT: run in sandbox only
    content = "MOCK_PYTHON_OUTPUT"
    return Observation(ok=True, tool="run_python", content=content, metadata={})


async def execute_tool(action: ActionName, args: Dict[str, Any]) -> Observation:
    if action == "search_web":
        return await tool_search_web(args)
    if action == "open_url":
        return await tool_open_url(args)
    if action == "extract_text":
        return await tool_extract_text(args)
    if action == "run_python":
        return await tool_run_python(args)
    if action == "finish":
        return Observation(ok=True, tool="finish", content="finish requested", metadata={})
    raise ToolExecutionError(f"Unsupported action: {action}")
