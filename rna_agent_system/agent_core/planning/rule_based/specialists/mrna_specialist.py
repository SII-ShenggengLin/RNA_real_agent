"""mRNA specialist: decide which mRNA tool(s) to call and build an ``ExecutionPlan``."""

from __future__ import annotations

from typing import Any

from agent_core.file_manager import save_sequence
from agent_core.nodes import (
    _build_codonw_tool_args,
    _build_linearfold_tool_args,
    _build_ribodiffusion_tool_args,
    _extract_gernabind_overrides,
    _extract_odesign_request,
    _extract_protein_sequence,
    _extract_rnasmol_overrides,
    _extract_structure_design_inputs,
    _needs_3utr_design,
    _needs_5utr_design,
    _needs_blast_search,
    _needs_codonw_standalone,
    _needs_dot_bracket_unpaired_fraction_metric,
    _needs_gernabind_scoring,
    _needs_inverse_fold_vienna,
    _needs_iresfinder_prediction,
    _needs_lineardesign,
    _needs_linearfold,
    _needs_odesign_mode,
    _needs_rna_gc_content_metric,
    _needs_rna_plfold_local_profile,
    _needs_ribodiffusion_design,
    _needs_rnarl_design,
    _needs_rnasmol_scoring,
    _needs_rnastop_prediction,
    _needs_secondary_structure,
    _needs_structure_to_sequence_design,
    _needs_tertiary_structure,
    _resolve_protein_to_cds_tool,
    _resolve_rna_ligand_inputs,
    _resolve_sequence_input,
    _resolve_utr_tool,
    _update_state_with_ligand_inputs,
)
from agent_core.planning.base import ExecutionPlan, PlanStep


