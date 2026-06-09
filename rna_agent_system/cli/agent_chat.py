#!/usr/bin/env python3
"""Interactive CLI for the RNA Design Agent (replaces the deleted Streamlit UI).

Usage:
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" python cli/agent_chat.py
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402
from agent_core.file_manager import save_text_file  # noqa: E402
from agent_core.llm_config import get_deepseek_llm  # noqa: E402
from agent_core.planning.factory import build_planner  # noqa: E402
from agent_core.runner import AgentRunner  # noqa: E402
from agent_core.session_memory import SessionMemory  # noqa: E402
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry  # noqa: E402
from agent_core.workspace_manager import WorkspaceManager  # noqa: E402


def _truncate(text: str, limit: int = 220) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def _save_report(session_id: str, user_input: str, report: str) -> Path:
    """Save the final report to workspace/."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content = (
        f"# RNA Design Agent Report\n\n"
        f"**Session ID:** {session_id}\n\n"
        f"**Timestamp:** {timestamp}\n\n"
        f"**User Request:**\n\n{user_input}\n\n"
        f"---\n\n"
        f"**Final Report:**\n\n{report}\n"
    )
    filepath = save_text_file(content, prefix=f"report_{timestamp}", suffix=".md", session_id=session_id)
    return Path(filepath)


def _candidate_to_dict(c) -> dict[str, Any]:
    """Serialize a Candidate to a plain dict for JSON export."""
    meta = c.metadata or {}
    mb = meta.get("metrics_bundle", {})
    return {
        "rank": c.rank,
        "id": c.id,
        "source": c.source,
        "sequence": c.sequence,
        "sequence_type": c.sequence_type,
        "total_length": len(c.sequence),
        "scores": c.scores,
        "metadata": {
            k: (len(v) if isinstance(v, str) and len(v) > 200 else v)
            for k, v in meta.items()
            if k != "metrics_bundle"
        },
        "metrics": mb,
    }


def _save_workflow_results(state: dict[str, Any], session_id: str) -> Optional[Path]:
    """Save full workflow results to a JSON file under the session workspace."""
    wf = state.get("workflow_result")
    if wf is None:
        return None

    data: dict[str, Any] = {
        "task_id": getattr(wf, "task_id", ""),
        "success": getattr(wf, "success", False),
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
    }

    all_candidates = getattr(wf, "all_candidates", [])
    if all_candidates:
        data["candidate_count"] = len(all_candidates)
        data["candidates"] = [_candidate_to_dict(c) for c in all_candidates]

    best = getattr(wf, "best_candidate", None)
    if best:
        data["best_candidate"] = _candidate_to_dict(best)

    if getattr(wf, "summary", ""):
        data["summary"] = wf.summary
    if getattr(wf, "errors", []):
        data["errors"] = wf.errors

    tool_results = state.get("tool_results")
    if tool_results:
        data["tool_results"] = tool_results

    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    filepath = save_text_file(content, prefix="workflow_results", suffix=".json", session_id=session_id)
    return Path(filepath)


