"""Node implementations for the MVP siRNA workflow graph."""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from agent_core.llm_config import get_llm
from agent_core.state import AgentState
from agent_core.tools import check_off_target, predict_sirna_efficiency

TOOLS = [predict_sirna_efficiency, check_off_target]
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def _msg_text(message: Any) -> str:
    if hasattr(message, "content"):
        content = message.content
        return content if isinstance(content, str) else str(content)
    return str(message)


def _extract_rna_sequence(text: str) -> str:
    normalized = text.upper().replace("T", "U")
    seq = "".join(ch for ch in normalized if ch in {"A", "U", "G", "C"})
    return seq[:21] if seq else "AUGCUAACGUAGCUAUGCUA"


def router_node(state: AgentState) -> AgentState:
    """Use LLM to choose downstream node name."""
    llm = get_llm()
    prompt = (
        "You are a router for an RNA design workflow.\n"
        "Read the latest user request and output exactly one token:\n"
        "- sirna_specialist (for siRNA design/evaluation requests)\n"
        "- unsupported (for anything else)\n"
        "No extra words."
    )
    try:
        decision = llm.invoke([SystemMessage(content=prompt), *state.get("messages", [])])
        text = _msg_text(decision).strip().lower()
        route = "sirna_specialist" if "sirna_specialist" in text else "unsupported"
        decision_note = f"Router decision: {route}"
    except Exception as exc:
        route = "sirna_specialist"
        decision_note = (
            "Router fallback: LLM connection failed, default to sirna_specialist. "
            f"error={exc}"
        )

    state["current_task"] = "sirna_design" if route == "sirna_specialist" else "unsupported"
    state["route"] = "sirna" if route == "sirna_specialist" else "unsupported"
    state["messages"] = state.get("messages", []) + [
        AIMessage(content=decision_note)
    ]
    return state


