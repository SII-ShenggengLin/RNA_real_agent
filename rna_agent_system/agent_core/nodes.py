"""Node implementations for the MVP siRNA workflow graph."""

from __future__ import annotations

import json
from pathlib import Path
import re
import uuid
from typing import Any, Optional, Tuple

from langchain_core.messages import AIMessage, ToolMessage

from agent_core.file_manager import save_sequence
from agent_core.state import AgentState
from agent_core.tools import (
    check_off_target,
    design_rna_sequence_with_rhodesign,
    design_mrna_cds_with_gemorna,
    design_mrna_cds_with_rnarl,
    mock_codon_optimization,
    predict_mrna_stability_with_rnastop,
    predict_rna_secondary_structure,
    predict_rna_tertiary_structure_with_rhofold,
    predict_sirna_efficiency,
    score_rna_ligand_binding_with_gernabind,
    score_rna_ligand_binding_with_rnasmol,
)

SIRNA_TOOLS = [predict_sirna_efficiency, check_off_target]
MRNA_TOOLS = [
    score_rna_ligand_binding_with_gernabind,
    score_rna_ligand_binding_with_rnasmol,
    predict_mrna_stability_with_rnastop,
    mock_codon_optimization,
    predict_rna_secondary_structure,
    predict_rna_tertiary_structure_with_rhofold,
    design_mrna_cds_with_rnarl,
    design_mrna_cds_with_gemorna,
    design_rna_sequence_with_rhodesign,
]
TOOLS = SIRNA_TOOLS + MRNA_TOOLS
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _msg_text(message: Any) -> str:
    if hasattr(message, "content"):
        content = message.content
        return content if isinstance(content, str) else str(content)
    return str(message)


def _extract_rna_sequence(text: str) -> str:
    normalized = text.upper().replace("T", "U")
    seq = "".join(ch for ch in normalized if ch in {"A", "U", "G", "C"})
    return seq[:21] if seq else "AUGCUAACGUAGCUAUGCUA"


def _extract_long_rna_sequence(text: str) -> Optional[str]:
    matches = re.findall(r"[ACGUTacgut]{12,}", text)
    if not matches:
        return None
    return max(matches, key=len).upper().replace("T", "U")


def _extract_protein_sequence(text: str) -> str:
    candidates = re.findall(r"[A-Za-z\*]{8,}", text)
    if not candidates:
        return "MVSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDA"
    return max(candidates, key=len).upper()


def _needs_secondary_structure(text: str) -> bool:
    return any(k in text for k in ["structure", "fold", "rnafold", "二级结构"])


def _needs_tertiary_structure(text: str) -> bool:
    return any(k in text for k in ["rhofold", "3d", "3-d", "tertiary", "三级结构", "三维结构", "三维", "pdb"])


def _needs_rnasmol_scoring(text: str) -> bool:
    return any(
        k in text
        for k in [
            "rnasmol",
            "smiles",
            "ligand",
            "rna-ligand",
            "配体",
            "结合打分",
            "结合评分",
        ]
    )


def _needs_gernabind_scoring(text: str) -> bool:
    return any(
        k in text
        for k in [
            "gernabind",
            "gerna-bind",
            "gerna bind",
        ]
    )


def _needs_rnastop_prediction(text: str) -> bool:
    return any(
        k in text
        for k in [
            "rnastop",
            "stability",
            "stable",
            "degradation",
            "degrade",
            "稳定性",
            "稳定",
            "降解",
            "半衰期",
        ]
    )


def _extract_path_with_suffixes(text: str, suffixes: Tuple[str, ...]) -> Optional[str]:
    suffix_pattern = "|".join(re.escape(suffix.lstrip(".")) for suffix in suffixes)

    quoted_pattern = re.compile(r"""["']([^"']+)["']""")
    for match in quoted_pattern.finditer(text):
        candidate = match.group(1).strip()
        if re.search(rf"\.({suffix_pattern})$", candidate, re.IGNORECASE):
            return candidate

    unquoted_pattern = re.compile(
        rf"((?:/|\.{{1,2}}/|workspace/|rna_agent_system/)?[A-Za-z0-9_./-]+\.({suffix_pattern}))",
        re.IGNORECASE,
    )
    for match in unquoted_pattern.finditer(text):
        candidate = match.group(1).strip()
        if candidate:
            return candidate
    return None


