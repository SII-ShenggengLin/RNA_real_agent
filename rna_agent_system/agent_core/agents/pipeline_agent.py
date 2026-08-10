"""PipelineAgent: deterministic orchestration of PipelinePlan nodes."""

from __future__ import annotations

import logging
from typing import Any

from agent_core.agents.base import AgentResult, BaseAgent
from agent_core.agents.quality_agent import QualityAgent, QualityReport
from agent_core.agents.synthesis_agent import SynthesisAgent
from agent_core.pipeline.binding_resolver import BindingResolver

_LOGGER = logging.getLogger(__name__)


class PipelineAgent(BaseAgent):
    """Deterministic pipeline scheduler.

    PipelineAgent does NOT call LLMs. It resolves node bindings, executes nodes
    via SpecialistAgents, collects QualityReports, handles critical failures,
    and delegates final synthesis to SynthesisAgent.
    """

    def __init__(
        self,
        specialist_registry: dict[str, Any],
        quality_agent: QualityAgent,
        synthesis_agent: SynthesisAgent,
    ) -> None:
        self.specialist_registry = specialist_registry
        self.quality_agent = quality_agent
        self.synthesis_agent = synthesis_agent

    def execute(
        self,
        plan: "PipelinePlan",
        state: dict[str, Any] | None = None,
        *,
        progress_callback: Any | None = None,
    ) -> "PipelineResult":
        """Execute a PipelinePlan and return a PipelineResult."""
        from agent_core.pipeline.models import PipelineResult

        if state is None:
            state = {}
        order = plan.topological_order()
        node_results: dict[str, AgentResult] = {}
        quality_reports: dict[str, QualityReport] = {}
        errors: list[str] = []

        alias_to_node_id = {
            n.output_alias: n.node_id
            for n in plan.nodes
            if n.output_alias and n.output_alias != n.node_id
        }

        for node_id in order:
            node = plan.get_node(node_id)
            _LOGGER.info("pipeline executing node=%s workflow=%s", node_id, node.workflow)

            specialist = self.specialist_registry.get(node.workflow)
            if specialist is None:
                error = f"Node {node_id}: no SpecialistAgent registered for workflow {node.workflow}"
                errors.append(error)
                if node.critical:
                    break
                continue

            resolved = self._resolve_inputs(node, node_results, alias_to_node_id)
            node_state = dict(state)
            node_state["_user_explicit_params"] = sorted(node.static_params.keys())

            try:
                result = specialist.run(
                    node_id,
                    resolved,
                    self.quality_agent,
                    state=node_state,
                    progress_callback=progress_callback,
                )
            except Exception as exc:
                error = f"Node {node_id}: execution failed: {type(exc).__name__}: {exc}"
                errors.append(error)
                result = AgentResult(
                    node_id=node_id,
                    workflow=node.workflow,
                    success=False,
                    errors=[error],
                )

            node_results[node_id] = result

            # Merge quality-related state produced by SpecialistAgent/QualityAgent
            # back into the shared pipeline state so that CLI/API reports can
            # render diagnosis history and retry counts.
            self._merge_quality_state(state, node_state)

            quality_report = result.metadata.get("quality_report")
            if quality_report is None:
                errors.append(
                    f"Node {node_id}: SpecialistAgent did not return quality_report"
                )
            else:
                quality_reports[node_id] = quality_report

            if not result.success:
                errors.extend(result.errors)
                if node.critical:
                    break

        success = (
            all(r.success for r in node_results.values())
            and len(node_results) == len(plan.nodes)
            and not errors
        )

        final_report = self.synthesis_agent.synthesize(plan, node_results, quality_reports)

        return PipelineResult(
            plan_id=plan.plan_id,
            success=success,
            node_results=node_results,
            quality_reports=quality_reports,
            final_report=final_report,
            errors=errors,
        )

    @staticmethod
    def _merge_quality_state(
        state: dict[str, Any],
        node_state: dict[str, Any],
    ) -> None:
        """Merge quality-related state from a node execution back into ``state``.

        ``QualityAgent`` writes diagnosis history, last diagnosis, parameter
        overrides, and error state into the per-node state.  This helper ensures
        those values survive in the shared pipeline state for report generation.
        """
        node_history = node_state.get("_diagnosis_history", [])
        if node_history:
            state.setdefault("_diagnosis_history", []).extend(node_history)
        for key in (
            "_last_diagnosis",
            "_parameter_overrides",
            "_last_workflow_params",
            "_quality_review_error",
        ):
            if key in node_state:
                state[key] = node_state[key]

    def _resolve_inputs(
        self,
        node: Any,
        node_results: dict[str, AgentResult],
        alias_to_node_id: dict[str, str],
    ) -> dict[str, Any]:
        """Merge static params with resolved input bindings."""
        params = dict(node.static_params)
        if node.input_bindings:
            resolver = BindingResolver(node_results, alias_to_node_id)
            bound = resolver.resolve_params(node.input_bindings)
            params.update(bound)
        return params
