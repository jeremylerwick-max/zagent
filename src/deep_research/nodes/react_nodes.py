from __future__ import annotations
from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from deep_research.agents.react_actor import next_react_step
from deep_research.react_schema import ReActTraceItem
from deep_research.tools.router import execute_tool, ToolExecutionError


def _build_messages(state: Dict[str, Any]) -> List[Dict[str, str]]:
    system = {"role": "system", "content": state["react_system_prompt"]}
    user = {"role": "user", "content": state["user_query"]}
    context = []
    for i, t in enumerate(state.get("react_trace", [])[-8:], start=1):
        step = t.get("step", {})
        obs = t.get("observation")
        context.append({"role": "assistant", "content": f"STEP {i} JSON: {step}"})
        if obs:
            context.append({"role": "tool", "content": f"OBS {i}: {obs}"})
    return [system, user, *context]


async def react_think(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    messages = _build_messages(state)
    step = await next_react_step(messages)
    state.setdefault("react_trace", [])
    state["_current_step"] = step.model_dump()
    return state


async def react_act(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    step = state["_current_step"]
    action = step["action"]
    args = step.get("action_input", {}).get("args", {}) or {}
    if action == "finish":
        state["done"] = True
        return state
    try:
        obs = await execute_tool(action, args)
        obs_dict = obs.model_dump()
    except ToolExecutionError as e:
        obs_dict = {"ok": False, "tool": action, "content": f"tool_error: {e}", "metadata": {}}
    trace_item = ReActTraceItem(iteration=int(state.get("iteration", 0)), step=step, observation=obs_dict)
    state["react_trace"].append(trace_item.model_dump())
    state.setdefault("observation_log", []).append(obs_dict)
    state["iteration"] = int(state.get("iteration", 0)) + 1
    return state


async def react_synthesize(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Replace with synthesizer model using evidence from DB + react_trace."""
    used = len(state.get("react_trace", []))
    state["final_answer"] = f"Draft synthesized answer using {used} ReAct steps."
    state["done"] = True
    return state