def _needs_structure_to_sequence_design(text: str) -> bool:
    return any(
        k in text
        for k in [
            "rhodesign",
            "structure-to-sequence",
            "结构到序列",
            "根据结构设计",
            "从结构设计",
            "基于结构设计",
            "根据pdb设计",
            "从pdb设计",
            ".pdb",
            ".cif",
        ]
    )


def _needs_rnarl_design(text: str) -> bool:
    return any(
        k in text
        for k in [
            "rnarl",
            "reinforcement learning",
            "rl design",
            "rl-based",
        ]
    )


def _extract_rnarl_model_type(text: str) -> str:
    lowered = text.lower()
    if "circular" in lowered or "circrna" in lowered or "circ rna" in lowered or "环状" in lowered:
        return "Homo sapiens circular RNA"
    if "arabidopsis" in lowered:
        return "Arabidopsis thaliana mRNA"
    if "escherichia" in lowered or "e. coli" in lowered or "e coli" in lowered:
        return "Escherichia coli mRNA"
    if "penicillium" in lowered or "chrysogenum" in lowered:
        return "Penicillium chrysogenum mRNA"
    if "chlamydomonas" in lowered or "reinhardtii" in lowered:
        return "Chlamydomonas reinhardtii mRNA"
    if "thermococcus" in lowered or "kod1" in lowered:
        return "Thermococcus kodakarensis KOD1 mRNA"
    if "human" in lowered or "homo sapiens" in lowered:
        return "Homo sapiens mRNA"
    return "Homo sapiens mRNA"


