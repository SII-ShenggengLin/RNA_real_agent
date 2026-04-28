"""CRISPR specialist: deterministic CRISOT / CRGPT dispatch."""

from __future__ import annotations

from typing import Any

from agent_core.nodes import (
    _needs_sgrna_handle_design,
    _needs_sgrna_handle_score,
    _resolve_crisot_request,
    _resolve_sgrna_design_request,
)
from agent_core.planning.base import ExecutionPlan, PlanStep


class CrisprSpecialist:
    """Deterministic CRISPR tool selection (refactored from ``crispr_specialist_node``)."""

    def plan(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        lowered = raw_text.lower()

        if _needs_sgrna_handle_score(lowered):
            from agent_core.nodes import _extract_sgrna_seed_sequence
            seq = _extract_sgrna_seed_sequence(raw_text)
            if seq:
                tool_args = {"sequence": seq}
                state_updates = {"sgrna_design_score_sequence": seq}
            else:
                from agent_core.file_manager import read_sequence
                from agent_core.nodes import _extract_path_with_suffixes
                filepath = _extract_path_with_suffixes(raw_text, ("fasta", "fa", "txt", "seq"))
                if filepath:
                    tool_args = {"sequence": read_sequence(filepath)}
                    state_updates = {"current_filepath": filepath}
                else:
                    default_wildtype = "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG"
                    tool_args = {"sequence": default_wildtype}
                    state_updates = {"sgrna_design_score_sequence": default_wildtype}
            for k, v in state_updates.items():
                state[k] = v
            return ExecutionPlan(steps=[
                PlanStep(
                    step_id="sgrna_score",
                    type="capability",
                    target="score_sgrna_handle_with_crgpt",
                    input_binding=tool_args,
                    description="CRGPT sgRNA handle scoring",
                )
            ])

        if _needs_sgrna_handle_design(lowered):
            tool_args, state_updates = _resolve_sgrna_design_request(raw_text)
            extra_files = state_updates.pop("workspace_files", [])
            state["workspace_files"] = state.get("workspace_files", []) + extra_files
            for k, v in state_updates.items():
                state[k] = v
            return ExecutionPlan(steps=[
                PlanStep(
                    step_id="sgrna_design",
                    type="capability",
                    target="design_sgrna_handle_with_crgpt",
                    input_binding=tool_args,
                    description="CRGPT sgRNA handle design",
                )
            ])

        # Default: CRISOT request
        tool_name, tool_args, state_updates = _resolve_crisot_request(raw_text)
        extra_files = state_updates.pop("workspace_files", [])
        state["workspace_files"] = state.get("workspace_files", []) + extra_files
        for k, v in state_updates.items():
            state[k] = v
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="crisot",
                type="capability",
                target=tool_name,
                input_binding=tool_args,
                description="CRISOT CRISPR analysis",
            )
        ])