def _build_llm_context(user_input: str, state: dict[str, Any]) -> str:
    """Build a workflow-agnostic context string for LLM report generation."""
    wf = state.get("workflow_result")
    lines: list[str] = [f"用户请求: {user_input}"]

    if wf is None:
        tool_results = state.get("tool_results", {})
        if tool_results:
            lines.append(f"\n已执行工具: {', '.join(tool_results.keys())}")
            for tool_name, result in tool_results.items():
                lines.append(f"  {tool_name}: {str(result)[:300]}")
        return "\n".join(lines)

    lines.append(f"任务ID: {getattr(wf, 'task_id', 'N/A')}")
    lines.append(f"执行状态: {'成功' if getattr(wf, 'success', False) else '失败'}")

    if getattr(wf, "errors", []):
        lines.append(f"错误信息: {', '.join(wf.errors)}")

    all_candidates = getattr(wf, "all_candidates", [])
    if all_candidates:
        lines.append(f"\n候选结果数量: {len(all_candidates)}")

        best = getattr(wf, "best_candidate", None)
        if best:
            lines.append("\n最佳候选:")
            lines.append(f"  排名: #{best.rank if best.rank is not None else 'N/A'}")
            lines.append(f"  来源: {best.source}")
            lines.append(f"  序列长度: {len(best.sequence)} nt")
            if best.scores:
                for k, v in best.scores.items():
                    if isinstance(v, float):
                        lines.append(f"  {k}: {v:.4f}")
                    else:
                        lines.append(f"  {k}: {v}")

            meta = best.metadata or {}
            for seg_name, key in [
                ("5'UTR", "utr5_sequence"),
                ("CDS", "cds_sequence"),
                ("3'UTR", "utr3_sequence"),
            ]:
                seq = meta.get(key)
                if seq:
                    lines.append(f"  {seg_name}: {len(seq)} nt")

            mb = meta.get("metrics_bundle", {})
            if mb:
                lines.append("  关键指标:")
                for k, v in mb.items():
                    if v is not None and (not isinstance(v, str) or len(v) < 100):
                        lines.append(f"    {k}: {v}")

        if len(all_candidates) > 1:
            top_n = min(5, len(all_candidates))
            lines.append(f"\nTop {top_n} 候选概览:")
            for i, c in enumerate(all_candidates[:top_n], start=1):
                meta = c.metadata or {}
                mb = meta.get("metrics_bundle", {})
                parts = [f"#{i} {c.source}"]
                parts.append(f"长度={len(c.sequence)} nt")
                if meta.get("cds_sequence"):
                    parts.append(f"CDS={len(meta['cds_sequence'])} nt")
                total = c.scores.get("total_score")
                if total is not None:
                    parts.append(f"得分={total:.3f}")
                lines.append("  " + " | ".join(parts))
    else:
        summary = getattr(wf, "summary", "")
        if summary:
            lines.append(f"\n工作流摘要:\n{summary}")

        tool_results = state.get("tool_results", {})
        if tool_results:
            lines.append("\n工具执行结果:")
            for tool_name, result in tool_results.items():
                lines.append(f"  {tool_name}: {str(result)[:300]}")

    return "\n".join(lines)


def _generate_llm_report(user_input: str, state: dict[str, Any]) -> str:
    """Generate a human-readable report via LLM (workflow-agnostic)."""
    wf = state.get("workflow_result")
    if wf is None:
        return AgentRunner._format_final_report(state)  # pylint: disable=protected-access

    context = _build_llm_context(user_input, state)

    prompt = (
        "你是一位专业的生物信息学分析助手。请根据以下工作流执行结果，"
        "生成一份简洁、专业、人类易读的中文总结报告。\n\n"
        f"{context}\n\n"
        "报告要求:\n"
        "1. 用专业的中文撰写，术语准确\n"
        "2. 总结关键发现和最佳结果\n"
        "3. 如果有多个候选，列出 Top 候选的关键信息\n"
        "4. 对关键指标进行简要解读\n"
        "5. 给出使用建议或后续步骤\n"
        "6. 不要输出完整的长序列（序列保存在结果文件中），只描述特征和统计信息\n"
        "7. 使用清晰的格式（小标题、列表）\n\n"
        "请生成报告:"
    )

    try:
        llm = get_deepseek_llm(model="deepseek-v4-flash")
        messages = [
            SystemMessage(content="你是一位专业的生物信息学分析助手，擅长解读各类生物信息学工作流结果。"),
            HumanMessage(content=prompt),
        ]
        response = llm.invoke(messages)
        report = response.content if hasattr(response, "content") else str(response)
        return report.strip()
    except Exception as exc:
        print(f"  [Warning] LLM报告生成失败 ({exc})，使用默认报告格式。")
        return AgentRunner._format_final_report(state)  # pylint: disable=protected-access


