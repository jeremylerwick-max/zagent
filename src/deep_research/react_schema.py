from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator

ActionName = Literal["search_web", "open_url", "extract_text", "run_python", "finish"]


class ActionInput(BaseModel):
    args: Dict[str, Any] = Field(default_factory=dict)


class ReActStep(BaseModel):
    thought: str = Field(min_length=1, max_length=4000)
    action: ActionName
    action_input: ActionInput = Field(default_factory=ActionInput)

    @field_validator("thought")
    @classmethod
    def no_tool_leak_in_thought(cls, v: str) -> str:
        banned = ["api_key", "password", "secret="]
        lower = v.lower()
        for b in banned:
            if b in lower:
                raise ValueError("Potential secret leakage in thought")
        return v


class Observation(BaseModel):
    ok: bool
    tool: ActionName
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReActTraceItem(BaseModel):
    iteration: int
    step: ReActStep
    observation: Optional[Observation] = None
