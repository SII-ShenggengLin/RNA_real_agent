"""Node implementations for the MVP siRNA workflow graph."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from agent_core.file_manager import save_sequence
from agent_core.state import AgentState
from agent_core.tools import (
    check_off_target,
    design_mrna_cds_with_gemorna,
    mock_codon_optimization,
    predict_rna_secondary_structure,
    predict_sirna_efficiency,
)

SIRNA_TOOLS = [predict_sirna_efficiency, check_off_target]
MRNA_TOOLS = [mock_codon_optimization, predict_rna_secondary_structure, design_mrna_cds_with_gemorna]
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


def _extract_protein_sequence(text: str) -> str:
    candidates = re.findall(r"[A-Za-z\*]{8,}", text)
    if not candidates:
        return "MVSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDA"
    return max(candidates, key=len).upper()


def router_node(state: AgentState) -> AgentState:
    """Route by deterministic rules without LLM."""
    user_text = state.get("input_sequence", "").lower()
    if any(
        k in user_text
        for k in [
            "mrna",
            "rnafold",
            "fold",
            "structure",
            "二级结构",
            "密码子",
            "codon",
            "design",
            "设计",
            "gemorna",
            "protein",
            "cds",
            "utr",
        ]
    ):
        route = "mrna_specialist"
    elif any(k in user_text for k in ["sirna", "脱靶", "off-target"]):
        route = "sirna_specialist"
    else:
        # Default to mRNA for current integration testing focus (RNAfold).
        route = "mrna_specialist"
    decision_note = f"Router decision (rule-based): {route}"

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
    """Emit deterministic siRNA tool calls without LLM."""
    filepath = state.get("current_filepath")
    if not filepath:
        filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="sirna")
        state["current_filepath"] = filepath
        state["workspace_files"] = state.get("workspace_files", []) + [filepath]
    state["active_specialist"] = "sirna_specialist"
    ai_msg = AIMessage(
        content="siRNA specialist (rule-based): dispatch tool calls.",
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
    """Emit deterministic mRNA tool calls without LLM."""
    user_text = state.get("input_sequence", "").lower()
    state["active_specialist"] = "mrna_specialist"
    design_mode = any(k in user_text for k in ["design", "设计", "gemorna", "protein", "cds", "utr", "生成"])

    if design_mode:
        filepath = save_sequence(_extract_protein_sequence(state.get("input_sequence", "")), prefix="protein")
        state["current_filepath"] = filepath
        state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_calls = [
            {
                "name": "design_mrna_cds_with_gemorna",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch GEMORNA design."
    else:
        filepath = state.get("current_filepath")
        if not filepath:
            filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="mrna")
            state["current_filepath"] = filepath
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_calls = [
            {
                "name": "mock_codon_optimization",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            },
            {
                "name": "predict_rna_secondary_structure",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            },
        ]
        content = "mRNA specialist (rule-based): dispatch tool calls."

    ai_msg = AIMessage(content=content, tool_calls=tool_calls)
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
        user_text = state.get("input_sequence", "").lower()
        if state.get("active_specialist") == "sirna_specialist":
            fallback_calls = [
                {"name": "predict_sirna_efficiency", "args": {"filepath": filepath}},
                {"name": "check_off_target", "args": {"filepath": filepath}},
            ]
        elif any(k in user_text for k in ["design", "设计", "gemorna", "protein", "cds", "utr", "生成"]):
            fallback_calls = [
                {"name": "design_mrna_cds_with_gemorna", "args": {"filepath": filepath}},
            ]
        else:
            fallback_calls = [
                {"name": "mock_codon_optimization", "args": {"filepath": filepath}},
                {"name": "predict_rna_secondary_structure", "args": {"filepath": filepath}},
            ]
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
        elif tool_name == "predict_rna_secondary_structure":
            mfe_match = re.search(r"mfe=([-+]?\d*\.?\d+)", str(tool_result))
            structure_match = re.search(r"structure=([^;]+)", str(tool_result))
            if mfe_match:
                state["mfe"] = float(mfe_match.group(1))
            if structure_match:
                structure = structure_match.group(1).strip()
                structure_filepath = save_sequence(structure, prefix="structure")
                state["structure_filepath"] = structure_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [structure_filepath]
        elif tool_name == "design_mrna_cds_with_gemorna":
            output_filepath = str(tool_result.get("output_filepath", ""))
            if output_filepath:
                state["current_filepath"] = output_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_filepath]
            state["candidate_sequence"] = str(tool_result.get("generated_sequence", ""))

            user_text = state.get("input_sequence", "").lower()
            if any(k in user_text for k in ["structure", "fold", "rnafold", "二级结构"]):
                fold_result = predict_rna_secondary_structure.invoke({"filepath": state["current_filepath"]})
                out_messages.append(
                    ToolMessage(
                        content=json.dumps(fold_result, ensure_ascii=True),
                        tool_call_id=f"call_{uuid.uuid4().hex[:8]}",
                        name="predict_rna_secondary_structure",
                    )
                )
                mfe_match = re.search(r"mfe=([-+]?\d*\.?\d+)", str(fold_result))
                structure_match = re.search(r"structure=([^;]+)", str(fold_result))
                if mfe_match:
                    state["mfe"] = float(mfe_match.group(1))
                if structure_match:
                    structure = structure_match.group(1).strip()
                    structure_filepath = save_sequence(structure, prefix="structure")
                    state["structure_filepath"] = structure_filepath
                    state["workspace_files"] = state.get("workspace_files", []) + [structure_filepath]

    state["messages"] = messages + out_messages
    return state


def critic_node(state: AgentState) -> AgentState:
    """Use hard rules only (no LLM) to decide pass/reject."""
    off_target = state.get("off_target_genes", 0)
    mfe = state.get("mfe", 0.0)
    cai_score = state.get("cai_score", 0.0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    specialist = state.get("active_specialist", "")

    hard_reject = False
    if specialist == "sirna_specialist" and off_target > 0:
        hard_reject = True
    user_text = state.get("input_sequence", "").lower()
    if specialist == "mrna_specialist" and any(k in user_text for k in ["structure", "fold", "rnafold", "二级结构"]) and mfe > -20.0:
        hard_reject = True
    should_retry = hard_reject and retry_count < max_retries

    if should_retry:
        state["retry_count"] = retry_count + 1
        state["next_action"] = "retry"
        state["critic_verdict"] = "reject"
        state["messages"] = state.get("messages", []) + [
            AIMessage(
                content=(
                    f"Critic (rule-based): reject and retry. "
                    f"specialist={specialist}, off_target={off_target}, mfe={mfe}, retry={retry_count + 1}"
                )
            )
        ]
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
        state["messages"] = state.get("messages", []) + [
            AIMessage(
                content=(
                    f"Critic (rule-based): pass. "
                    f"specialist={specialist}, off_target={off_target}, mfe={mfe}"
                )
            )
        ]
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
