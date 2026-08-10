#!/usr/bin/env python3
"""Form-driven interactive CLI for the RNA Design Agent (TUI)."""

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

CLI_DIR = Path(__file__).resolve().parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from agent_core.file_manager import save_text_file  # noqa: E402
from agent_core.form import FormSchemaBuilder, FormValidator  # noqa: E402
from agent_core.pipeline.models import PipelinePlan, PipelineResult  # noqa: E402
from agent_core.runner import AgentRunner  # noqa: E402
from agent_core.session_memory import SessionMemory  # noqa: E402
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry  # noqa: E402
from agent_core.workspace_manager import WorkspaceManager  # noqa: E402

import resource_checker  # noqa: E402
import service_orchestrator  # noqa: E402


_WORKFLOW_LIST: list[tuple[str, str, str]] = [
    ("1", "mrna_cds_design", "mRNA CDS 设计"),
    ("2", "full_length_mrna_design", "全长 mRNA 设计"),
    ("3", "mrna_sequence_scoring", "mRNA 序列评分"),
    ("4", "sirna_design", "siRNA 设计"),
    ("5", "sgrna_design", "sgRNA 设计"),
    ("6", "rna_secondary_structure_design", "RNA 二级结构设计"),
    ("7", "rna_tertiary_structure_design", "RNA 三级结构设计"),
    ("8", "rna_aptamer_design", "RNA 适配体设计"),
    ("9", "rna_small_molecule_interaction", "RNA-小分子相互作用预测"),
    ("10", "aso_target_screening", "ASO 靶点筛选"),
    ("11", "ires_prediction", "IRES 预测"),
]


def _select_workflows() -> list[str]:
    """Prompt the user to select one or more workflows by number."""
    print("\n可用 Workflow（支持多选，输入编号如 1,3,5）：")
    for num, wf_key, desc in _WORKFLOW_LIST:
        print(f"  [{num}] {desc}  ({wf_key})")

    while True:
        raw = input("\n请选择: ").strip()
        if not raw:
            print("输入不能为空，请重新选择。")
            continue

        selected: list[str] = []
        invalid: list[str] = []
        for part in raw.split(","):
            part = part.strip()
            matched: Optional[str] = None
            for num, wf_key, _ in _WORKFLOW_LIST:
                if part == num:
                    matched = wf_key
                    break
            if matched:
                selected.append(matched)
            else:
                invalid.append(part)

        if invalid:
            print(f"无效选项: {', '.join(invalid)}，请重新输入。")
            continue
        if not selected:
            print("未选择任何 workflow，请重新输入。")
            continue

        return selected


def _select_active_workflow(enabled_workflows: list[str]) -> Optional[str]:
    """Ask the user to pick the workflow for the current turn."""
    print(f"\n当前已启用 workflow: {', '.join(enabled_workflows)}")
    mapping = {str(i + 1): wf for i, wf in enumerate(enabled_workflows)}
    for num, wf in mapping.items():
        print(f"  [{num}] {wf}")

    while True:
        raw = input("本次使用哪个 workflow? ").strip()
        if raw in mapping:
            return mapping[raw]
        if raw.lower() in ("exit", "quit", "q"):
            return None
        print("无效选项，请重新输入。")


