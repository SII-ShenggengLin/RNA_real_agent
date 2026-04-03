"""Streamlit chat UI for the MVP siRNA LangGraph workflow."""

from __future__ import annotations

import streamlit as st

from agent_core.graph import compiled_graph
from agent_core.state import default_state


st.set_page_config(page_title="RNA Design Agent (MVP)", page_icon="🧬", layout="wide")
st.title("🧬 RNA Design Multi-Agent System (MVP)")
st.caption("Phase 1: siRNA single-path workflow (Router -> Specialist -> Tools -> Critic)")


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


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
            for step_event in compiled_graph.stream(default_state(user_input)):
                for node_name, node_state in step_event.items():
                    msg = f"- `{node_name}` 执行完成"
                    detail_lines.append(msg)

                    if "messages" in node_state and node_state["messages"]:
                        latest = _message_text(node_state["messages"][-1])
                        detail_lines.append(f"  - {_truncate(latest)}")

                    if "efficiency_score" in node_state or "off_target_genes" in node_state:
                        eff = node_state.get("efficiency_score", "N/A")
                        off = node_state.get("off_target_genes", "N/A")
                        detail_lines.append(f"  - tool结果: efficiency={eff}, off_target_genes={off}")

                    detail_box.markdown("\n".join(detail_lines))
                    final_state = node_state
        except Exception as exc:
            status_box.error("工作流执行失败。请检查 LLM 网关连通性和 .env 配置。")
            st.exception(exc)
            st.stop()

        final_report = "流程执行完成，但未生成最终报告。"
        if final_state and final_state.get("final_report"):
            final_report = final_state["final_report"]

        status_box.success("执行完成")
        st.markdown(f"**最终结果：** {final_report}")

    st.session_state.chat_history.append({"role": "assistant", "content": final_report})
