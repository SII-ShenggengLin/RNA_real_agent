"""siRNA specialist: deterministic Evitar / ViennaRNA duplex dispatch."""

from __future__ import annotations

from typing import Any

from agent_core.file_manager import save_sequence
from agent_core.planning.rule_based.parsers.common import (
    _build_evitar_tool_args,
    _ensure_duplex_fasta_workspace_path,
    _needs_evitar_mode,
    _needs_sirna_duplex_vienna,
    _resolve_evitar_input_filepath,
)
from agent_core.planning.base import ExecutionPlan, PlanStep


class SirnaSpecialist:
    """Deterministic siRNA tool selection (refactored from ``sirna_specialist_node``)."""

    def plan(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        user_text = raw_text.lower()
        filepath = state.get("current_filepath")

        if _needs_evitar_mode(user_text):
            if not filepath:
                filepath = _resolve_evitar_input_filepath(raw_text, current_filepath=None)
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            if filepath != state.get("current_filepath"):
                state["current_filepath"] = filepath
            evitar_args = _build_evitar_tool_args(filepath, raw_text)
            return ExecutionPlan(steps=[
                PlanStep(
                    step_id="evitar",
                    type="capability",
                    target="design_sirna_with_evitar",
                    input_binding=evitar_args,
                    description="Evitar siRNA/Cas13 design",
                )
            ])

        if _needs_sirna_duplex_vienna(user_text):
            duplex_fp = _ensure_duplex_fasta_workspace_path(raw_text, filepath)
            state["current_filepath"] = duplex_fp
            if duplex_fp.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [duplex_fp]
            return ExecutionPlan(steps=[
                PlanStep(
                    step_id="duplex",
                    type="capability",
                    target="compute_sirna_duplex_binding_vienna",
                    input_binding={"filepath": duplex_fp},
                    description="ViennaRNA sense/antisense duplex (cofold) energy",
                )
            ])

        # Unsupported siRNA request
        return ExecutionPlan(steps=[])