def sirna_specialist_node(state: AgentState) -> AgentState:
    """Use LLM + tool binding to produce tool calls and candidate."""
    llm = get_llm().bind_tools(TOOLS)
    prompt = (
        "You are a siRNA specialist.\n"
        "You must perform ONLY tool calls, no long prose, no code block.\n"
        "Steps:\n"
        "1) Extract one RNA sequence candidate (A/U/G/C, length <= 21) from user request.\n"
        "2) MUST call predict_sirna_efficiency with that sequence.\n"
        "3) MUST call check_off_target with that sequence.\n"
        "If user input is invalid, use default AUGCUAACGUAGCUAUGCUA."
    )
    try:
        ai_msg = llm.invoke([SystemMessage(content=prompt), *state.get("messages", [])])
    except Exception:
        seq = _extract_rna_sequence(state.get("input_sequence", ""))
        ai_msg = AIMessage(
            content="Specialist fallback: generated deterministic candidate and tool calls.",
            tool_calls=[
                {
                    "name": "predict_sirna_efficiency",
                    "args": {"sequence": seq},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
                {
                    "name": "check_off_target",
                    "args": {"sequence": seq},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
            ],
        )
    if not ai_msg.tool_calls:
        seq = _extract_rna_sequence(state.get("input_sequence", ""))
        ai_msg = AIMessage(
            content="Specialist repaired: model returned no tool_calls, injected required calls.",
            tool_calls=[
                {
                    "name": "predict_sirna_efficiency",
                    "args": {"sequence": seq},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
                {
                    "name": "check_off_target",
                    "args": {"sequence": seq},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
            ],
        )
    state["messages"] = state.get("messages", []) + [ai_msg]
    return state


def tool_execution_node(state: AgentState) -> AgentState:
    """Execute tool calls emitted by specialist LLM message."""
    messages = state.get("messages", [])
    if not messages or not isinstance(messages[-1], AIMessage):
        return state

    ai_msg = messages[-1]
    out_messages: list[Any] = []
    if not ai_msg.tool_calls:
        seq = _extract_rna_sequence(state.get("input_sequence", ""))
        ai_msg = AIMessage(
            content="Tool executor repaired missing tool calls.",
            tool_calls=[
                {
                    "name": "predict_sirna_efficiency",
                    "args": {"sequence": seq},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
                {
                    "name": "check_off_target",
                    "args": {"sequence": seq},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
            ],
        )
        messages = messages + [ai_msg]
    for call in ai_msg.tool_calls:
        tool_name = call["name"]
        tool_args = call.get("args", {})
        tool_obj = TOOLS_BY_NAME.get(tool_name)
        if not tool_obj:
            continue
        tool_result = tool_obj.invoke(tool_args)
        out_messages.append(
            ToolMessage(
                content=json.dumps(tool_result, ensure_ascii=True),
                tool_call_id=call["id"],
                name=tool_name,
            )
        )

        if tool_name == "predict_sirna_efficiency":
            state["efficiency_score"] = float(tool_result.get("efficiency_score", 0.0))
            state["candidate_sequence"] = str(tool_result.get("sequence", ""))
        elif tool_name == "check_off_target":
            state["off_target_genes"] = int(tool_result.get("off_target_genes", 0))
            if not state.get("candidate_sequence"):
                state["candidate_sequence"] = str(tool_result.get("sequence", ""))

    state["messages"] = messages + out_messages
    return state


def critic_node(state: AgentState) -> AgentState:
    """Use LLM to assess risk and choose retry/finish."""
    off_target = state.get("off_target_genes", 0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    llm = get_llm()

    critic_prompt = (
        "You are a critic for siRNA candidates.\n"
        "Given current scores, provide one short sentence in Chinese only.\n"
        "Do not provide unrelated content, code, or examples.\n"
        "Then on a new line output exactly: DECISION=retry or DECISION=finish."
    )
    critic_input = (
        f"candidate={state.get('candidate_sequence', '')}\n"
        f"efficiency={state.get('efficiency_score', 0.0)}\n"
        f"off_target_genes={off_target}\n"
        f"retry_count={retry_count}\n"
        f"max_retries={max_retries}"
    )
    try:
        critic_msg = llm.invoke(
            [SystemMessage(content=critic_prompt), AIMessage(content=critic_input)]
        )
        critic_text = _msg_text(critic_msg)
        if len(critic_text) > 400:
            raise ValueError("critic output too long")
        suspicious = ("class ", "public:", "题目", "```")
        if any(flag in critic_text.lower() for flag in [s.lower() for s in suspicious]):
            raise ValueError("critic output suspicious")
    except Exception as exc:
        decision = "retry" if (off_target > 0 and retry_count < max_retries) else "finish"
        critic_text = (
            "Connection fallback critic. "
            f"off_target_genes={off_target}, retry_count={retry_count}. error={exc}\n"
            f"DECISION={decision}"
        )
        critic_msg = AIMessage(content=critic_text)

    llm_retry = "decision=retry" in critic_text.lower()
    if (off_target > 0 and retry_count < max_retries) or (
        llm_retry and retry_count < max_retries
    ):
        state["retry_count"] = retry_count + 1
        state["next_action"] = "retry"
        state["messages"] = state.get("messages", []) + [critic_msg]
    else:
        state["next_action"] = "finish"
        state["final_report"] = (
            f"Final candidate: {state.get('candidate_sequence', '')}; "
            f"efficiency={state.get('efficiency_score', 0.0)}; "
            f"off_target_genes={off_target}; "
            f"retries={retry_count}."
        )
        state["messages"] = state.get("messages", []) + [critic_msg]
    return state


def route_after_router(state: AgentState) -> str:
    """Choose downstream branch after routing."""
    return "sirna_specialist" if state.get("route") == "sirna" else "end"


def route_after_critic(state: AgentState) -> str:
    """Choose whether to retry or finish."""
    return "sirna_specialist" if state.get("next_action") == "retry" else "end"
