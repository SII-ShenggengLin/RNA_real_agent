"""Layer 5 — AgentRunner: unified entry point for all presentation layers."""

from __future__ import annotations

import time
from typing import Any, Iterator, Optional, get_args, get_origin

from langchain_core.messages import AIMessage, HumanMessage

from agent_core.capabilities.base import build_default_capability_registry
from agent_core.planning.base import ExecutionController, Planner
from agent_core.planning.router import DeterministicRouter
from agent_core.session_memory import SessionMemory
from agent_core.file_manager import _SESSION_ID_CTX
from agent_core.state import AgentState, default_state
from agent_core.tool_executor import ToolExecutor
from pydantic import BaseModel
from pydantic.fields import PydanticUndefined
from agent_core.workflows import (
    AsoTargetScreeningWorkflow,
    FullLengthMrnaDesignWorkflow,
    IresPredictionWorkflow,
    MrnaCdsDesignWorkflow,
    MrnaSequenceScoringWorkflow,
    RnaAptamerDesignWorkflow,
    RnaSecondaryStructureDesignWorkflow,
    RnaSmallMoleculeInteractionWorkflow,
    RnaTertiaryStructureDesignWorkflow,
    SgRnaDesignWorkflow,
    SirnaDesignWorkflow,
)


class AgentRunner:
    """Unified façade used by FastAPI and CLI.

    Parameters
    ----------
    planner:
        Concrete ``Planner`` backend (``LLMPlanner``).
    executor:
        ``ToolExecutor`` used to build the ``CapabilityRegistry``.
    session_memory:
        Optional ``SessionMemory`` for multi-turn persistence.
        When *None* (default), every call to ``.run()`` starts from a
        fresh state — the single-turn behaviour.
    """

    def __init__(
        self,
        planner: Planner,
        executor: ToolExecutor,
        *,
        session_memory: Optional[SessionMemory] = None,
        llm_critic_enabled: bool = True,
        deterministic_router: Optional[DeterministicRouter] = None,
        persist_run: bool = False,
    ):
        self.planner = planner
        self.executor = executor
        self.llm_critic_enabled = llm_critic_enabled
        self.deterministic_router = deterministic_router or DeterministicRouter()
        self.persist_run = persist_run
        self.capability_registry = build_default_capability_registry(executor)
        # INTERFACE LOCK (v1.0.0) — AsoTargetScreening: sync with workflows/aso_target_screening.py
        # INTERFACE LOCK (v1.0.0) — MrnaSequenceScoring: sync with workflows/mrna_sequence_scoring.py
        # INTERFACE LOCK (v1.0.0) — FullLengthMrnaDesign: sync with workflows/full_length_mrna_design.py
        # INTERFACE LOCK (v1.0.0) — RnaAptamerDesign: sync with workflows/rna_aptamer_design.py
        # INTERFACE LOCK (v1.0.0) — RnaSmallMoleculeInteraction: sync with workflows/rna_small_molecule_interaction.py
        self.workflow_registry: dict[str, Any] = {
            "aso_target_screening": AsoTargetScreeningWorkflow(self.capability_registry),
            "mrna_cds_design": MrnaCdsDesignWorkflow(self.capability_registry),
            "mrna_sequence_scoring": MrnaSequenceScoringWorkflow(self.executor),
            "full_length_mrna_design": FullLengthMrnaDesignWorkflow(self.capability_registry),
            "rna_aptamer_design": RnaAptamerDesignWorkflow(self.capability_registry),
        # INTERFACE LOCK (v1.0.0) — RnaSecondaryStructureDesign: sync with workflows/rna_secondary_structure_design.py
            "rna_secondary_structure_design": RnaSecondaryStructureDesignWorkflow(self.capability_registry),
            "rna_small_molecule_interaction": RnaSmallMoleculeInteractionWorkflow(self.capability_registry),
            "rna_tertiary_structure_design": RnaTertiaryStructureDesignWorkflow(self.capability_registry),
            "sgrna_design": SgRnaDesignWorkflow(self.capability_registry),
            "sirna_design": SirnaDesignWorkflow(self.capability_registry),
            "ires_prediction": IresPredictionWorkflow(self.capability_registry),
        }
        self.controller = ExecutionController(
            capability_registry=self.capability_registry,
            workflow_registry=self.workflow_registry,
        )
        self._available_capabilities = self.capability_registry.list_names()
        self._available_workflows = list(self.workflow_registry.keys())
        self.memory = session_memory

    def _prepare_state(
        self,
        user_input: str,
        session_id: str,
        explicit_state: Optional[AgentState],
    ) -> AgentState:
        """Load or create state, inject user message and session_id, and return it."""
        if explicit_state is not None:
            state = explicit_state
            state["user_text"] = user_input
            state["session_id"] = session_id
            state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]
        else:
            if self.memory is not None:
                state = self.memory.load(session_id)
            else:
                state = default_state("")
            state["user_text"] = user_input
            state["session_id"] = session_id
            state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]
        # 新增：写入LLM Critic开关
        state["_llm_critic_enabled"] = self.llm_critic_enabled
        return state

    @staticmethod
    def _extract_param_schema(model_cls: type[BaseModel]) -> str:
        """Build a concise 'param=default (type) - description' summary from a Pydantic model."""
        parts: list[str] = []
        # Include class docstring as preamble so domain-specific warnings reach the LLM
        if model_cls.__doc__:
            parts.append(model_cls.__doc__.strip())
            parts.append("")
        for name, field_info in model_cls.model_fields.items():
            default = field_info.default
            if default is None and hasattr(field_info, "default_factory"):
                default = field_info.default_factory() if field_info.default_factory is not None else None
            # Skip private / internal fields
            if name.startswith("_"):
                continue
            annotation = field_info.annotation
            origin = get_origin(annotation)
            args = get_args(annotation)

            # Unwrap Optional[X]
            if origin is not None and len(args) == 2 and type(None) in args:
                annotation = args[0] if args[1] is type(None) else args[1]
                origin = get_origin(annotation)
                args = get_args(annotation)

            # Pretty-print Literal[...] so the LLM sees allowed values
            if origin is not None and hasattr(origin, "__name__") and origin.__name__ == "Literal":
                type_name = f"Literal[{', '.join(repr(v) for v in args)}]"
            else:
                type_name = getattr(annotation, "__name__", str(annotation))
            desc = field_info.description or ""
            if default is PydanticUndefined:
                default_str = "(required)"
            elif default is None:
                default_str = "None"
            else:
                default_str = repr(default)
            if desc:
                parts.append(f"  {name}={default_str} ({type_name}) — {desc}")
            else:
                parts.append(f"  {name}={default_str} ({type_name})")
        return "\n".join(parts)

    def _build_workflow_param_schemas(self) -> dict[str, str]:
        """Collect default-parameter summaries for all registered workflows."""
        schemas: dict[str, str] = {}
        for wf_name, wf in self.workflow_registry.items():
            input_model = getattr(wf, "input_model", None)
            if input_model is not None and issubclass(input_model, BaseModel):
                try:
                    schemas[wf_name] = self._extract_param_schema(input_model)
                except Exception:
                    pass
        return schemas

    def _build_plan(self, user_input: str, state: AgentState) -> Any:
        """Route and build an execution plan, mutating state in place.

        Routing priority:
        1. DeterministicRouter (keyword matching) — fast, no LLM call.
        2. LLMPlanner — handles complex / composite / ambiguous requests.
        """
        state.setdefault("_execution_log", [])

        # 1. Try deterministic routing first
        deterministic_plan = self.deterministic_router.route(user_input)
        if deterministic_plan is not None:
            state["_execution_plan"] = deterministic_plan.model_dump(mode="json")
            state["_routing_method"] = "deterministic"
            state["_execution_log"].append({
                "event": "routing_decision",
                "method": "deterministic",
                "target": deterministic_plan.steps[0].target,
                "description": deterministic_plan.steps[0].description,
                "timestamp": time.time(),
            })
            state["messages"] = state.get("messages", []) + [
                AIMessage(
                    content=f"Router decision: deterministic → {deterministic_plan.steps[0].target}"
                )
            ]
            return deterministic_plan

        # 2. Fallback to LLM-driven planning
        state["_routing_method"] = "llm"
        state["_execution_log"].append({
            "event": "routing_decision",
            "method": "llm",
            "timestamp": time.time(),
        })
        state["_available_capabilities"] = self._available_capabilities
        state["_available_workflows"] = self._available_workflows

        wf_schemas = self._build_workflow_param_schemas()
        state["_workflow_param_schemas"] = wf_schemas

        if hasattr(self.planner, "plan_with_state"):
            plan = self.planner.plan_with_state(user_input, state)
        else:
            from agent_core.planning.base import AgentContext
            ctx = AgentContext(
                session_id=state.get("session_id", ""),
                available_capabilities=self._available_capabilities,
                available_workflows=self._available_workflows,
                workflow_param_schemas=wf_schemas,
            )
            plan = self.planner.plan(user_input, ctx)

        state["_execution_plan"] = plan.model_dump(mode="json")

        state["messages"] = state.get("messages", []) + [
            AIMessage(content="Router decision: LLM-driven planning")
        ]
        return plan

    @staticmethod
    def _format_final_report(state: dict[str, Any]) -> str:
        """Build a human-readable final_report from execution results."""
        wf_result = state.get("workflow_result")
        if wf_result is not None and hasattr(wf_result, "success"):
            if not getattr(wf_result, "success", False):
                return f"Workflow failed: {getattr(wf_result, 'summary', 'unknown error')}"

            all_candidates = getattr(wf_result, "all_candidates", [])
            best = getattr(wf_result, "best_candidate", None)

            # Build a concise summary
            lines: list[str] = []
            lines.append(f"✓ 工作流执行成功，共生成 {len(all_candidates)} 个候选序列。")

            if best and hasattr(best, "sequence"):
                src = getattr(best, "source", "")
                scores = getattr(best, "scores", {})
                total = scores.get("total_score") if isinstance(scores, dict) else None
                lines.append(f"✓ 最佳候选: {src}，序列长度 {len(best.sequence)} nt" + (
                    f"，综合得分 {total:.3f}" if total is not None else ""
                ))

                # For full-length mRNA, show CDS info
                meta = best.metadata or {}
                cds = meta.get("cds_sequence", "")
                utr5 = meta.get("utr5_sequence", "")
                utr3 = meta.get("utr3_sequence", "")
                if cds:
                    lines.append(f"  - 5'UTR: {len(utr5)} nt | CDS: {len(cds)} nt | 3'UTR: {len(utr3)} nt")
                    mb = meta.get("metrics_bundle", {})
                    if mb.get("cds_cai") is not None:
                        lines.append(
                            f"  - CAI={mb['cds_cai']:.4f}, "
                            f"MFE={mb.get('cds_mfe', 'N/A')}, "
                            f"GC={mb.get('cds_gc', 'N/A')}"
                        )

            # Show top-3 candidates (brief)
            top_n = min(3, len(all_candidates))
            if top_n > 1:
                lines.append(f"\nTop {top_n} 候选序列概览:")
                for i, c in enumerate(all_candidates[:top_n], start=1):
                    meta = c.metadata or {}
                    mb = meta.get("metrics_bundle", {})
                    scores = c.scores or {}
                    total = scores.get("total_score")
                    parts = [f"  #{i} {c.source}"]
                    parts.append(f"总长度={len(c.sequence)} nt")
                    if meta.get("cds_sequence"):
                        parts.append(f"CDS={len(meta['cds_sequence'])} nt")
                    if mb.get("cds_cai") is not None:
                        parts.append(f"CAI={mb['cds_cai']:.4f}")
                    if total is not None:
                        parts.append(f"得分={total:.3f}")
                    lines.append(" | ".join(parts))

            # ── Critic 诊断历史 ──
            diagnosis_history = state.get("_diagnosis_history", [])
            retry_count = state.get("retry_count", 0)

            if diagnosis_history or retry_count > 0:
                lines.append("\n" + "─" * 40)
                lines.append("LLM Critic 诊断报告")
                lines.append("─" * 40)

                if retry_count > 0:
                    lines.append(f"重试次数: {retry_count}")

                for i, diag in enumerate(diagnosis_history, start=1):
                    lines.append(f"\n第 {i} 轮诊断:")
                    assessment = diag.get("overall_assessment", "N/A")
                    lines.append(f"  总体评估: {assessment}")

                    quality = diag.get("quality_score")
                    if quality is not None:
                        lines.append(f"  质量评分: {quality:.2f}/1.0")

                    issues = diag.get("issues", [])
                    if issues:
                        lines.append(f"  发现问题 ({len(issues)} 个):")
                        for issue in issues:
                            sev = issue.get("severity", "unknown")
                            desc = issue.get("description", "")
                            lines.append(f"    [{sev.upper()}] {desc}")

                    action = diag.get("action", "unknown")
                    overrides = diag.get("parameter_overrides", {})
                    if overrides:
                        lines.append(f"  建议操作: {action}")
                        lines.append(f"  参数调整:")
                        for k, v in overrides.items():
                            lines.append(f"    {k} → {v}")
                    elif action != "unknown":
                        lines.append(f"  建议操作: {action}")

                # 如果最后一轮有错误
                critic_error = state.get("_llm_critic_error")
                if critic_error:
                    lines.append(f"\n⚠ Critic 错误: {critic_error.get('type')}: {critic_error.get('message')}")

                lines.append("─" * 40)

            lines.append("\n详细结果已保存，请查看结果文件获取完整序列及所有指标。")
            return "\n".join(lines)

        # Fallback: report tool execution summary (very concise)
        tool_results = state.get("tool_results", {})
        if tool_results:
            tool_names = list(tool_results.keys())
            return f"已执行工具: {', '.join(tool_names)}。执行完成。"

        return "Execution completed but no structured result was produced."

    def run(
        self,
        user_input: str,
        *,
        session_id: str = "",
        state: Optional[AgentState] = None,
    ) -> AgentState:
        """Plan → Execute → Return updated state.

        This is the unified path; it does **not** require LangGraph.
        """
        token = _SESSION_ID_CTX.set(session_id)
        try:
            explicit_state = state is not None
            prepared = self._prepare_state(user_input, session_id, state if explicit_state else None)
            plan = self._build_plan(user_input, prepared)

            def _replan(s: dict[str, Any]) -> Any:
                return self.planner.plan_with_state(user_input, s)

            result_state = self.controller.execute(plan, prepared, replan_fn=_replan, persist_run=self.persist_run)
            result_state["final_report"] = self._format_final_report(result_state)

            if self.memory is not None and session_id and not explicit_state:
                self.memory.save(session_id, result_state)

            return result_state
        finally:
            _SESSION_ID_CTX.reset(token)

    def stream(
        self,
        user_input: str,
        *,
        session_id: str = "",
    ) -> Iterator[dict[str, Any]]:
        """Yield step-by-step events from the execution pipeline.

        Events are emitted as ``{node_name: state_dict}`` dicts.
        This shape is compatible with presentation layers.
        """
        import queue
        import threading

        token = _SESSION_ID_CTX.set(session_id)
        try:
            state = self._prepare_state(user_input, session_id, None)
            plan = self._build_plan(user_input, state)
            yield {"router": dict(state)}

            # Expose LLM planning details to the presentation layer
            yield {"plan": {
                "reasoning": getattr(plan, "reasoning", ""),
                "steps": [
                    {
                        "step_id": s.step_id,
                        "type": s.type,
                        "target": s.target,
                        "description": s.description,
                    }
                    for s in plan.steps
                ],
                "max_retries": getattr(plan, "max_retries", 2),
            }}

            def _replan(s: dict[str, Any]) -> Any:
                return self.planner.plan_with_state(user_input, s)

            # Use a queue + background thread so that long-running workflow
            # steps do not block the generator.
            progress_q: queue.Queue[dict[str, Any]] = queue.Queue()
            result_container: dict[str, Any] = {}

            def _progress_callback(entry: dict[str, Any]) -> None:
                progress_q.put(entry)

            def _execute_in_thread() -> None:
                try:
                    result = self.controller.execute(
                        plan, state, replan_fn=_replan, progress_callback=_progress_callback, persist_run=self.persist_run
                    )
                    result["final_report"] = self._format_final_report(result)
                    result_container["state"] = result
                    progress_q.put({"__done__": True, "success": True})
                except Exception as exc:
                    progress_q.put({"__done__": True, "success": False, "error": str(exc)})

            thread = threading.Thread(target=_execute_in_thread, daemon=True)
            thread.start()

            while True:
                item = progress_q.get()
                if item.get("__done__"):
                    if not item.get("success", True):
                        raise RuntimeError(
                            f"执行失败: {item.get('error', 'Unknown error')}"
                        )
                    break
                yield {"progress": item}

            thread.join()
            result_state = result_container["state"]
            yield {"tool_execution": dict(result_state)}

            if self.memory is not None and session_id:
                self.memory.save(session_id, result_state)
            yield {"runner": dict(result_state)}
        finally:
            _SESSION_ID_CTX.reset(token)
