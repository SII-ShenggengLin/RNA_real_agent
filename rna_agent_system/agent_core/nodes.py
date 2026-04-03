"""Node implementations for the MVP siRNA workflow graph."""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from agent_core.file_manager import save_sequence
from agent_core.llm_config import get_llm
from agent_core.state import AgentState
from agent_core.tools import (
    check_off_target,
    mock_codon_optimization,
    mock_rna_fold,
    predict_sirna_efficiency,
)

SIRNA_TOOLS = [predict_sirna_efficiency, check_off_target]
MRNA_TOOLS = [mock_codon_optimization, mock_rna_fold]
TOOLS = SIRNA_TOOLS + MRNA_TOOLS
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
        "- sirna_specialist (for siRNA design, siRNA efficacy, off-target analysis)\n"
        "- mrna_specialist (for mRNA design, codon optimization, structure/folding prediction)\n"
        "- unsupported (for anything else)\n"
        "No extra words."
    )
    try:
        decision = llm.invoke([SystemMessage(content=prompt), *state.get("messages", [])])
        text = _msg_text(decision).strip().lower()
        if "mrna_specialist" in text:
            route = "mrna_specialist"
        elif "sirna_specialist" in text:
            route = "sirna_specialist"
        else:
            route = "unsupported"
        decision_note = f"Router decision: {route}"
    except Exception as exc:
        route = "sirna_specialist"
        decision_note = (
            "Router fallback: LLM connection failed, default to sirna_specialist. "
            f"error={exc}"
        )

    state["current_task"] = (
        "sirna_design"
        if route == "sirna_specialist"
        else "mrna_design" if route == "mrna_specialist" else "unsupported"
    )
    state["route"] = (
        "sirna" if route == "sirna_specialist" else "mrna" if route == "mrna_specialist" else "unsupported"
    )
    state["messages"] = state.get("messages", []) + [
        AIMessage(content=decision_note)
    ]
    return state