def _extract_smiles(text: str) -> Optional[str]:
    patterns = [
        re.compile(r"""smiles?\s*[:=]\s*["']([^"']+)["']""", re.IGNORECASE),
        re.compile(r"""smiles?\s*[:=]\s*([A-Za-z0-9@+\-\[\]\(\)=#$\\/%.]+)""", re.IGNORECASE),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _extract_secondary_structure(text: str) -> Optional[str]:
    patterns = [
        re.compile(r"""secondary_structure\s*[:=]\s*["']?([().]+)["']?""", re.IGNORECASE),
        re.compile(r"""dot[\s_-]*bracket\s*[:=]\s*["']?([().]+)["']?""", re.IGNORECASE),
        re.compile(r"""二级结构\s*[:：=]\s*["']?([().]+)["']?""", re.IGNORECASE),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _extract_gernabind_overrides(text: str) -> dict[str, str]:
    overrides: dict[str, str] = {}
    pdb_path = _extract_path_with_suffixes(text, ("pdb", "cif"))
    if pdb_path:
        overrides["pdb_path"] = pdb_path
    secondary_structure = _extract_secondary_structure(text)
    if secondary_structure:
        overrides["secondary_structure"] = secondary_structure
    return overrides


def _resolve_rnasmol_inputs(text: str) -> Tuple[str, str, bool]:
    smiles = _extract_smiles(text)
    if not smiles:
        raise ValueError(
            "RNAsmol scoring requires a ligand SMILES string. "
            "Please provide it like `SMILES=CCO` or `SMILES: C1=CC=CC=C1`."
        )

    filepath = _extract_path_with_suffixes(text, ("fasta", "fa", "txt", "seq"))
    if filepath:
        return filepath, smiles, False

    rna_sequence = _extract_long_rna_sequence(text)
    if not rna_sequence:
        raise ValueError(
            "RNAsmol scoring requires an RNA sequence or a `.fasta/.fa/.txt/.seq` filepath."
        )

    return save_sequence(rna_sequence, prefix="rnasmol_rna"), smiles, True


def _resolve_rnastop_input(text: str) -> Tuple[str, bool]:
    filepath = _extract_path_with_suffixes(text, ("fasta", "fa", "txt", "seq"))
    if filepath:
        return filepath, False

    rna_sequence = _extract_long_rna_sequence(text)
    if not rna_sequence:
        raise ValueError(
            "RNASTOP prediction requires an RNA sequence or a `.fasta/.fa/.txt/.seq` filepath."
        )

    return save_sequence(rna_sequence, prefix="rnastop_rna"), True


def _extract_structure_design_inputs(text: str) -> Tuple[str, Optional[str]]:
    pdb_path = _extract_path_with_suffixes(text, ("pdb", "cif"))
    ss_path = _extract_path_with_suffixes(text, ("npy",))

    if not pdb_path:
        pdb_path = "rna_agent_system/external_repos/RhoDesign/example/2zh6_B.pdb"

    if not ss_path:
        pdb_candidate = Path(pdb_path)
        derived_npy = pdb_candidate.with_suffix(".npy")
        if derived_npy.is_absolute():
            if derived_npy.exists():
                ss_path = str(derived_npy)
        else:
            repo_relative_npy = (
                Path("rna_agent_system") / derived_npy
                if not str(derived_npy).startswith("rna_agent_system/")
                else derived_npy
            )
            if (PROJECT_ROOT.parent / repo_relative_npy).exists():
                ss_path = str(repo_relative_npy)

    return pdb_path, ss_path


def router_node(state: AgentState) -> AgentState:
    """Route by deterministic rules without LLM."""
    user_text = state.get("input_sequence", "").lower()
    if any(
        k in user_text
        for k in [
            "mrna",
            "rnafold",
            "fold",
            "structure",
            "tertiary",
            "3d",
            "三级结构",
            "三维结构",
            "rhofold",
            "rhodesign",
            "二级结构",
            "密码子",
            "codon",
            "design",
            "设计",
            "gemorna",
            "rnarl",
            "pdb",
            "cif",
            "protein",
            "cds",
            "utr",
            "rnasmol",
            "rnastop",
            "stability",
            "degradation",
            "稳定性",
            "降解",
            "smiles",
            "ligand",
            "配体",
            "gernabind",
            "gerna-bind",
        ]
    ):
        route = "mrna_specialist"
    elif any(k in user_text for k in ["sirna", "脱靶", "off-target"]):
        route = "sirna_specialist"
    else:
        # Default to mRNA for current integration testing focus (RNAfold).
        route = "mrna_specialist"
    decision_note = f"Router decision (rule-based): {route}"

    state["current_task"] = (
        "sirna_design"
        if route == "sirna_specialist"
        else "mrna_design" if route == "mrna_specialist" else "unsupported"
    )
    state["route"] = (
        "sirna" if route == "sirna_specialist" else "mrna" if route == "mrna_specialist" else "unsupported"
    )
    state["messages"] = state.get("messages", []) + [
        AIMessage(content=decision_note)
    ]
    return state


def sirna_specialist_node(state: AgentState) -> AgentState:
    """Emit deterministic siRNA tool calls without LLM."""
    filepath = state.get("current_filepath")
    if not filepath:
        filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="sirna")
        state["current_filepath"] = filepath
        state["workspace_files"] = state.get("workspace_files", []) + [filepath]
    state["active_specialist"] = "sirna_specialist"
    ai_msg = AIMessage(
        content="siRNA specialist (rule-based): dispatch tool calls.",
        tool_calls=[
            {
                "name": "predict_sirna_efficiency",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            },
            {
                "name": "check_off_target",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            },
        ],
    )
    state["messages"] = state.get("messages", []) + [ai_msg]
    return state


def mrna_specialist_node(state: AgentState) -> AgentState:
    """Emit deterministic mRNA tool calls without LLM."""
    raw_text = state.get("input_sequence", "")
    user_text = raw_text.lower()
    state["active_specialist"] = "mrna_specialist"
    gernabind_mode = _needs_gernabind_scoring(user_text)
    rnasmol_mode = _needs_rnasmol_scoring(user_text)
    rnastop_mode = _needs_rnastop_prediction(user_text)
    structure_design_mode = _needs_structure_to_sequence_design(user_text)
    rnarl_mode = _needs_rnarl_design(user_text)
    design_mode = any(
        k in user_text for k in ["design", "设计", "gemorna", "rnarl", "protein", "cds", "utr", "生成"]
    )

    if gernabind_mode:
        filepath, smiles, created_workspace_file = _resolve_rnasmol_inputs(raw_text)
        gernabind_overrides = _extract_gernabind_overrides(raw_text)
        state["current_filepath"] = filepath
        state["ligand_smiles"] = smiles
        if created_workspace_file or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_args: dict[str, Any] = {"filepath": filepath, "smiles": smiles}
        tool_args.update(gernabind_overrides)
        tool_calls = [
            {
                "name": "score_rna_ligand_binding_with_gernabind",
                "args": tool_args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch GerNA-Bind RNA-ligand scoring."
    elif rnasmol_mode:
        filepath, smiles, created_workspace_file = _resolve_rnasmol_inputs(raw_text)
        state["current_filepath"] = filepath
        state["ligand_smiles"] = smiles
        if created_workspace_file or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_calls = [
            {
                "name": "score_rna_ligand_binding_with_rnasmol",
                "args": {"filepath": filepath, "smiles": smiles},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch RNAsmol RNA-ligand scoring."
    elif rnastop_mode:
        filepath, created_workspace_file = _resolve_rnastop_input(raw_text)
        state["current_filepath"] = filepath
        if created_workspace_file or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_calls = [
            {
                "name": "predict_mrna_stability_with_rnastop",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch RNASTOP stability prediction."
    elif structure_design_mode:
        pdb_path, ss_path = _extract_structure_design_inputs(raw_text)
        state["design_input_pdb_filepath"] = pdb_path
        if ss_path:
            state["design_input_secondary_structure_filepath"] = ss_path
        tool_args: dict[str, Any] = {"pdb_filepath": pdb_path}
        if ss_path:
            tool_args["secondary_structure_filepath"] = ss_path
        tool_calls = [
            {
                "name": "design_rna_sequence_with_rhodesign",
                "args": tool_args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch RhoDesign structure-to-sequence design."
    elif design_mode:
        filepath = save_sequence(_extract_protein_sequence(state.get("input_sequence", "")), prefix="protein")
        state["current_filepath"] = filepath
        state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_name = "design_mrna_cds_with_rnarl" if rnarl_mode else "design_mrna_cds_with_gemorna"
        tool_args: dict[str, Any] = {"filepath": filepath}
        if rnarl_mode:
            tool_args["model_type"] = _extract_rnarl_model_type(raw_text)
        tool_calls = [
            {
                "name": tool_name,
                "args": tool_args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = (
            "mRNA specialist (rule-based): dispatch RNARL design."
            if rnarl_mode
            else "mRNA specialist (rule-based): dispatch GEMORNA design."
        )
    else:
        filepath = state.get("current_filepath")
        if not filepath:
            filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="mrna")
            state["current_filepath"] = filepath
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_calls = [
            {
                "name": "mock_codon_optimization",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            },
            {
                "name": "predict_rna_secondary_structure",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            },
        ]
        if _needs_tertiary_structure(user_text):
            tool_calls.append(
                {
                    "name": "predict_rna_tertiary_structure_with_rhofold",
                    "args": {"filepath": filepath},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                }
            )
        content = "mRNA specialist (rule-based): dispatch tool calls."

    ai_msg = AIMessage(content=content, tool_calls=tool_calls)
    state["messages"] = state.get("messages", []) + [ai_msg]
    return state


def tool_execution_node(state: AgentState) -> AgentState:
    """Execute tool calls emitted by specialist LLM message."""
    messages = state.get("messages", [])
    if not messages or not isinstance(messages[-1], AIMessage):
        return state

    ai_msg = messages[-1]
    out_messages: list[Any] = []
    if not ai_msg.tool_calls:
        filepath = state.get("current_filepath")
        user_text = state.get("input_sequence", "").lower()
        if state.get("active_specialist") == "sirna_specialist":
            if not filepath:
                filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="sirna")
                state["current_filepath"] = filepath
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            fallback_calls = [
                {"name": "predict_sirna_efficiency", "args": {"filepath": filepath}},
                {"name": "check_off_target", "args": {"filepath": filepath}},
            ]
        elif _needs_gernabind_scoring(user_text):
            filepath, smiles, created_workspace_file = _resolve_rnasmol_inputs(state.get("input_sequence", ""))
            gernabind_overrides = _extract_gernabind_overrides(state.get("input_sequence", ""))
            state["current_filepath"] = filepath
            state["ligand_smiles"] = smiles
            if created_workspace_file or filepath.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            tool_args = {"filepath": filepath, "smiles": smiles}
            tool_args.update(gernabind_overrides)
            fallback_calls = [
                {
                    "name": "score_rna_ligand_binding_with_gernabind",
                    "args": tool_args,
                }
            ]
        elif _needs_rnasmol_scoring(user_text):
            filepath, smiles, created_workspace_file = _resolve_rnasmol_inputs(state.get("input_sequence", ""))
            state["current_filepath"] = filepath
            state["ligand_smiles"] = smiles
            if created_workspace_file or filepath.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            fallback_calls = [
                {
                    "name": "score_rna_ligand_binding_with_rnasmol",
                    "args": {"filepath": filepath, "smiles": smiles},
                }
            ]
        elif _needs_rnastop_prediction(user_text):
            filepath, created_workspace_file = _resolve_rnastop_input(state.get("input_sequence", ""))
            state["current_filepath"] = filepath
            if created_workspace_file or filepath.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            fallback_calls = [
                {
                    "name": "predict_mrna_stability_with_rnastop",
                    "args": {"filepath": filepath},
                }
            ]
        elif _needs_structure_to_sequence_design(user_text):
            pdb_path, ss_path = _extract_structure_design_inputs(state.get("input_sequence", ""))
            structure_call: dict[str, Any] = {
                "name": "design_rna_sequence_with_rhodesign",
                "args": {"pdb_filepath": pdb_path},
            }
            if ss_path:
                structure_call["args"]["secondary_structure_filepath"] = ss_path
            fallback_calls = [structure_call]
        elif any(k in user_text for k in ["design", "设计", "gemorna", "rnarl", "protein", "cds", "utr", "生成"]):
            if not filepath:
                filepath = save_sequence(
                    _extract_protein_sequence(state.get("input_sequence", "")),
                    prefix="protein",
                )
                state["current_filepath"] = filepath
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            tool_name = (
                "design_mrna_cds_with_rnarl"
                if _needs_rnarl_design(user_text)
                else "design_mrna_cds_with_gemorna"
            )
            tool_args = {"filepath": filepath}
            if tool_name == "design_mrna_cds_with_rnarl":
                tool_args["model_type"] = _extract_rnarl_model_type(state.get("input_sequence", ""))
            fallback_calls = [
                {"name": tool_name, "args": tool_args},
            ]
        else:
            if not filepath:
                filepath = save_sequence(_extract_rna_sequence(state.get("input_sequence", "")), prefix="seq")
                state["current_filepath"] = filepath
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            fallback_calls = [
                {"name": "mock_codon_optimization", "args": {"filepath": filepath}},
                {"name": "predict_rna_secondary_structure", "args": {"filepath": filepath}},
            ]
            if _needs_tertiary_structure(user_text):
                fallback_calls.append(
                    {"name": "predict_rna_tertiary_structure_with_rhofold", "args": {"filepath": filepath}}
                )
        ai_msg = AIMessage(
            content="Tool executor repaired missing tool calls.",
            tool_calls=[
                {
                    "name": call["name"],
                    "args": call["args"],
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                }
                for call in fallback_calls
            ],
        )
        messages = messages + [ai_msg]
    for call in ai_msg.tool_calls:
        tool_name = call["name"]
        tool_args = call.get("args", {})
        tool_obj = TOOLS_BY_NAME.get(tool_name)
        if not tool_obj:
            continue
        tool_result = tool_obj.invoke(tool_args)
        out_messages.append(
            ToolMessage(
                content=json.dumps(tool_result, ensure_ascii=True),
                tool_call_id=call["id"],
                name=tool_name,
            )
        )

        if tool_name == "predict_sirna_efficiency":
            state["efficiency_score"] = float(tool_result.get("efficiency_score", 0.0))
            state["candidate_sequence"] = str(tool_result.get("sequence", ""))
            state["current_filepath"] = str(tool_result.get("filepath", state.get("current_filepath", "")))
        elif tool_name == "check_off_target":
            state["off_target_genes"] = int(tool_result.get("off_target_genes", 0))
            if not state.get("candidate_sequence"):
                state["candidate_sequence"] = str(tool_result.get("sequence", ""))
            state["current_filepath"] = str(tool_result.get("filepath", state.get("current_filepath", "")))
        elif tool_name == "mock_codon_optimization":
            state["cai_score"] = float(tool_result.get("cai_score", 0.0))
            optimized_filepath = str(tool_result.get("optimized_filepath", ""))
            if optimized_filepath:
                state["current_filepath"] = optimized_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [optimized_filepath]
        elif tool_name == "predict_rna_secondary_structure":
            mfe_match = re.search(r"mfe=([-+]?\d*\.?\d+)", str(tool_result))
            structure_match = re.search(r"structure=([^;]+)", str(tool_result))
            if mfe_match:
                state["mfe"] = float(mfe_match.group(1))
            if structure_match:
                structure = structure_match.group(1).strip()
                structure_filepath = save_sequence(structure, prefix="structure")
                state["structure_filepath"] = structure_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [structure_filepath]
        elif tool_name == "predict_rna_tertiary_structure_with_rhofold":
            output_pdb_filepath = str(tool_result.get("output_pdb_filepath", ""))
            if output_pdb_filepath:
                state["tertiary_structure_filepath"] = output_pdb_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_pdb_filepath]
            secondary_ct_filepath = str(tool_result.get("secondary_structure_ct_filepath", ""))
            if secondary_ct_filepath:
                state["tertiary_structure_ct_filepath"] = secondary_ct_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [secondary_ct_filepath]
            results_npz_filepath = str(tool_result.get("results_npz_filepath", ""))
            if results_npz_filepath:
                state["tertiary_results_filepath"] = results_npz_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [results_npz_filepath]
            log_filepath = str(tool_result.get("log_filepath", ""))
            if log_filepath:
                state["tertiary_log_filepath"] = log_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [log_filepath]
            state["mean_plddt"] = float(tool_result.get("mean_plddt", 0.0))
        elif tool_name in {"design_mrna_cds_with_gemorna", "design_mrna_cds_with_rnarl"}:
            output_filepath = str(tool_result.get("output_filepath", ""))
            if output_filepath:
                state["current_filepath"] = output_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_filepath]
            state["candidate_sequence"] = str(tool_result.get("generated_sequence", ""))
            state["design_model"] = str(tool_result.get("model", ""))
            state["rnarl_model_type"] = str(tool_result.get("model_type", ""))
            state["rnarl_checkpoint_path"] = str(tool_result.get("checkpoint_path", ""))
            state["rnarl_esm2_model_path"] = str(tool_result.get("esm2_model_path", ""))

            user_text = state.get("input_sequence", "").lower()
            if _needs_secondary_structure(user_text):
                fold_result = predict_rna_secondary_structure.invoke({"filepath": state["current_filepath"]})
                out_messages.append(
                    ToolMessage(
                        content=json.dumps(fold_result, ensure_ascii=True),
                        tool_call_id=f"call_{uuid.uuid4().hex[:8]}",
                        name="predict_rna_secondary_structure",
                    )
                )
                mfe_match = re.search(r"mfe=([-+]?\d*\.?\d+)", str(fold_result))
                structure_match = re.search(r"structure=([^;]+)", str(fold_result))
                if mfe_match:
                    state["mfe"] = float(mfe_match.group(1))
                if structure_match:
                    structure = structure_match.group(1).strip()
                    structure_filepath = save_sequence(structure, prefix="structure")
                    state["structure_filepath"] = structure_filepath
                    state["workspace_files"] = state.get("workspace_files", []) + [structure_filepath]
            if _needs_tertiary_structure(user_text):
                tertiary_result = predict_rna_tertiary_structure_with_rhofold.invoke(
                    {"filepath": state["current_filepath"]}
                )
                out_messages.append(
                    ToolMessage(
                        content=json.dumps(tertiary_result, ensure_ascii=True),
                        tool_call_id=f"call_{uuid.uuid4().hex[:8]}",
                        name="predict_rna_tertiary_structure_with_rhofold",
                    )
                )
                output_pdb_filepath = str(tertiary_result.get("output_pdb_filepath", ""))
                if output_pdb_filepath:
                    state["tertiary_structure_filepath"] = output_pdb_filepath
                    state["workspace_files"] = state.get("workspace_files", []) + [output_pdb_filepath]
                secondary_ct_filepath = str(tertiary_result.get("secondary_structure_ct_filepath", ""))
                if secondary_ct_filepath:
                    state["tertiary_structure_ct_filepath"] = secondary_ct_filepath
                    state["workspace_files"] = state.get("workspace_files", []) + [secondary_ct_filepath]
                results_npz_filepath = str(tertiary_result.get("results_npz_filepath", ""))
                if results_npz_filepath:
                    state["tertiary_results_filepath"] = results_npz_filepath
                    state["workspace_files"] = state.get("workspace_files", []) + [results_npz_filepath]
                log_filepath = str(tertiary_result.get("log_filepath", ""))
                if log_filepath:
                    state["tertiary_log_filepath"] = log_filepath
                    state["workspace_files"] = state.get("workspace_files", []) + [log_filepath]
                state["mean_plddt"] = float(tertiary_result.get("mean_plddt", 0.0))
        elif tool_name == "design_rna_sequence_with_rhodesign":
            state["design_input_pdb_filepath"] = str(tool_result.get("input_pdb_filepath", ""))
            secondary_structure_filepath = str(tool_result.get("secondary_structure_filepath", ""))
            if secondary_structure_filepath:
                state["design_input_secondary_structure_filepath"] = secondary_structure_filepath

            output_filepath = str(tool_result.get("output_filepath", ""))
            if output_filepath:
                state["current_filepath"] = output_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_filepath]

            output_fasta_filepath = str(tool_result.get("output_fasta_filepath", ""))
            if output_fasta_filepath:
                state["designed_sequence_fasta_filepath"] = output_fasta_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_fasta_filepath]

            stdout_filepath = str(tool_result.get("stdout_filepath", ""))
            if stdout_filepath:
                state["workspace_files"] = state.get("workspace_files", []) + [stdout_filepath]
            stderr_filepath = str(tool_result.get("stderr_filepath", ""))
            if stderr_filepath:
                state["workspace_files"] = state.get("workspace_files", []) + [stderr_filepath]

            state["candidate_sequence"] = str(tool_result.get("predicted_sequence", ""))
            if "recovery_rate" in tool_result:
                state["sequence_recovery_rate"] = float(tool_result.get("recovery_rate", 0.0))
        elif tool_name == "score_rna_ligand_binding_with_gernabind":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
            state["candidate_sequence"] = str(tool_result.get("rna_sequence", ""))
            state["ligand_smiles"] = str(tool_result.get("smiles", ""))
            state["gernabind_probability"] = float(tool_result.get("probability_positive", 0.0))
            state["gernabind_predicted_label"] = int(tool_result.get("predicted_label", 0))
            state["gernabind_checkpoint_path"] = str(tool_result.get("checkpoint_path", ""))
            state["gernabind_preprocessing_pdb_path"] = str(
                tool_result.get("preprocessing_pdb_path", "")
            )
        elif tool_name == "score_rna_ligand_binding_with_rnasmol":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
            state["candidate_sequence"] = str(tool_result.get("rna_sequence", ""))
            state["ligand_smiles"] = str(tool_result.get("smiles", ""))
            state["rnasmol_probability"] = float(tool_result.get("probability_positive", 0.0))
            state["rnasmol_predicted_label"] = int(tool_result.get("predicted_label", 0))
            state["rnasmol_checkpoint_path"] = str(tool_result.get("checkpoint_path", ""))
        elif tool_name == "predict_mrna_stability_with_rnastop":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
            prediction_filepath = str(tool_result.get("prediction_filepath", ""))
            if prediction_filepath:
                state["rnastop_prediction_filepath"] = prediction_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [prediction_filepath]
            state["candidate_sequence"] = str(tool_result.get("used_sequence", tool_result.get("sequence", "")))
            state["rnastop_mean_reactivity"] = float(tool_result.get("mean_reactivity", 0.0))
            state["rnastop_mean_deg_mg_ph10"] = float(tool_result.get("mean_deg_mg_ph10", 0.0))
            state["rnastop_mean_deg_mg_50c"] = float(tool_result.get("mean_deg_mg_50c", 0.0))
            state["rnastop_mfe"] = float(tool_result.get("mfe", 0.0))
            state["rnastop_checkpoint_path"] = str(tool_result.get("checkpoint_path", ""))
            if not state.get("mfe"):
                state["mfe"] = state["rnastop_mfe"]

    state["messages"] = messages + out_messages
    return state


def critic_node(state: AgentState) -> AgentState:
    """Use hard rules only (no LLM) to decide pass/reject."""
    off_target = state.get("off_target_genes", 0)
    mfe = state.get("mfe", 0.0)
    cai_score = state.get("cai_score", 0.0)
    mean_plddt = state.get("mean_plddt", 0.0)
    rnasmol_probability = state.get("rnasmol_probability", 0.0)
    rnasmol_predicted_label = state.get("rnasmol_predicted_label", 0)
    gernabind_probability = state.get("gernabind_probability", 0.0)
    gernabind_predicted_label = state.get("gernabind_predicted_label", 0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    specialist = state.get("active_specialist", "")

    hard_reject = False
    if specialist == "sirna_specialist" and off_target > 0:
        hard_reject = True
    user_text = state.get("input_sequence", "").lower()
    if (
        specialist == "mrna_specialist"
        and not _needs_rnastop_prediction(user_text)
        and not _needs_structure_to_sequence_design(user_text)
        and any(k in user_text for k in ["structure", "fold", "rnafold", "二级结构"])
        and mfe > -20.0
    ):
        hard_reject = True
    should_retry = hard_reject and retry_count < max_retries

    if should_retry:
        state["retry_count"] = retry_count + 1
        state["next_action"] = "retry"
        state["critic_verdict"] = "reject"
        state["messages"] = state.get("messages", []) + [
            AIMessage(
                content=(
                    f"Critic (rule-based): reject and retry. "
                    f"specialist={specialist}, off_target={off_target}, mfe={mfe}, retry={retry_count + 1}"
                )
            )
        ]
    else:
        state["next_action"] = "finish"
        state["critic_verdict"] = "pass"
        state["final_report"] = (
            f"specialist={specialist}; "
            f"filepath={state.get('current_filepath', '')}; "
            f"efficiency={state.get('efficiency_score', 0.0)}; "
            f"off_target_genes={off_target}; "
            f"cai_score={cai_score}; "
            f"mfe={mfe}; "
            f"design_model={state.get('design_model', '')}; "
            f"rnarl_model_type={state.get('rnarl_model_type', '')}; "
            f"rnarl_checkpoint_path={state.get('rnarl_checkpoint_path', '')}; "
            f"rnarl_esm2_model_path={state.get('rnarl_esm2_model_path', '')}; "
            f"design_input_pdb_filepath={state.get('design_input_pdb_filepath', '')}; "
            f"designed_sequence_fasta_filepath={state.get('designed_sequence_fasta_filepath', '')}; "
            f"sequence_recovery_rate={state.get('sequence_recovery_rate', 0.0)}; "
            f"tertiary_structure_filepath={state.get('tertiary_structure_filepath', '')}; "
            f"mean_plddt={mean_plddt}; "
            f"ligand_smiles={state.get('ligand_smiles', '')}; "
            f"gernabind_probability={gernabind_probability}; "
            f"gernabind_predicted_label={gernabind_predicted_label}; "
            f"gernabind_checkpoint_path={state.get('gernabind_checkpoint_path', '')}; "
            f"gernabind_preprocessing_pdb_path={state.get('gernabind_preprocessing_pdb_path', '')}; "
            f"rnasmol_probability={rnasmol_probability}; "
            f"rnasmol_predicted_label={rnasmol_predicted_label}; "
            f"rnasmol_checkpoint_path={state.get('rnasmol_checkpoint_path', '')}; "
            f"rnastop_prediction_filepath={state.get('rnastop_prediction_filepath', '')}; "
            f"rnastop_mean_reactivity={state.get('rnastop_mean_reactivity', 0.0)}; "
            f"rnastop_mean_deg_mg_ph10={state.get('rnastop_mean_deg_mg_ph10', 0.0)}; "
            f"rnastop_mean_deg_mg_50c={state.get('rnastop_mean_deg_mg_50c', 0.0)}; "
            f"rnastop_mfe={state.get('rnastop_mfe', 0.0)}; "
            f"rnastop_checkpoint_path={state.get('rnastop_checkpoint_path', '')}; "
            f"retries={retry_count}"
        )
        state["messages"] = state.get("messages", []) + [
            AIMessage(
                content=(
                    f"Critic (rule-based): pass. "
                    f"specialist={specialist}, off_target={off_target}, mfe={mfe}"
                )
            )
        ]
    return state


def route_after_router(state: AgentState) -> str:
    """Choose downstream branch after routing."""
    if state.get("route") == "sirna":
        return "sirna_specialist"
    if state.get("route") == "mrna":
        return "mrna_specialist"
    return "end"


def route_after_critic(state: AgentState) -> str:
    """Choose whether to retry or finish."""
    if state.get("next_action") != "retry":
        return "end"
    return state.get("active_specialist", "sirna_specialist")
