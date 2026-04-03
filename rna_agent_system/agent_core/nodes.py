"""Node implementations for the MVP siRNA workflow graph."""

from __future__ import annotations

from agent_core.state import AgentState
from agent_core.tools import check_off_target, predict_sirna_efficiency

RNA_ALPHABET = ("A", "U", "G", "C")


def router_node(state: AgentState) -> AgentState:
    """Route request to siRNA pipeline for this MVP."""
    text = state.get("input_sequence", "").upper()
    task = "sirna_design" if any(base in text for base in RNA_ALPHABET) else "sirna_design"
    state["current_task"] = task
    state["route"] = "sirna"
    state["messages"] = state.get("messages", []) + [
        {"role": "assistant", "content": "Router: route to siRNA specialist."}
    ]
    return state


def sirna_specialist_node(state: AgentState) -> AgentState:
    """Produce candidate sequence; mutate slightly when retrying."""
    source = state.get("input_sequence", "").upper().replace("T", "U")
    source = "".join(ch for ch in source if ch in RNA_ALPHABET)
    if not source:
        source = "AUGCUAACGUAGCUA"

    retry_count = state.get("retry_count", 0)
    candidate = source[:21] if len(source) > 21 else source
    if retry_count > 0 and candidate:
        idx = retry_count % len(candidate)
        replacement = RNA_ALPHABET[retry_count % len(RNA_ALPHABET)]
        candidate = candidate[:idx] + replacement + candidate[idx + 1 :]

    state["candidate_sequence"] = candidate
    state["messages"] = state.get("messages", []) + [
        {
            "role": "assistant",
            "content": f"siRNA Specialist: propose candidate (attempt {retry_count + 1}).",
        }
    ]
    return state


def tool_execution_node(state: AgentState) -> AgentState:
    """Call both mock tools and write outputs into state."""
    seq = state["candidate_sequence"]
    efficiency_payload = predict_sirna_efficiency.invoke({"sequence": seq})
    off_target_payload = check_off_target.invoke({"sequence": seq})

    state["efficiency_score"] = float(efficiency_payload["efficiency_score"])
    state["off_target_genes"] = int(off_target_payload["off_target_genes"])
    state["messages"] = state.get("messages", []) + [
        {
            "role": "assistant",
            "content": (
                "Tool Executor: "
                f"efficiency={state['efficiency_score']}, "
                f"off_target_genes={state['off_target_genes']}."
            ),
        }
    ]
    return state


def critic_node(state: AgentState) -> AgentState:
    """Judge output quality and decide retry or finish."""
    off_target = state.get("off_target_genes", 0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if off_target > 0 and retry_count < max_retries:
        state["retry_count"] = retry_count + 1
        state["next_action"] = "retry"
        state["messages"] = state.get("messages", []) + [
            {
                "role": "assistant",
                "content": "Critic: off-target risk detected, regenerate candidate.",
            }
        ]
    else:
        state["next_action"] = "finish"
        state["final_report"] = (
            f"Final candidate: {state.get('candidate_sequence', '')}; "
            f"efficiency={state.get('efficiency_score', 0.0)}; "
            f"off_target_genes={off_target}; "
            f"retries={retry_count}."
        )
        state["messages"] = state.get("messages", []) + [
            {"role": "assistant", "content": "Critic: candidate accepted."}
        ]
    return state


def route_after_router(state: AgentState) -> str:
    """Choose downstream branch after routing."""
    return "sirna_specialist" if state.get("route") == "sirna" else "end"


def route_after_critic(state: AgentState) -> str:
    """Choose whether to retry or finish."""
    return "sirna_specialist" if state.get("next_action") == "retry" else "end"