def main() -> int:
    p = argparse.ArgumentParser(description="RNA Design Agent — Interactive CLI")
    p.add_argument(
        "--session-id",
        default=str(uuid.uuid4()),
        help="Session ID for multi-turn persistence (default: random UUID)",
    )
    p.add_argument(
        "--single",
        metavar="TEXT",
        help="Run a single query and exit (non-interactive mode)",
    )
    args = p.parse_args()

    # Use deepseek-v4-flash for faster planning (deepseek-v4-pro can take 30-60s)
    flash_planner = build_planner()
    flash_planner.llm = get_deepseek_llm(model="deepseek-v4-flash")

    runner = AgentRunner(
        planner=flash_planner,
        executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
        session_memory=SessionMemory(),
    )

    session_id = args.session_id

    if args.single:
        user_input = args.single
        print(f"\n[User] {user_input}\n")
        _run_once(runner, user_input, session_id, save_file=True)
        return 0

    # Interactive mode
    print("=" * 60)
    print("🧬 RNA Design Multi-Agent System — CLI")
    print("输入 RNA 序列或设计请求，例如：")
    print('  - AUGCUAACGUAGCUAUGCUA')
    print('  - 预测这条 RNA 的二级结构')
    print('  - design mRNA CDS for protein MKTLLIL...')
    print("输入 'exit' 或按 Ctrl-C 退出")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n>>> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见。")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("再见。")
            break

        _run_once(runner, user_input, session_id, save_file=True)

    return 0


def _run_once(runner: AgentRunner, user_input: str, session_id: str, *, save_file: bool = False) -> None:
    print("\n[Agent] 正在调用 DeepSeek API 进行任务规划，预计需要 10-20 秒...")

    final_state = None
    plan_steps: list[dict] = []
    executed_tools: list[str] = []

    try:
        for step_event in runner.stream(user_input, session_id=session_id):
            for node_name, node_state in step_event.items():
                if node_name == "router":
                    print("  → [Router] 任务已接收，开始规划...")

                elif node_name == "plan":
                    plan_steps = node_state.get("steps", [])
                    print(f"\n  → [Planner] DeepSeek 规划完成，共 {len(plan_steps)} 个步骤")
                    for s in plan_steps:
                        target = s.get("target", "?")
                        desc = s.get("description", "")
                        print(f"    - [{s.get('step_id', '?')}] {target}" + (f" — {desc}" if desc else ""))

                elif node_name == "progress":
                    entry = node_state
                    if entry.get("event") == "step_start":
                        target = entry.get("target", "?")
                        if target not in executed_tools:
                            executed_tools.append(target)
                        print(f"    ▶ 正在执行: {target}")
                    elif entry.get("event") == "step_done":
                        target = entry.get("target", "?")
                        ok = "✓" if entry.get("success", True) else "✗"
                        print(f"    {ok} 完成: {target}")
                    elif entry.get("event") == "plan_complete":
                        print("    ✓ 所有步骤执行完毕")
                    elif entry.get("event") == "generate_complete":
                        wf_name = entry.get("workflow", "workflow")
                        count = entry.get("candidate_count", 0)
                        print(f"    ℹ️  [{wf_name}] 已生成 {count} 个候选序列，开始评估...")
                    elif entry.get("event") == "evaluate_progress":
                        wf_name = entry.get("workflow", "workflow")
                        current = entry.get("current", 0)
                        total = entry.get("total", 0)
                        print(f"    ⏳ [{wf_name}] 评估进度: {current}/{total}", end="\r")

                elif node_name == "runner":
                    print("  → [Runner] 执行结束")

                final_state = node_state

    except Exception as exc:
        print(f"\n[Error] 工作流执行失败: {exc}")
        return

    if final_state is None:
        print("\n[Error] 未获取到执行结果。")
        return

    # Save full results to JSON (workflow-agnostic)
    json_path = _save_workflow_results(final_state, session_id)

    # Generate human-readable report via LLM
    print("\n[Agent] 正在生成人类易读的设计报告...")
    llm_report = _generate_llm_report(user_input, final_state)

    print(f"\n{'=' * 60}")
    print("📋 设计报告")
    print(f"{'=' * 60}")
    print(llm_report)
    print(f"{'=' * 60}")

    if json_path:
        print(f"\n[Saved] 完整结果已保存: {json_path}")

    # List other files in the session workspace
    try:
        wm = WorkspaceManager()
        files = wm.list_files(session_id)
        if files:
            print(f"[Saved] 本次会话工作区文件 ({len(files)} 个):")
            for f in files[:10]:
                print(f"    - {f}")
            if len(files) > 10:
                print(f"    ... 还有 {len(files) - 10} 个文件")
    except Exception:
        pass

    if save_file:
        try:
            report_path = _save_report(session_id, user_input, llm_report)
            print(f"[Saved] Markdown 报告已保存: {report_path}")
        except Exception as exc:
            print(f"[Warning] 保存报告失败: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
