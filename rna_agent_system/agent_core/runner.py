"""Layer 6 — AgentRunner: unified form-driven entry point."""

from __future__ import annotations

import contextvars
import copy
import logging
import queue
import threading
from typing import Any, Iterator, Optional

from langchain_core.messages import HumanMessage

from agent_core.agents.pipeline_agent import PipelineAgent
from agent_core.agents.quality_agent import QualityAgent
from agent_core.agents.specialist_agent import SpecialistAgent
from agent_core.agents.synthesis_agent import SynthesisAgent
from agent_core.capabilities.base import build_default_capability_registry
from agent_core.file_manager import _SESSION_ID_CTX
from agent_core.pipeline.models import PipelinePlan, PipelineResult
from agent_core.quality_profiles import QUALITY_PROFILES
from agent_core.session_memory import SessionMemory
from agent_core.state import AgentState, default_state
from agent_core.tool_executor import ToolExecutor
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

_LOGGER = logging.getLogger(__name__)


class AgentRunner:
    """Unified façade used by FastAPI and CLI.

    Parameters
    ----------
    executor:
        ``ToolExecutor`` used to build the ``CapabilityRegistry``.
    session_memory:
        Optional ``SessionMemory`` for multi-turn persistence.
    """

    def __init__(
        self,
        executor: ToolExecutor,
        *,
        session_memory: Optional[SessionMemory] = None,
        quality_review_enabled: bool = True,
        quality_auto_retry: bool = False,
        persist_run: bool = False,
    ):
        self.executor = executor
        self.quality_review_enabled = quality_review_enabled
        self.quality_auto_retry = quality_auto_retry
        self.persist_run = persist_run
        self.capability_registry = build_default_capability_registry(executor)
        self.workflow_registry: dict[str, Any] = {
            "aso_target_screening": AsoTargetScreeningWorkflow(self.capability_registry),
            "mrna_cds_design": MrnaCdsDesignWorkflow(self.capability_registry),
            "mrna_sequence_scoring": MrnaSequenceScoringWorkflow(self.capability_registry),
            "full_length_mrna_design": FullLengthMrnaDesignWorkflow(self.capability_registry),
            "rna_aptamer_design": RnaAptamerDesignWorkflow(self.capability_registry),
            "rna_secondary_structure_design": RnaSecondaryStructureDesignWorkflow(self.capability_registry),
            "rna_small_molecule_interaction": RnaSmallMoleculeInteractionWorkflow(self.capability_registry),
            "rna_tertiary_structure_design": RnaTertiaryStructureDesignWorkflow(self.capability_registry),
            "sgrna_design": SgRnaDesignWorkflow(self.capability_registry),
            "sirna_design": SirnaDesignWorkflow(self.capability_registry),
            "ires_prediction": IresPredictionWorkflow(self.capability_registry),
        }
        # Enable automatic microservice startup for all runner-managed workflows.
        for wf in self.workflow_registry.values():
            if hasattr(wf, "auto_start_services"):
                wf.auto_start_services = True
        # Platform CapGate: audit every tool call and gate managed oracle tools
        # against the packaged SelfModel (RNADA_CAPGATE=off|advisory|enforce).
        from agent_core.calibrated.runtime import runtime_from_env

        self.calibrated_runtime = runtime_from_env()
        self.quality_agent = QualityAgent()
        self.synthesis_agent = SynthesisAgent()
        self.specialist_registry = self._build_specialist_registry()
        self.pipeline_agent = PipelineAgent(
            specialist_registry=self.specialist_registry,
            quality_agent=self.quality_agent,
            synthesis_agent=self.synthesis_agent,
        )
        self.memory = session_memory

    def _build_specialist_registry(self) -> dict[str, SpecialistAgent]:
        """Create a SpecialistAgent for each workflow that has a QualityProfile."""
        registry: dict[str, SpecialistAgent] = {}
        for wf_name, workflow in self.workflow_registry.items():
            profile = QUALITY_PROFILES.get(wf_name)
            if profile is None:
                continue
            specialist = SpecialistAgent(workflow, profile)
            registry[wf_name] = specialist
        return registry

    def run_pipeline(
        self,
        plan: PipelinePlan,
        state: Optional[dict[str, Any]] = None,
    ) -> PipelineResult:
        """Execute a PipelinePlan through the multi-agent pipeline engine.

        When *state* carries a ``session_id``, tool-level artifacts are scoped
        to ``workspace/sessions/<session_id>/`` — the same no-global-root-leak
        contract ``run_form``/``stream_form`` already uphold. Callers that pass
        no session keep the legacy global-workspace behaviour.
        """
        session_id = ""
        if state is not None:
            session_id = str(state.get("session_id", "") or "")
        token = _SESSION_ID_CTX.set(session_id)
        try:
            return self.pipeline_agent.execute(plan, state=state)
        finally:
            _SESSION_ID_CTX.reset(token)

    def _prepare_state(
        self,
        user_input: str,
        session_id: str,
        explicit_state: Optional[AgentState],
    ) -> AgentState:
        """Load or create state, inject user message and session_id, and return it."""
        if explicit_state is not None:
            state = explicit_state
        else:
            if self.memory is not None:
                state = self.memory.load(session_id)
            else:
                state = default_state("")
        state["user_text"] = user_input
        state["session_id"] = session_id
        state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]
        state["_quality_review_enabled"] = self.quality_review_enabled
        state["_quality_auto_retry"] = self.quality_auto_retry
        return state

    def _prepare_state_form(
        self,
        session_id: str,
        explicit_workflow: str,
        form_params: dict[str, Any],
        explicit_state: Optional[AgentState] = None,
    ) -> AgentState:
        """Load or create state for a form-driven execution.

        Before overwriting any stale workflow result left in session memory, copy
        it to ``_previous_workflow_result`` and append it to
        ``_workflow_result_history``. This preserves cross-turn context for the
        QualityAgent and CLI report generator.
        """
        if explicit_state is not None:
            state = explicit_state
        else:
            if self.memory is not None:
                state = self.memory.load(session_id)
            else:
                state = default_state("")
        state["session_id"] = session_id
        state["_form_params"] = form_params
        state["_user_explicit_params"] = sorted(form_params.keys())
        state["_quality_review_enabled"] = self.quality_review_enabled
        state["_quality_auto_retry"] = self.quality_auto_retry

        # Cross-turn quality context: snapshot the previous turn's result before
        # it is replaced by the current run.
        previous_wf = state.get("workflow_result")
        if previous_wf is not None:
            state["_previous_workflow_result"] = copy.deepcopy(previous_wf)
            history = state.get("_workflow_result_history") or []
            history = list(history)
            history.append(copy.deepcopy(previous_wf))
            state["_workflow_result_history"] = history
            state.pop("workflow_result", None)

        state.pop("_diagnosis_history", None)
        return state

    def _sanitize_form_params(
        self, workflow_name: str, form_params: dict[str, Any]
    ) -> dict[str, Any]:
        """Remove invented parameters not present in the workflow input model."""
        wf = self.workflow_registry.get(workflow_name)
        if wf is None or not hasattr(wf, "input_model") or wf.input_model is None:
            return dict(form_params)
        valid_keys = set(wf.input_model.model_fields.keys())
        return {k: v for k, v in form_params.items() if k in valid_keys}

    def _validate_required_params_for_workflow(
        self, workflow_name: str, params: dict[str, Any]
    ) -> None:
        """Raise ValueError if any required parameter is missing."""
        wf = self.workflow_registry.get(workflow_name)
        if wf is None or not hasattr(wf, "input_model") or wf.input_model is None:
            return
        missing: list[str] = []
        for name, field_info in wf.input_model.model_fields.items():
            if field_info.is_required():
                value = params.get(name)
                if value is None or value == "":
                    missing.append(name)
        if missing:
            raise ValueError(
                f"Missing required parameters for {workflow_name}: {', '.join(missing)}"
            )

    @staticmethod
    def _format_final_report(state: dict[str, Any]) -> str:
        """Build a human-readable final_report from execution results."""
        wf_result = state.get("workflow_result")
        if wf_result is not None and hasattr(wf_result, "success"):
            if not getattr(wf_result, "success", False):
                return f"Workflow failed: {getattr(wf_result, 'summary', 'unknown error')}"

            all_candidates = getattr(wf_result, "all_candidates", [])
            best = getattr(wf_result, "best_candidate", None)

            lines: list[str] = []
            lines.append(f"✓ 工作流执行成功，共生成 {len(all_candidates)} 个候选序列。")

            if best and hasattr(best, "sequence"):
                src = getattr(best, "source", "")
                scores = getattr(best, "scores", {})
                total = scores.get("total_score") if isinstance(scores, dict) else None
                lines.append(f"✓ 最佳候选: {src}，序列长度 {len(best.sequence)} nt" + (
                    f"，综合得分 {total:.3f}" if total is not None else ""
                ))

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

            diagnosis_history = state.get("_diagnosis_history", [])
            retry_count = state.get("retry_count", 0)

            if diagnosis_history or retry_count > 0:
                lines.append("\n" + "─" * 40)
                lines.append("QualityAgent 诊断报告")
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

                quality_error = state.get("_quality_review_error")
                if quality_error:
                    lines.append(f"\n⚠ QualityAgent 错误: {quality_error.get('type')}: {quality_error.get('message')}")

                lines.append("─" * 40)

            lines.append("\n详细结果已保存，请查看结果文件获取完整序列及所有指标。")
            return "\n".join(lines)

        # A pipeline node that crashed without producing a WorkflowResult
        # (node_result.workflow_result is None) used to fall through to the
        # generic "Execution completed" text — report the recorded pipeline
        # errors instead so callers see the failure.
        pipeline_payload = state.get("pipeline_result") or {}
        if pipeline_payload and not pipeline_payload.get("success", True):
            errors = pipeline_payload.get("errors") or ["pipeline failed without recorded errors"]
            return "Workflow failed: " + "; ".join(str(e) for e in errors)

        tool_results = state.get("tool_results", {})
        if tool_results:
            tool_names = list(tool_results.keys())
            return f"已执行工具: {', '.join(tool_names)}。执行完成。"

        return "Execution completed but no structured result was produced."

    def run_form(
        self,
        form_params: dict[str, Any],
        *,
        session_id: str,
        explicit_workflow: str,
        user_text: str = "",
        state: Optional[AgentState] = None,
    ) -> AgentState:
        """Execute a workflow from structured form parameters."""
        token = _SESSION_ID_CTX.set(session_id)
        try:
            explicit_state = state is not None
            prepared = self._prepare_state_form(
                session_id,
                explicit_workflow,
                form_params,
                state if explicit_state else None,
            )
            if user_text:
                prepared["user_text"] = user_text
                prepared["messages"] = prepared.get("messages", []) + [HumanMessage(content=user_text)]

            sanitized_params = self._sanitize_form_params(explicit_workflow, form_params)
            self._validate_required_params_for_workflow(explicit_workflow, sanitized_params)

            plan = PipelinePlan.single(
                explicit_workflow,
                sanitized_params,
                plan_id=f"form_{session_id}_{explicit_workflow}",
                output_alias="result",
            )
            prepared["_execution_plan"] = plan.model_dump(mode="json")
            prepared["_routing_method"] = "explicit"
            prepared["_user_explicit_params"] = sorted(form_params.keys())

            pipeline_result = self.run_pipeline(plan, state=prepared)

            # Write results back to state, preserving the existing AgentState contract.
            node_result = pipeline_result.node_results.get("n1")
            if node_result is not None:
                prepared["workflow_result"] = node_result.workflow_result
                prepared["retry_count"] = node_result.metadata.get("retry_count", 0)
                prepared["max_retries"] = node_result.metadata.get("max_retries", 2)

            prepared["pipeline_result"] = pipeline_result.model_dump(mode="json")
            prepared["final_report"] = self._format_final_report(prepared)

            # Persist form params for multi-turn prefilling.
            prepared["_last_form_params"] = dict(form_params)
            by_workflow = prepared.get("_last_form_params_by_workflow", {})
            by_workflow[explicit_workflow] = dict(form_params)
            prepared["_last_form_params_by_workflow"] = by_workflow

            if self.memory is not None and session_id and not explicit_state:
                self.memory.save(session_id, prepared)

            return prepared
        finally:
            _SESSION_ID_CTX.reset(token)

    def stream_form(
        self,
        form_params: dict[str, Any],
        *,
        session_id: str,
        explicit_workflow: str,
        user_text: str = "",
    ) -> Iterator[dict[str, Any]]:
        """Yield step-by-step events from a form-driven execution."""
        token = _SESSION_ID_CTX.set(session_id)
        try:
            state = self._prepare_state_form(session_id, explicit_workflow, form_params)
            if user_text:
                state["user_text"] = user_text
                state["messages"] = state.get("messages", []) + [HumanMessage(content=user_text)]

            sanitized_params = self._sanitize_form_params(explicit_workflow, form_params)
            self._validate_required_params_for_workflow(explicit_workflow, sanitized_params)

            plan = PipelinePlan.single(
                explicit_workflow,
                sanitized_params,
                plan_id=f"form_{session_id}_{explicit_workflow}",
                output_alias="result",
            )
            state["_execution_plan"] = plan.model_dump(mode="json")
            state["_routing_method"] = "explicit"
            state["_user_explicit_params"] = sorted(form_params.keys())
            yield {"router": dict(state)}

            yield {"plan": {
                "reasoning": "",
                "steps": [
                    {
                        "step_id": "n1",
                        "type": "workflow",
                        "target": n.workflow,
                        "description": f"Execute {n.workflow}",
                    }
                    for n in plan.nodes
                ],
                "max_retries": 2,
            }}

            progress_q: queue.Queue[dict[str, Any]] = queue.Queue()
            result_container: dict[str, Any] = {}

            def _progress_callback(entry: dict[str, Any]) -> None:
                progress_q.put(entry)

            def _execute_in_thread() -> None:
                try:
                    pipeline_result = self.pipeline_agent.execute(
                        plan,
                        state,
                        progress_callback=_progress_callback,
                    )
                    node_result = pipeline_result.node_results.get("n1")
                    if node_result is not None:
                        state["workflow_result"] = node_result.workflow_result
                        state["retry_count"] = node_result.metadata.get("retry_count", 0)
                        state["max_retries"] = node_result.metadata.get("max_retries", 2)
                    state["pipeline_result"] = pipeline_result.model_dump(mode="json")
                    state["final_report"] = self._format_final_report(state)
                    state["_last_form_params"] = dict(form_params)
                    by_workflow = state.get("_last_form_params_by_workflow", {})
                    by_workflow[explicit_workflow] = dict(form_params)
                    state["_last_form_params_by_workflow"] = by_workflow
                    result_container["state"] = state
                    done_error = None
                    if not pipeline_result.success:
                        # DIAGNOSIS NOTE (2026-07 experiment incident): when the
                        # pipeline fails without entries in pipeline_result.errors
                        # (e.g. a service hiccup mid-evaluation), the generic
                        # "pipeline failed without recorded errors" message hides
                        # the root cause. To diagnose, read the session's
                        # driver/console log and the workflow's own logger output —
                        # the real error is almost always there, not here.
                        done_error = "; ".join(pipeline_result.errors) or "pipeline failed without recorded errors"
                    progress_q.put({"__done__": True, "success": pipeline_result.success, "error": done_error})
                except Exception as exc:
                    progress_q.put({"__done__": True, "success": False, "error": str(exc)})

            # Run the pipeline with a copy of the current context so
            # context-propagated state (session id, CapGate task type) stays
            # visible inside the worker thread.
            thread = threading.Thread(
                target=contextvars.copy_context().run, args=(_execute_in_thread,), daemon=True
            )
            thread.start()

            while True:
                item = progress_q.get()
                if item.get("__done__"):
                    if not item.get("success", True):
                        raise RuntimeError(f"执行失败: {item.get('error', 'Unknown error')}")
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