def sirna_specialist_node(state: AgentState) -> AgentState:
    """Use LLM + siRNA tools to produce tool calls."""
    llm = get_llm().bind_tools(SIRNA_TOOLS)
    filepath = state.get("current_filepath")
    if not filepath:
        filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="sirna")
        state["current_filepath"] = filepath
        state["workspace_files"] = state.get("workspace_files", []) + [filepath]
    state["active_specialist"] = "sirna_specialist"

    prompt = (
        "You are a siRNA specialist.\n"
        "You must perform ONLY tool calls.\n"
        "Tool parameters MUST use workspace filepath, not raw sequence.\n"
        f"Current sequence filepath: {filepath}\n"
        "MUST call:\n"
        "1) predict_sirna_efficiency(filepath=...)\n"
        "2) check_off_target(filepath=...)\n"
    )
    try:
        ai_msg = llm.invoke([SystemMessage(content=prompt), *state.get("messages", [])])
    except Exception:
        ai_msg = AIMessage(
            content="Specialist fallback: generated deterministic candidate and tool calls.",
            tool_calls=[
                {
                    "name": "predict_sirna_efficiency",
                    "args": {"filepath": filepath},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
                {
                    "name": "check_off_target",
                    "args": {"filepath": filepath},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
            ],
        )
    if not ai_msg.tool_calls:
        ai_msg = AIMessage(
            content="Specialist repaired: model returned no tool_calls, injected required calls.",
            tool_calls=[
                {
                    "name": "predict_sirna_efficiency",
                    "args": {"filepath": filepath},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
                {
                    "name": "check_off_target",
                    "args": {"filepath": filepath},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
            ],
        )
    state["messages"] = state.get("messages", []) + [ai_msg]
    return state


def mrna_specialist_node(state: AgentState) -> AgentState:
    """Use LLM + mRNA tools to produce tool calls."""
    llm = get_llm().bind_tools(MRNA_TOOLS)
    filepath = state.get("current_filepath")
    if not filepath:
        filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="mrna")
        state["current_filepath"] = filepath
        state["workspace_files"] = state.get("workspace_files", []) + [filepath]
    state["active_specialist"] = "mrna_specialist"

    prompt = (
        "You are an mRNA specialist.\n"
        "You must perform ONLY tool calls.\n"
        "Tool parameters MUST use workspace filepath, not raw sequence.\n"
        f"Current mRNA filepath: {filepath}\n"
        "MUST call:\n"
        "1) mock_codon_optimization(filepath=...)\n"
        "2) mock_rna_fold(filepath=...)\n"
    )
    try:
        ai_msg = llm.invoke([SystemMessage(content=prompt), *state.get("messages", [])])
    except Exception:
        ai_msg = AIMessage(
            content="mRNA specialist fallback: generated deterministic tool calls.",
            tool_calls=[
                {
                    "name": "mock_codon_optimization",
                    "args": {"filepath": filepath},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
                {
                    "name": "mock_rna_fold",
                    "args": {"filepath": filepath},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
            ],
        )
    if not ai_msg.tool_calls:
        ai_msg = AIMessage(
            content="mRNA specialist repaired missing tool calls.",
            tool_calls=[
                {
                    "name": "mock_codon_optimization",
                    "args": {"filepath": filepath},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                },
                {
                    "name": "mock_rna_fold",
                    "args": {"filepath": filepath},
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
        filepath = state.get("current_filepath")
        if not filepath:
            filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="seq")
            state["current_filepath"] = filepath
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        fallback_calls = (
            [
                {"name": "predict_sirna_efficiency", "args": {"filepath": filepath}},
                {"name": "check_off_target", "args": {"filepath": filepath}},
            ]
            if state.get("active_specialist") == "sirna_specialist"
            else [
                {"name": "mock_codon_optimization", "args": {"filepath": filepath}},
                {"name": "mock_rna_fold", "args": {"filepath": filepath}},
            ]
        )
        ai_msg = AIMessage(
            content="Tool executor repaired missing tool calls.",
            tool_calls=[
                {
                    "name": call["name"],
                    "args": call["args"],
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                }
                for call in fallback_calls
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
            state["current_filepath"] = str(tool_result.get("filepath", state.get("current_filepath", "")))
        elif tool_name == "check_off_target":
            state["off_target_genes"] = int(tool_result.get("off_target_genes", 0))
            if not state.get("candidate_sequence"):
                state["candidate_sequence"] = str(tool_result.get("sequence", ""))
            state["current_filepath"] = str(tool_result.get("filepath", state.get("current_filepath", "")))
        elif tool_name == "mock_codon_optimization":
            state["cai_score"] = float(tool_result.get("cai_score", 0.0))
            optimized_filepath = str(tool_result.get("optimized_filepath", ""))
            if optimized_filepath:
                state["current_filepath"] = optimized_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [optimized_filepath]
        elif tool_name == "mock_rna_fold":
            state["mfe"] = float(tool_result.get("mfe", 0.0))
            structure_filepath = str(tool_result.get("structure_filepath", ""))
            if structure_filepath:
                state["structure_filepath"] = structure_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [structure_filepath]

    state["messages"] = messages + out_messages
    return state


def critic_node(state: AgentState) -> AgentState:
    """Use LLM + hard constraints to decide pass/reject and retry loop."""
    off_target = state.get("off_target_genes", 0)
    mfe = state.get("mfe", 0.0)
    cai_score = state.get("cai_score", 0.0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    specialist = state.get("active_specialist", "")
    llm = get_llm()

    critic_prompt = (
        "你是RNA工作流的Critic。\n"
        "请基于给定指标输出两行：\n"
        "第1行：简短评估和修改建议。\n"
        "第2行：VERDICT=pass 或 VERDICT=reject。\n"
        "禁止输出无关内容。"
    )
    critic_input = (
        f"active_specialist={specialist}\n"
        f"candidate={state.get('candidate_sequence', '')}\n"
        f"efficiency={state.get('efficiency_score', 0.0)}\n"
        f"off_target_genes={off_target}\n"
        f"cai_score={cai_score}\n"
        f"mfe={mfe}\n"
        f"retry_count={retry_count}, max_retries={max_retries}"
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

    hard_reject = False
    if specialist == "sirna_specialist" and off_target > 0:
        hard_reject = True
    if specialist == "mrna_specialist" and mfe > -20.0:
        hard_reject = True

    llm_reject = "verdict=reject" in critic_text.lower()
    should_retry = (hard_reject or llm_reject) and retry_count < 3

    if should_retry:
        state["retry_count"] = retry_count + 1
        state["next_action"] = "retry"
        state["critic_verdict"] = "reject"
        state["messages"] = state.get("messages", []) + [critic_msg]
    else:
        state["next_action"] = "finish"
        state["critic_verdict"] = "pass"
        state["final_report"] = (
            f"specialist={specialist}; "
            f"filepath={state.get('current_filepath', '')}; "
            f"efficiency={state.get('efficiency_score', 0.0)}; "
            f"off_target_genes={off_target}; "
            f"cai_score={cai_score}; "
            f"mfe={mfe}; "
            f"retries={retry_count}"
        )
        state["messages"] = state.get("messages", []) + [critic_msg]
    return state


def route_after_router(state: AgentState) -> str:
    """Choose downstream branch after routing."""
    if state.get("route") == "sirna":
        return "sirna_specialist"
    if state.get("route") == "mrna":
        return "mrna_specialist"
    return "end"


def route_after_critic(state: AgentState) -> str:
    """Choose whether to retry or finish."""
    if state.get("next_action") != "retry":
        return "end"
    return state.get("active_specialist", "sirna_specialist")
