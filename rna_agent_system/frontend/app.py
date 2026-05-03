"""Streamlit chat UI for the RNA Design multi-agent workflow."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import streamlit as st

# Make sibling modules importable when Streamlit runs this file directly.
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from agent_core.graph import compiled_graph
from agent_core.runner import AgentRunner
from agent_core.session_memory import SessionMemory
from agent_core.state import default_state
from agent_core.planning.rule_based.planner import RuleBasedPlanner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

# Unified entry point: AgentRunner wraps both the new path and the legacy graph.
_runner = AgentRunner(
    planner=RuleBasedPlanner(),
    executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
    compiled_graph=compiled_graph,
    session_memory=SessionMemory(),
)


st.set_page_config(page_title="RNA Design Agent", page_icon="🧬", layout="wide")
st.title("🧬 RNA Design Multi-Agent System")
st.caption("Rule-based workflow: Router → Specialist → Tool Execution → Critic")


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


def _message_text(message_obj) -> str:
    if hasattr(message_obj, "content"):
        content = message_obj.content
        return content if isinstance(content, str) else str(content)
    if isinstance(message_obj, dict):
        return str(message_obj.get("content", ""))
    return str(message_obj)


def _truncate(text: str, limit: int = 220) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


for item in st.session_state.chat_history:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])


user_input = st.chat_input("输入RNA序列或设计请求，例如：AUGCUAACGUAGCUAUGCUA")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        status_box = st.empty()
        detail_box = st.empty()

        status_box.info("正在执行多智能体工作流...")
        detail_lines: list[str] = []

        final_state = None
        try:
            for step_event in _runner.stream_chat(user_input, session_id=st.session_state.session_id):
                for node_name, node_state in step_event.items():
                    msg = f"- `{node_name}` 执行完成"
                    detail_lines.append(msg)

                    if "messages" in node_state and node_state["messages"]:
                        latest = _message_text(node_state["messages"][-1])
                        detail_lines.append(f"  - {_truncate(latest)}")

                    # CRISOT INTERFACE LOCK (v0.2.0): 展示字段必须与 state.py / writebacks.py 同步
                    crisot_parts: list[str] = []
                    if "crisot_score" in node_state:
                        crisot_parts.append(f"score={node_state.get('crisot_score', 'N/A')}")
                    if "crisot_spec" in node_state:
                        crisot_parts.append(f"spec={node_state.get('crisot_spec', 'N/A')}")
                    if "crisot_off_target_count" in node_state:
                        crisot_parts.append(f"off_targets={node_state.get('crisot_off_target_count', 'N/A')}")
                    if "crisot_optimized_available" in node_state:
                        crisot_parts.append(f"optimized={node_state.get('crisot_optimized_available', False)}")
                    if "crisot_rescore_sgrna_count" in node_state:
                        crisot_parts.append(f"rescore_count={node_state.get('crisot_rescore_sgrna_count', 0)}")
                    if "crisot_fp_xgb_model" in node_state:
                        crisot_parts.append(f"fp_model={node_state.get('crisot_fp_xgb_model', '')}")
                    if crisot_parts:
                        detail_lines.append(f"  - CRISOT结果: {', '.join(crisot_parts)}")

                    # New-path workflow result display
                    wf_result = node_state.get("workflow_result")
                    if wf_result is not None and hasattr(wf_result, "best_candidate"):
                        bc = wf_result.best_candidate
                        if bc:
                            detail_lines.append(
                                f"  - Workflow best: score={bc.scores.get('total_score', 'N/A')} "
                                f"source={bc.source} len={len(bc.sequence)}"
                            )

                    detail_box.markdown("\n".join(detail_lines))
                    final_state = node_state
        except Exception as exc:
            status_box.error("工作流执行失败。请检查 LLM 网关连通性和 .env 配置。")
            st.exception(exc)
            st.stop()

        final_report = "流程执行完成，但未生成最终报告。"
        if final_state and final_state.get("final_report"):
            final_report = final_state["final_report"]
        elif final_state and final_state.get("workflow_result"):
            wf = final_state["workflow_result"]
            if wf and hasattr(wf, "summary"):
                final_report = f"Workflow complete: {wf.summary}"

        status_box.success("执行完成")
        st.markdown(f"**最终结果：** {final_report}")

    st.session_state.chat_history.append({"role": "assistant", "content": final_report})
