from __future__ import annotations
import json
from typing import Any, Dict, List
from pydantic import ValidationError
from deep_research.react_schema import ReActStep


class ModelOutputError(Exception):
    pass


async def call_actor_model(messages: List[Dict[str, str]]) -> str:
    """TODO: implement with model router (local Ollama / API fallback). Must return raw JSON string."""
    return json.dumps({
        "thought": "Need current sources before synthesis.",
        "action": "search_web",
        "action_input": {"args": {"query": "latest battery density breakthroughs 2025 2026"}}
    })


async def next_react_step(messages: List[Dict[str, str]]) -> ReActStep:
    raw = await call_actor_model(messages)
    try:
        data = json.loads(raw)
        step = ReActStep.model_validate(data)
        return step
    except (json.JSONDecodeError, ValidationError) as e:
        raise ModelOutputError(f"Invalid ReAct JSON from model: {e}")