class MrnaSpecialist:
    """Deterministic mRNA tool selection (refactored from ``mrna_specialist_node``).

    The specialist inspects the user request, prepares workspace files if
    necessary, and emits an ``ExecutionPlan`` of capability / workflow steps.
    """

    def plan(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        """Return an execution plan for the mRNA domain.

        Side effects: may write workspace files and update *state* fields
        (``current_filepath``, ``workspace_files``, etc.) so that the
        controller can execute the plan without re-parsing input.
        """
        user_text = raw_text.lower()
        steps: list[PlanStep] = []

        # ── ODesign ──
        if _needs_odesign_mode(user_text):
            return self._plan_odesign(raw_text, state)

        # ── GerNA-Bind ──
        if _needs_gernabind_scoring(user_text):
            return self._plan_gernabind(raw_text, state)

        # ── RNAsmol ──
        if _needs_rnasmol_scoring(user_text):
            return self._plan_rnasmol(raw_text, state)

        # ── IRESfinder ──
        if _needs_iresfinder_prediction(user_text):
            return self._plan_iresfinder(raw_text, state)

        # ── Inverse fold ──
        if _needs_inverse_fold_vienna(user_text):
            return self._plan_inverse_fold(raw_text, state)

        # ── RNASTOP ──
        if _needs_rnastop_prediction(user_text):
            return self._plan_rnastop(raw_text, state)

        # ── codonw-slim standalone ──
        if _needs_codonw_standalone(raw_text):
            return self._plan_codonw(raw_text, state)

        # ── GC content ──
        if _needs_rna_gc_content_metric(user_text):
            return self._plan_gc_content(raw_text, state)

        # ── Dot-bracket unpaired fraction ──
        if _needs_dot_bracket_unpaired_fraction_metric(user_text):
            return self._plan_unpaired_fraction(raw_text, state)

        # ── BLAST ──
        if _needs_blast_search(user_text):
            return self._plan_blast(raw_text, state)

        # ── RiboDiffusion ──
        if _needs_ribodiffusion_design(user_text):
            return self._plan_ribodiffusion(raw_text, state)

        # ── Structure-to-sequence (RhoDesign) ──
        if _needs_structure_to_sequence_design(user_text):
            return self._plan_structure_to_sequence(raw_text, state)

        # ── UTR design ──
        if _needs_5utr_design(user_text) or _needs_3utr_design(user_text):
            return self._plan_utr(raw_text, state)

        # ── Protein → CDS design (golden path) ──
        design_mode = any(
            k in user_text
            for k in [
                "design",
                "设计",
                "gemorna",
                "rnarl",
                "lineardesign",
                "linear design",
                "protein",
                "cds",
                "utr",
                "生成",
            ]
        )
        if design_mode:
            return self._plan_protein_to_cds(raw_text, state)

        # ── Default: fold (+ optional codonw + tertiary) ──
        return self._plan_default(raw_text, state)

    # ──────────────────────────────────────────────────────────────────────────
    # Sub-planners (one per tool / family)
    # ──────────────────────────────────────────────────────────────────────────

    def _plan_odesign(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        tool_args, state_updates = _extract_odesign_request(raw_text)
        extra_files = state_updates.pop("workspace_files", [])
        state["workspace_files"] = state.get("workspace_files", []) + extra_files
        for k, v in state_updates.items():
            state[k] = v
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="odesign",
                type="capability",
                target="run_odesign_inference",
                input_binding=tool_args,
                description="ODesign inference",
            )
        ])

    def _plan_gernabind(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        filepath, smiles, created = _resolve_rna_ligand_inputs(raw_text)
        overrides = _extract_gernabind_overrides(raw_text)
        _update_state_with_ligand_inputs(state, filepath, smiles, created)
        tool_args = {"filepath": filepath, "smiles": smiles, **overrides}
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="gernabind",
                type="capability",
                target="score_rna_ligand_binding_with_gernabind",
                input_binding=tool_args,
                description="GerNA-Bind RNA-ligand scoring",
            )
        ])

    def _plan_rnasmol(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        filepath, smiles, created = _resolve_rna_ligand_inputs(raw_text)
        overrides = _extract_rnasmol_overrides(raw_text)
        _update_state_with_ligand_inputs(state, filepath, smiles, created)
        tool_args = {"filepath": filepath, "smiles": smiles, **overrides}
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="rnasmol",
                type="capability",
                target="score_rna_ligand_binding_with_rnasmol",
                input_binding=tool_args,
                description="RNAsmol RNA-ligand scoring",
            )
        ])

    def _plan_iresfinder(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        from agent_core.nodes import _build_iresfinder_tool_args
        filepath, created = _resolve_sequence_input(raw_text)
        state["current_filepath"] = filepath
        if created or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="iresfinder",
                type="capability",
                target="predict_putative_ires_with_iresfinder",
                input_binding=_build_iresfinder_tool_args(filepath, raw_text),
                description="IRESfinder putative IRES scoring",
            )
        ])

    def _plan_inverse_fold(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        from agent_core.nodes import _ensure_inverse_fold_structure_file
        import re
        inv_fp = _ensure_inverse_fold_structure_file(raw_text, state.get("current_filepath"))
        state["current_filepath"] = inv_fp
        if inv_fp.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [inv_fp]
        rep_m = re.search(r"repeats?\s*[:=]\s*(\d+)", raw_text, flags=re.IGNORECASE)
        repeats = int(rep_m.group(1)) if rep_m else 1
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="inverse_fold",
                type="capability",
                target="inverse_fold_rna_secondary_structure_vienna",
                input_binding={"filepath": inv_fp, "repeats": repeats},
                description="ViennaRNA RNAinverse secondary-structure inverse fold",
            )
        ])

    def _plan_rnastop(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        filepath, created = _resolve_sequence_input(raw_text)
        state["current_filepath"] = filepath
        if created or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="rnastop",
                type="capability",
                target="predict_mrna_stability_with_rnastop",
                input_binding={"filepath": filepath},
                description="RNASTOP stability prediction",
            )
        ])

    def _plan_codonw(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        filepath, created = _resolve_sequence_input(raw_text)
        state["current_filepath"] = filepath
        if created or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="codonw",
                type="capability",
                target="analyze_cds_codon_metrics_with_codonw_slim",
                input_binding=_build_codonw_tool_args(filepath, raw_text),
                description="codonw-slim CDS codon metrics",
            )
        ])

    def _plan_gc_content(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        filepath, created = _resolve_sequence_input(raw_text)
        state["current_filepath"] = filepath
        if created or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="gc",
                type="capability",
                target="compute_rna_sequence_gc_content",
                input_binding={"filepath": filepath},
                description="RNA sequence GC content",
            )
        ])

    def _plan_unpaired_fraction(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        from agent_core.nodes import _resolve_dot_bracket_structure_filepath
        ss_fp, created = _resolve_dot_bracket_structure_filepath(raw_text)
        state["current_filepath"] = ss_fp
        if created or ss_fp.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [ss_fp]
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="unpaired",
                type="capability",
                target="compute_dot_bracket_unpaired_fraction",
                input_binding={"filepath": ss_fp},
                description="Dot-bracket unpaired fraction",
            )
        ])

    def _plan_blast(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        from agent_core.nodes import _build_blast_tool_args
        filepath, created = _resolve_sequence_input(raw_text)
        state["current_filepath"] = filepath
        if created or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        blast_args = _build_blast_tool_args(filepath, raw_text)
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="blast",
                type="capability",
                target="run_blastn_similarity_search",
                input_binding=blast_args,
                description="NCBI blastn similarity search",
            )
        ])

    def _plan_ribodiffusion(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        rb_args = _build_ribodiffusion_tool_args(raw_text)
        state["design_input_pdb_filepath"] = rb_args["pdb_filepath"]
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="ribodiffusion",
                type="capability",
                target="design_rna_inverse_fold_with_ribodiffusion",
                input_binding=rb_args,
                description="RiboDiffusion diffusion inverse folding",
            )
        ])

    def _plan_structure_to_sequence(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        pdb_path, ss_path = _extract_structure_design_inputs(raw_text)
        state["design_input_pdb_filepath"] = pdb_path
        if ss_path:
            state["design_input_secondary_structure_filepath"] = ss_path
        tool_args: dict[str, Any] = {"pdb_filepath": pdb_path}
        if ss_path:
            tool_args["secondary_structure_filepath"] = ss_path
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="rhodesign",
                type="capability",
                target="design_rna_sequence_with_rhodesign",
                input_binding=tool_args,
                description="RhoDesign structure-to-sequence design",
            )
        ])

    def _plan_utr(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        from agent_core.nodes import _extract_utr_length
        tool_name, tool_args = _resolve_utr_tool(raw_text)
        tool_args["utr_length"] = _extract_utr_length(raw_text)
        return ExecutionPlan(steps=[
            PlanStep(
                step_id="utr",
                type="capability",
                target=tool_name,
                input_binding=tool_args,
                description="GEMORNA UTR design",
            )
        ])

    def _plan_protein_to_cds(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        """Golden path: protein → CDS design (LinearDesign / RNARL / GEMORNA) via workflow."""
        user_text = raw_text.lower()
        protein_seq = _extract_protein_sequence(raw_text)
        filepath = save_sequence(protein_seq, prefix="protein")
        state["current_filepath"] = filepath
        state["workspace_files"] = state.get("workspace_files", []) + [filepath]

        # Resolve which design tool the user wants
        tool_name, tool_args = _resolve_protein_to_cds_tool(user_text, raw_text)
        design_tool = tool_name.replace("design_mrna_cds_with_", "")

        # Build workflow input
        workflow_input: dict[str, Any] = {
            "protein_sequence": protein_seq,
            "design_tool": design_tool,
        }
        if design_tool == "lineardesign":
            workflow_input["lambda_value"] = float(tool_args.get("lambda_value", 0.0))
        elif design_tool == "rnarl":
            workflow_input["model_type"] = str(tool_args.get("model_type", "Homo sapiens mRNA"))

        # If user explicitly asks for structure, keep fold inside the workflow
        workflow_input["run_fold"] = True
        workflow_input["run_gc"] = True

        return ExecutionPlan(steps=[
            PlanStep(
                step_id="cds_design",
                type="workflow",
                target="mrna_cds_design",
                input_binding=workflow_input,
                output_key="workflow_result",
                description=f"Protein-to-CDS design workflow ({design_tool})",
            )
        ])

    def _plan_default(self, raw_text: str, state: dict[str, Any]) -> ExecutionPlan:
        """Default path: codonw + fold (+ optional tertiary)."""
        user_text = raw_text.lower()
        filepath = state.get("current_filepath")
        if not filepath:
            from agent_core.nodes import _extract_rna_sequence
            filepath = save_sequence(_extract_rna_sequence(raw_text), prefix="mrna")
            state["current_filepath"] = filepath
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        steps: list[PlanStep] = [
            PlanStep(
                step_id="codonw",
                type="capability",
                target="analyze_cds_codon_metrics_with_codonw_slim",
                input_binding=_build_codonw_tool_args(filepath, raw_text),
                description="codonw-slim CDS codon metrics",
            )
        ]
        fold_target = (
            "predict_rna_secondary_structure_with_linearfold"
            if _needs_linearfold(user_text)
            else "predict_rna_secondary_structure"
        )
        fold_args: dict[str, Any] = {"filepath": filepath}
        if fold_target == "predict_rna_secondary_structure_with_linearfold":
            fold_args = _build_linearfold_tool_args(filepath, raw_text)
        steps.append(
            PlanStep(
                step_id="fold",
                type="capability",
                target=fold_target,
                input_binding=fold_args,
                description="Secondary structure prediction",
            )
        )
        if _needs_tertiary_structure(raw_text):
            steps.append(
                PlanStep(
                    step_id="rhofold",
                    type="capability",
                    target="predict_rna_tertiary_structure_with_rhofold",
                    input_binding={"filepath": filepath},
                    description="Tertiary structure prediction (RhoFold)",
                )
            )
        return ExecutionPlan(steps=steps)