def _candidate_to_dict(c) -> dict[str, Any]:
    """Serialize a Candidate to a plain dict for JSON export."""
    meta = c.metadata or {}
    mb = meta.get("metrics_bundle", {})
    scores = dict(c.scores or {})
    for k, v in mb.items():
        if k not in scores:
            scores[k] = v
    return {
        "rank": c.rank,
        "id": c.id,
        "source": c.source,
        "sequence": c.sequence,
        "sequence_type": c.sequence_type,
        "total_length": len(c.sequence),
        "total_score": scores.get("total_score"),
        "scores": scores,
        "metadata": {
            k: (f"{v[:200]}...(truncated)" if isinstance(v, str) and len(v) > 200 else v)
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

    data["_diagnosis_history"] = state.get("_diagnosis_history", [])
    data["_quality_auto_retry"] = state.get("_quality_auto_retry", False)
    data["retry_count"] = state.get("retry_count", 0)
    if state.get("_quality_review_error"):
        data["_quality_review_error"] = state["_quality_review_error"]

    data["_user_explicit_params"] = state.get("_user_explicit_params", [])
    # NOTE (2026-07-20 fix): the BMC coordination trace is written by each BMC
    # workflow's ``bmc_finalize`` into ``result._state_writeback["_bmc_trace"]``
    # (INTERFACE_LOCKS §14 audit field). ``state`` never carries it, so without
    # this fallback the artifact's ``_bmc_trace`` was always ``[]``.
    bmc_trace = state.get("_bmc_trace") or []
    if not bmc_trace:
        wf_writeback = getattr(wf, "_state_writeback", None) or {}
        if isinstance(wf_writeback, dict):
            bmc_trace = wf_writeback.get("_bmc_trace") or []
    data["_bmc_trace"] = bmc_trace
    data["_tool_timings"] = state.get("_tool_timings", {})
    data["_last_form_params"] = state.get("_last_form_params", {})

    if wf is not None:
        wf_state = getattr(wf, "_state_writeback", None) or {}
        if isinstance(wf_state, dict):
            wf_input = (
                wf_state.get("_workflow_params")
                or wf_state.get("_aso_input")
                or wf_state.get("_sirna_input")
            )
            if wf_input:
                data["workflow_input"] = wf_input
        trace = getattr(wf, "trace", [])
        if trace:
            data["trace"] = [rec.model_dump(mode="json") for rec in trace]

    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    filepath = save_text_file(content, prefix="workflow_results", suffix=".json", session_id=session_id)
    return Path(filepath)


def _save_report(session_id: str, report: str) -> Path:
    """Save the final report to workspace/."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content = (
        f"# RNA Design Agent Report\n\n"
        f"**Session ID:** {session_id}\n\n"
        f"**Timestamp:** {timestamp}\n\n"
        f"---\n\n"
        f"{report}\n"
    )
    return Path(save_text_file(content, prefix=f"report_{timestamp}", suffix=".md", session_id=session_id))


def _load_prefilled(runner: AgentRunner, session_id: str, workflow: str) -> dict[str, Any]:
    """Load last form params for the selected workflow."""
    if runner.memory is None:
        return {}
    state = runner.memory.load(session_id)
    by_workflow = state.get("_last_form_params_by_workflow", {})
    return dict(by_workflow.get(workflow, {}))


def _collect_form_params(runner: AgentRunner, workflow: str, prefilled: dict[str, Any]) -> dict[str, Any]:
    """Render the TUI form and validate the user input."""
    wf = runner.workflow_registry.get(workflow)
    if wf is None or not hasattr(wf, "input_model") or wf.input_model is None:
        raise ValueError(f"Workflow {workflow} has no input model")

    from agent_core.form import TuiFormRenderer  # lazy: only needed for interactive TUI  # noqa: E402

    schema = FormSchemaBuilder.from_pydantic_model(workflow, wf.input_model)
    while True:
        raw_values = TuiFormRenderer.render(schema, prefilled=prefilled)
        if not raw_values:
            raise KeyboardInterrupt("User cancelled the form")
        coerced, _ = FormValidator.validate(schema, raw_values)
        coerced, errors = FormValidator.validate_with_model(wf.input_model, coerced)
        if not errors:
            return coerced
        print("\n参数校验失败:")
        for err in errors:
            print(f"  - {err}")
        input("按 Enter 重新填写...")
        prefilled = coerced


def _load_pipeline_plan(path: str) -> PipelinePlan:
    """Load a PipelinePlan from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Pipeline file must contain a JSON object, got {type(data).__name__}")
    plan = PipelinePlan.model_validate(data)
    if not plan.plan_id:
        plan.plan_id = Path(path).stem
    return plan


def _required_workflows(plan: PipelinePlan) -> list[str]:
    """Return the unique workflows referenced by a pipeline plan."""
    return list(dict.fromkeys(n.workflow for n in plan.nodes))


def _save_pipeline_results(
    pipeline_result: PipelineResult,
    session_id: str,
) -> tuple[Optional[Path], Path]:
    """Save a multi-node pipeline result to JSON and Markdown artifacts."""
    data: dict[str, Any] = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "plan_id": pipeline_result.plan_id,
        "success": pipeline_result.success,
        "errors": pipeline_result.errors,
        "final_report": pipeline_result.final_report,
        "pipeline_result": pipeline_result.model_dump(mode="json"),
    }
    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    json_path = Path(
        save_text_file(content, prefix="pipeline_results", suffix=".json", session_id=session_id)
    )
    report_path = _save_report(session_id, pipeline_result.final_report)
    return json_path, report_path


def _run_pipeline(
    runner: AgentRunner,
    session_id: str,
    plan: PipelinePlan,
    *,
    save_file: bool = True,
) -> PipelineResult:
    """Execute a multi-node PipelinePlan through the CLI."""
    print(f"\n[Agent] 正在执行 pipeline: {plan.plan_id} ({len(plan.nodes)} 个节点) ...")
    for idx, node_id in enumerate(plan.topological_order(), start=1):
        node = plan.get_node(node_id)
        print(f"  → 节点 {idx}: {node_id} ({node.workflow})")

    pipeline_result = runner.run_pipeline(plan)

    print(f"\n{'=' * 60}")
    print("📋 Pipeline 综合报告")
    print(f"{'=' * 60}")
    print(pipeline_result.final_report)
    print(f"{'=' * 60}")

    if save_file:
        try:
            json_path, report_path = _save_pipeline_results(pipeline_result, session_id)
            print(f"\n[Saved] Pipeline 完整结果已保存: {json_path}")
            print(f"[Saved] Markdown 报告已保存: {report_path}")
        except Exception as exc:
            print(f"[Warning] 保存 pipeline 结果失败: {exc}")

    return pipeline_result


def _run_once(
    runner: AgentRunner,
    session_id: str,
    explicit_workflow: str,
    *,
    form_params: Optional[dict[str, Any]] = None,
    save_file: bool = True,
) -> bool:
    """Run one form-driven turn. Returns True on success, False on failure."""
    if form_params is None:
        prefilled = _load_prefilled(runner, session_id, explicit_workflow)
        form_params = _collect_form_params(runner, explicit_workflow, prefilled)

    print(f"\n[Agent] 正在执行 workflow: {explicit_workflow} ...")

    final_state = None
    try:
        for step_event in runner.stream_form(
            form_params,
            session_id=session_id,
            explicit_workflow=explicit_workflow,
        ):
            for node_name, node_state in step_event.items():
                if node_name == "router":
                    print(f"  → [Router] 目标={explicit_workflow}")
                elif node_name == "plan":
                    plan_steps = node_state.get("steps", [])
                    print(f"\n  → [Planner] 规划完成，共 {len(plan_steps)} 个步骤")
                    for s in plan_steps:
                        print(f"    - [{s.get('step_id', '?')}] {s.get('target', '?')}")
                elif node_name == "progress":
                    entry = node_state
                    if entry.get("event") == "step_start":
                        print(f"    ▶ 正在执行: {entry.get('target', '?')}")
                    elif entry.get("event") == "step_done":
                        ok = "✓" if entry.get("success", True) else "✗"
                        print(f"    {ok} 完成: {entry.get('target', '?')}")
                    elif entry.get("event") == "generate_complete":
                        print(f"    ℹ️ 已生成 {entry.get('candidate_count', 0)} 个候选序列")
                elif node_name == "runner":
                    print("  → [Runner] 执行结束")
                final_state = node_state
    except Exception as exc:
        print(f"\n[Error] 工作流执行失败: {exc}")
        return False

    if final_state is None:
        print("\n[Error] 未获取到执行结果。")
        return False

    json_path = _save_workflow_results(final_state, session_id)

    report = AgentRunner._format_final_report(final_state)
    print(f"\n{'=' * 60}")
    print("📋 设计报告")
    print(f"{'=' * 60}")
    print(report)
    print(f"{'=' * 60}")

    if json_path:
        print(f"\n[Saved] 完整结果已保存: {json_path}")

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
            report_path = _save_report(session_id, report)
            print(f"[Saved] Markdown 报告已保存: {report_path}")
        except Exception as exc:
            print(f"[Warning] 保存报告失败: {exc}")

    return True


def main() -> int:
    p = argparse.ArgumentParser(description="RNA Design Agent — Form-driven TUI CLI")
    p.add_argument(
        "--session-id",
        default=str(uuid.uuid4()),
        help="Session ID for multi-turn persistence (default: random UUID)",
    )
    p.add_argument(
        "--workflow",
        metavar="NAME",
        help="Skip workflow selection and use this workflow",
    )
    p.add_argument(
        "--params-file",
        metavar="PATH",
        help="JSON file with form params for non-interactive single execution",
    )
    p.add_argument(
        "--pipeline-file",
        metavar="PATH",
        help="JSON file with a multi-node PipelinePlan for non-interactive execution",
    )
    args = p.parse_args()

    if args.params_file and not args.workflow:
        print("[Error] --params-file 需要同时指定 --workflow")
        return 1
    if args.pipeline_file and (args.workflow or args.params_file):
        print("[Error] --pipeline-file 不能和 --workflow/--params-file 同时使用")
        return 1

    print("=" * 60)
    print("🧬 RNA Design Multi-Agent System — Form-driven CLI")
    print("=" * 60)
    print("\n[系统检查] 正在检查运行环境...")
    ok, msg = resource_checker.check_all()
    if ok:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ {msg}")
        print("\n资源不足，无法启动。请确保系统满足最低要求后重试。")
        return 1

    runner = AgentRunner(
        executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
        session_memory=SessionMemory(),
        quality_review_enabled=True,
        quality_auto_retry=False,
    )

    session_id = args.session_id

    if args.pipeline_file:
        try:
            plan = _load_pipeline_plan(args.pipeline_file)
        except Exception as exc:
            print(f"[Error] 无法加载 pipeline 文件: {exc}")
            return 1

        print(f"\n[Pipeline] 已从 {args.pipeline_file} 加载计划")
        selected_workflows = _required_workflows(plan)
        print("[服务启动] 正在启动所需微服务...")
        svc_ok, svc_errors = service_orchestrator.ensure_multi_workflow_services_ready(selected_workflows)
        if svc_ok:
            print("  ✓ 所有微服务已就绪")
        else:
            print("  ! 部分微服务启动失败:")
            for err in svc_errors:
                print(f"    - {err}")
            cont = input("\n是否继续? (y/n): ").strip().lower()
            if cont != "y":
                return 1

        _run_pipeline(runner, session_id, plan, save_file=True)
        return 0

    if args.workflow:
        selected_workflows = [args.workflow]
    else:
        selected_workflows = _select_workflows()

    print("\n[服务启动] 正在启动所需微服务...")
    svc_ok, svc_errors = service_orchestrator.ensure_multi_workflow_services_ready(selected_workflows)
    if svc_ok:
        print("  ✓ 所有微服务已就绪")
    else:
        print("  ! 部分微服务启动失败:")
        for err in svc_errors:
            print(f"    - {err}")
        # NOTE (2026-07 experiment incident): a bare ``input()`` here crashes with
        # EOFError when stdin is not a TTY (batch drivers, nohup, CI), killing the
        # run in seconds with a misleading "cli_failure".  Only prompt on a real
        # terminal; otherwise continue — the workflow-level pre-flight
        # (``ensure_workflow_services_ready``) re-validates services at run time,
        # and a genuinely dead service fails the run with a proper error record.
        # Do NOT revert this to an unconditional prompt.
        if sys.stdin.isatty():
            cont = input("\n是否继续? (y/n): ").strip().lower()
            if cont != "y":
                return 1
        else:
            print("  ! 非交互模式，自动继续（工作流级预检会在运行时再次校验服务）")

    if args.params_file:
        with open(args.params_file, "r", encoding="utf-8") as f:
            form_params = json.load(f)
        print(f"\n[Params] 已从 {args.params_file} 加载参数")
        ok = _run_once(runner, session_id, selected_workflows[0], form_params=form_params, save_file=True)
        return 0 if ok else 1

    print("\n" + "=" * 60)
    print("进入多轮对话模式")
    print("输入 'exit' 退出")
    print("=" * 60)

    while True:
        try:
            active_wf = _select_active_workflow(selected_workflows)
            if active_wf is None:
                print("再见。")
                break
        except (KeyboardInterrupt, EOFError):
            print("\n再见。")
            break

        try:
            _run_once(runner, session_id, active_wf, save_file=True)
        except KeyboardInterrupt:
            print("\n再见。")
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
