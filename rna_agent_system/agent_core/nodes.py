"""Node implementations for the MVP siRNA workflow graph."""

from __future__ import annotations

import json
from pathlib import Path
import re
import uuid
from typing import Any, Optional, Tuple

from langchain_core.messages import AIMessage, ToolMessage

from agent_core.file_manager import save_sequence, save_text_file
from agent_core.state import AgentState
from agent_core.tools import (
    calculate_crispr_specificity_with_crisot,
    check_off_target,
    design_sirna_with_evitar,
    design_mrna_cds_with_lineardesign,
    design_rna_sequence_with_rhodesign,
    design_mrna_cds_with_gemorna,
    design_mrna_cds_with_rnarl,
    mock_codon_optimization,
    optimize_sgrna_with_crisot,
    predict_mrna_stability_with_rnastop,
    predict_putative_ires_with_iresfinder,
    predict_rna_secondary_structure,
    predict_rna_secondary_structure_with_linearfold,
    predict_rna_tertiary_structure_with_rhofold,
    predict_sirna_efficiency,
    run_odesign_inference,
    score_crispr_off_target_with_crisot,
    search_crispr_off_targets_with_crisot,
    score_rna_ligand_binding_with_gernabind,
    score_rna_ligand_binding_with_rnasmol,
)

SIRNA_TOOLS = [predict_sirna_efficiency, check_off_target, design_sirna_with_evitar]
CRISPR_TOOLS = [
    score_crispr_off_target_with_crisot,
    calculate_crispr_specificity_with_crisot,
    search_crispr_off_targets_with_crisot,
    optimize_sgrna_with_crisot,
]
MRNA_TOOLS = [
    score_rna_ligand_binding_with_gernabind,
    score_rna_ligand_binding_with_rnasmol,
    predict_mrna_stability_with_rnastop,
    predict_putative_ires_with_iresfinder,
    mock_codon_optimization,
    predict_rna_secondary_structure,
    predict_rna_secondary_structure_with_linearfold,
    predict_rna_tertiary_structure_with_rhofold,
    design_mrna_cds_with_lineardesign,
    design_mrna_cds_with_rnarl,
    design_mrna_cds_with_gemorna,
    design_rna_sequence_with_rhodesign,
    run_odesign_inference,
]
TOOLS = SIRNA_TOOLS + CRISPR_TOOLS + MRNA_TOOLS
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTEIN_RESIDUE_NAMES = {
    "ALA",
    "ARG",
    "ASN",
    "ASP",
    "CYS",
    "GLN",
    "GLU",
    "GLY",
    "HIS",
    "ILE",
    "LEU",
    "LYS",
    "MET",
    "PHE",
    "PRO",
    "SER",
    "THR",
    "TRP",
    "TYR",
    "VAL",
    "MSE",
    "SEC",
    "PYL",
    "ASX",
    "GLX",
    "UNK",
}


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


def _extract_crispr_named_sequence(text: str, labels: Tuple[str, ...]) -> Optional[str]:
    joined_labels = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(
        rf"(?:{joined_labels})\s*[:=]\s*[\"']?([ACGUTNacgutn]{{20,30}})[\"']?",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip().upper().replace("U", "T")


def _extract_crispr_sequences(text: str) -> list[str]:
    return [match.upper().replace("U", "T") for match in re.findall(r"[ACGUTNacgutn]{20,23}", text)]


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


def _needs_iresfinder_prediction(text: str) -> bool:
    lowered = text.lower()
    if "iresfinder" in lowered or "internal ribosome" in lowered:
        return True
    return re.search(r"\bires\b", lowered) is not None


def _needs_evitar_mode(text: str) -> bool:
    return any(
        k in text
        for k in [
            "evitar",
            "cas13",
            "future virus",
            "future viruses",
            "predesign",
            "rnaxs",
            "predsi",
        ]
    )


def _build_iresfinder_tool_args(filepath: str, raw_text: str) -> dict[str, Any]:
    args: dict[str, Any] = {"filepath": filepath}
    mode = _extract_int_setting(raw_text, ("ires_mode", "iresfinder_mode"))
    if mode is not None and 0 <= mode <= 2:
        args["mode"] = mode
    window_size = _extract_int_setting(raw_text, ("window_size", "ires_window", "ires_window_size"))
    if window_size is not None:
        args["window_size"] = window_size
    step_size = _extract_int_setting(raw_text, ("step_size", "ires_step", "ires_step_size"))
    if step_size is not None:
        args["step_size"] = step_size
    decision_threshold = _extract_float_setting(
        raw_text,
        ("decision_threshold", "ires_threshold", "iresfinder_threshold"),
    )
    if decision_threshold is not None:
        args["decision_threshold"] = decision_threshold
    return args


def _needs_odesign_mode(text: str) -> bool:
    return "odesign" in text


def _needs_crispr_mode(text: str) -> bool:
    return any(
        k in text
        for k in [
            "crisot",
            "crispr",
            "cas9",
            "sgRNA".lower(),
            "sgrna",
            "guide rna",
            "guide-rna",
            "off-spec",
            "off_spec",
        ]
    )


def _needs_crisot_optimization(text: str) -> bool:
    return any(
        k in text
        for k in [
            "opti",
            "optimize",
            "optimization",
            "优化",
            "优化sg",
            "降低off-target",
            "降低 off-target",
            "降低脱靶",
            "improve specificity",
            "increase specificity",
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


def _needs_lineardesign(text: str) -> bool:
    return any(
        k in text
        for k in [
            "lineardesign",
            "linear design",
        ]
    )


def _needs_linearfold(text: str) -> bool:
    lowered = text.lower()
    if "linearfold" in lowered:
        return True
    if "linear fold" in lowered:
        if "lineardesign" in lowered or "linear design" in lowered:
            return False
        return True
    return False


def _build_linearfold_tool_args(filepath: str, raw_text: str) -> dict[str, Any]:
    args: dict[str, Any] = {"filepath": filepath}
    lowered = raw_text.lower()
    if "linearfold-v" in lowered or "linearfold_v" in lowered:
        args["use_vienna"] = True
    elif "linearfold" in lowered and "vienna" in lowered:
        args["use_vienna"] = True
    beam = _extract_int_setting(raw_text, ("beam_size", "beamsize", "beam"))
    if beam is not None and beam >= 0:
        args["beam_size"] = beam
    dangles = _extract_int_setting(raw_text, ("dangles", "dangle"))
    if dangles in (0, 2):
        args["dangles"] = dangles
    return args


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


def _extract_hotspot(text: str) -> Optional[str]:
    patterns = [
        re.compile(
            r"""(?:hotspot|hotspots|binding_site|binding-site|热点)\s*[:=]\s*["']?([A-Za-z0-9_,/-]+)["']?""",
            re.IGNORECASE,
        ),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if not match:
            continue
        candidate = match.group(1).strip().replace(" ", "")
        if re.fullmatch(r"[A-Za-z0-9]+/\d+(?:,[A-Za-z0-9]+/\d+)*", candidate):
            return candidate
    return None


def _extract_float_setting(text: str, labels: Tuple[str, ...]) -> Optional[float]:
    joined_labels = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(rf"(?:{joined_labels})\s*[:=]\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_int_setting(text: str, labels: Tuple[str, ...]) -> Optional[int]:
    joined_labels = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(rf"(?:{joined_labels})\s*[:=]\s*(\d+)", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _extract_string_setting(text: str, labels: Tuple[str, ...]) -> Optional[str]:
    joined_labels = "|".join(re.escape(label) for label in labels)
    patterns = [
        re.compile(rf"""(?:{joined_labels})\s*[:=]\s*["']([^"']+)["']""", re.IGNORECASE),
        re.compile(rf"""(?:{joined_labels})\s*[:=]\s*([A-Za-z0-9:_-]+)""", re.IGNORECASE),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _extract_bool_setting(text: str, labels: Tuple[str, ...]) -> Optional[bool]:
    joined_labels = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(
        rf"(?:{joined_labels})\s*[:=]\s*(true|false|yes|no|on|off|1|0)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    value = match.group(1).strip().lower()
    return value in {"true", "yes", "on", "1"}


def _tokenize_mmcif_row(line: str) -> list[str]:
    return re.findall(r'''(?:'[^']*'|"[^"]*"|\S+)''', line)


def _parse_pdb_protein_chain_ranges(structure_path: Path) -> dict[str, Tuple[int, int]]:
    ranges: dict[str, list[int]] = {}
    for line in structure_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith("ATOM"):
            continue
        residue_name = line[17:20].strip().upper()
        if residue_name not in PROTEIN_RESIDUE_NAMES:
            continue
        chain_id = line[21:22].strip()
        residue_id_text = line[22:26].strip()
        if not chain_id or not residue_id_text:
            continue
        try:
            residue_id = int(residue_id_text)
        except ValueError:
            continue
        ranges.setdefault(chain_id, []).append(residue_id)
    return {
        chain_id: (min(residue_ids), max(residue_ids))
        for chain_id, residue_ids in ranges.items()
        if residue_ids
    }


def _parse_cif_protein_chain_ranges(structure_path: Path) -> dict[str, Tuple[int, int]]:
    ranges: dict[str, list[int]] = {}
    lines = structure_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    in_atom_loop = False
    for line in lines:
        if line.startswith("_atom_site.group_PDB"):
            in_atom_loop = True
            continue
        if not in_atom_loop:
            continue
        if not line or line.startswith("#"):
            continue
        if not (line.startswith("ATOM") or line.startswith("HETATM")):
            continue
        tokens = _tokenize_mmcif_row(line)
        if len(tokens) < 24:
            continue
        residue_name = tokens[22].strip("'\"").upper()
        if residue_name not in PROTEIN_RESIDUE_NAMES:
            continue
        chain_id = tokens[23].strip("'\"")
        residue_id_text = tokens[21].strip("'\"")
        if not chain_id or residue_id_text in {"?", "."}:
            continue
        try:
            residue_id = int(residue_id_text)
        except ValueError:
            continue
        ranges.setdefault(chain_id, []).append(residue_id)
    return {
        chain_id: (min(residue_ids), max(residue_ids))
        for chain_id, residue_ids in ranges.items()
        if residue_ids
    }


def _infer_odesign_protein_segment(
    structure_path_str: str,
    hotspot: str,
    explicit_protein_chain: Optional[str] = None,
) -> str:
    structure_path = Path(structure_path_str)
    suffix = structure_path.suffix.lower()
    if suffix == ".pdb":
        ranges = _parse_pdb_protein_chain_ranges(structure_path)
    elif suffix == ".cif":
        ranges = _parse_cif_protein_chain_ranges(structure_path)
    else:
        raise ValueError(
            "ODesign protein-binding RNA mode currently supports `.pdb` and `.cif` structure files."
        )

    if not ranges:
        raise ValueError(
            f"Unable to infer protein chain ranges from structure file: {structure_path_str}"
        )

    hotspot_entries = [entry for entry in hotspot.split(",") if entry.strip()]
    hotspot_chain = hotspot_entries[0].split("/")[0].strip() if hotspot_entries else ""
    preferred_chain = explicit_protein_chain or hotspot_chain

    if preferred_chain and preferred_chain in ranges:
        start, end = ranges[preferred_chain]
        return f"{preferred_chain}/{start}-{end}"

    if len(ranges) == 1:
        chain_id, (start, end) = next(iter(ranges.items()))
        return f"{chain_id}/{start}-{end}"

    raise ValueError(
        "Unable to determine the target protein chain automatically. "
        "Please provide `protein_chain=...` or `protein_segment=CHAIN/start-end`."
    )


def _needs_odesign_protein_binding_rna(text: str) -> bool:
    return any(
        key in text
        for key in [
            "protein-binding rna",
            "protein binding rna",
            "prot_binding_rna",
            "蛋白结合rna",
            "蛋白结合 rna",
            "结合蛋白的rna",
            "结合蛋白的 rna",
        ]
    )


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


def _extract_named_filepath(text: str, labels: Tuple[str, ...], suffixes: Tuple[str, ...]) -> Optional[str]:
    labels_pattern = "|".join(re.escape(label) for label in labels)
    suffix_pattern = "|".join(re.escape(suffix.lstrip(".")) for suffix in suffixes)
    pattern = re.compile(
        rf"(?:{labels_pattern})\s*[:=]\s*[\"']?([^\"'\s]+\.({suffix_pattern}))[\"']?",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip()


def _build_evitar_tool_args(filepath: str, raw_text: str) -> dict[str, Any]:
    lowered = raw_text.lower()
    args: dict[str, Any] = {
        "filepath": filepath,
        "mode": "predesign"
        if any(key in lowered for key in ["predesign", "future virus", "future viruses", "未来"])
        else "existing",
        "predict": "CRISPR"
        if any(key in lowered for key in ["cas13", "gRNA".lower(), "crispr"])
        else "rnaxs"
        if "rnaxs" in lowered
        else "predsi",
        "off_target": any(key in lowered for key in ["offtarget", "off-target", "脱靶"]),
    }
    ncores = _extract_int_setting(raw_text, ("ncores", "threads", "cores"))
    if ncores is not None and ncores > 0:
        args["ncores"] = ncores

    strains_path = _extract_named_filepath(raw_text, ("strains", "strain", "variants"), ("fa", "fasta", "fna"))
    if strains_path:
        args["strains_path"] = strains_path
    return args


def _extract_odesign_request(text: str) -> Tuple[dict[str, Any], dict[str, Any]]:
    lowered = text.lower()
    input_json_path = _extract_path_with_suffixes(text, ("json",))
    created_workspace_file = False

    if not input_json_path:
        if _needs_odesign_protein_binding_rna(lowered):
            ref_file = _extract_path_with_suffixes(text, ("cif", "pdb"))
            if not ref_file:
                raise ValueError(
                    "ODesign protein-binding RNA mode requires a reference `.cif` or `.pdb` file."
                )
            hotspot = _extract_hotspot(text)
            if not hotspot:
                raise ValueError(
                    "ODesign protein-binding RNA mode requires hotspot residues, for example "
                    "`hotspot=C/18,C/90,C/79,C/49`."
                )
            length = _extract_int_setting(text, ("length", "len", "rna_length", "长度"))
            if length is None:
                nt_match = re.search(r"(\d+)\s*(?:nt|nts|nucleotide|nucleotides)", text, re.IGNORECASE)
                if nt_match:
                    length = int(nt_match.group(1))
            if length is None or length <= 0:
                raise ValueError(
                    "ODesign protein-binding RNA mode requires the RNA length, for example "
                    "`length=61` or `61 nt`."
                )

            protein_segment = _extract_string_setting(text, ("protein_segment", "target_segment"))
            protein_chain = _extract_string_setting(text, ("protein_chain", "target_chain"))
            resolved_ref_file = Path(ref_file)
            if not resolved_ref_file.is_absolute():
                resolved_ref_file = (PROJECT_ROOT / ref_file).resolve()
                if not resolved_ref_file.exists():
                    resolved_ref_file = (PROJECT_ROOT.parent / ref_file).resolve()
            if not resolved_ref_file.exists():
                raise ValueError(
                    f"ODesign reference structure file does not exist: {ref_file}"
                )
            if protein_segment:
                normalized_protein_segment = protein_segment.replace(" ", "")
            else:
                normalized_protein_segment = _infer_odesign_protein_segment(
                    str(resolved_ref_file),
                    hotspot,
                    explicit_protein_chain=protein_chain,
                )

            sample_name = (
                _extract_string_setting(text, ("sample_name", "name", "job_name"))
                or f"odesign_prot_binding_rna_{length}"
            )
            input_spec = [
                {
                    "name": sample_name,
                    "ref_file": ref_file,
                    "chains": [
                        {
                            "chain_type": "proteinChain",
                            "sequence": normalized_protein_segment,
                        },
                        {
                            "chain_type": "rnaChain",
                            "sequence": f"{length}-{length}",
                        },
                    ],
                    "hotspot": hotspot,
                    "center_method": "hotspot_center",
                }
            ]
            input_json_path = save_text_file(
                json.dumps(input_spec, ensure_ascii=True, indent=2),
                prefix="odesign_input",
                suffix=".json",
            )
            created_workspace_file = True
        elif any(
            key in lowered
            for key in ["backbone", "骨架", "de novo", "从头", "length", "长度", "nt"]
        ):
            length = _extract_int_setting(text, ("length", "len", "rna_length", "长度"))
            if length is None:
                nt_match = re.search(r"(\d+)\s*(?:nt|nts|nucleotide|nucleotides)", text, re.IGNORECASE)
                if nt_match:
                    length = int(nt_match.group(1))
            if length is None or length <= 0:
                raise ValueError(
                    "ODesign RNA backbone mode requires a positive length, for example "
                    "`ODesign 设计 50 nt RNA backbone` or `length=50`."
                )
            input_spec = [
                {
                    "name": f"odesign_rna_bb_{length}",
                    "ref_file": "",
                    "chains": [
                        {
                            "chain_type": "rnaChain",
                            "sequence": f"{length}-{length}",
                        }
                    ],
                }
            ]
            input_json_path = save_text_file(
                json.dumps(input_spec, ensure_ascii=True, indent=2),
                prefix="odesign_input",
                suffix=".json",
            )
            created_workspace_file = True
        else:
            raise ValueError(
                "ODesign currently supports an explicit `.json` input filepath, a protein-binding RNA "
                "request with `ref_file + hotspot + RNA length`, or a simple RNA backbone request."
            )

    model_match = re.search(r"(odesign_base_[a-z_]+)", text, re.IGNORECASE)
    infer_model_name = (
        model_match.group(1) if model_match else "odesign_base_na_rigid"
    )
    design_modality = _extract_string_setting(
        text,
        ("design_modality", "odesign_modality", "modality"),
    )
    if not design_modality:
        design_modality = "dna" if "dna" in lowered else "rna"

    tool_args: dict[str, Any] = {
        "input_json_filepath": input_json_path,
        "infer_model_name": infer_model_name,
        "design_modality": design_modality,
    }

    exp_name = _extract_string_setting(text, ("exp_name", "experiment", "job_name"))
    if exp_name:
        tool_args["exp_name"] = exp_name

    n_sample = _extract_int_setting(text, ("n_sample", "samples", "num_samples"))
    if n_sample is not None:
        tool_args["n_sample"] = n_sample

    seed = _extract_int_setting(text, ("seed",))
    if seed is not None:
        tool_args["seeds_json"] = json.dumps([seed], ensure_ascii=True)

    use_msa = _extract_bool_setting(text, ("use_msa", "msa"))
    if use_msa is not None:
        tool_args["use_msa"] = use_msa

    enable_partial_diff = _extract_bool_setting(
        text,
        ("partial_diff", "enable_partial_diff"),
    )
    if enable_partial_diff is not None:
        tool_args["enable_partial_diff"] = enable_partial_diff

    snr = _extract_float_setting(text, ("snr",))
    if snr is not None:
        tool_args["snr"] = snr

    state_updates = {
        "odesign_input_json_filepath": input_json_path,
        "workspace_files": [input_json_path]
        if created_workspace_file or input_json_path.startswith("workspace/")
        else [],
    }
    return tool_args, state_updates


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


def _resolve_crisot_request(text: str) -> Tuple[str, dict[str, Any], dict[str, Any]]:
    lowered = text.lower()
    csv_path = _extract_path_with_suffixes(text, ("csv",))
    genome_path = _extract_path_with_suffixes(text, ("fa", "fasta", "fna", "fas"))
    threshold = _extract_float_setting(text, ("threshold", "score_threshold", "crisot_threshold"))
    mismatches = _extract_int_setting(text, ("mm", "mismatch", "mismatches"))
    device = _extract_string_setting(text, ("device", "dev"))
    sgrna = _extract_crispr_named_sequence(text, ("sgrna", "sg_rna", "guide", "guide_rna"))
    target_sequence = _extract_crispr_named_sequence(text, ("target", "tar", "off_target", "offtarget"))
    discovered_sequences = _extract_crispr_sequences(text)

    if not sgrna and discovered_sequences:
        sgrna = discovered_sequences[0]
    if not target_sequence:
        for candidate in discovered_sequences:
            if candidate != sgrna:
                target_sequence = candidate
                break
    if not target_sequence and sgrna:
        target_sequence = sgrna

    if _needs_crisot_optimization(lowered):
        if not target_sequence and not sgrna:
            raise ValueError(
                "CRISOT optimization requires one 23-nt target sequence. "
                "Provide it like `target=GAGT...` or include a 23-nt sequence."
            )
        if not genome_path:
            raise ValueError(
                "CRISOT optimization requires a reference genome FASTA path for Cas-OFFinder."
            )
        optimization_target = target_sequence or sgrna
        target_filepath = save_sequence(optimization_target, prefix="crisot_target")
        tool_args: dict[str, Any] = {
            "filepath": target_filepath,
            "genome_path": genome_path,
        }
        if threshold is not None:
            tool_args["threshold"] = threshold
        if mismatches is not None:
            tool_args["mismatches"] = mismatches
        if device:
            tool_args["device"] = device
        state_updates = {
            "current_filepath": target_filepath,
            "crisot_target_sequence": optimization_target,
            "crisot_genome_path": genome_path,
            "workspace_files": [target_filepath],
        }
        return (
            "optimize_sgrna_with_crisot",
            tool_args,
            state_updates,
        )

    if csv_path and any(k in lowered for k in ["spec", "specificity", "specific"]):
        state_updates = {
            "crisot_input_csv_filepath": csv_path,
            "workspace_files": [],
        }
        return (
            "calculate_crispr_specificity_with_crisot",
            {"csv_filepath": csv_path},
            state_updates,
        )

    if not sgrna:
        raise ValueError(
            "CRISOT requires an sgRNA sequence. Provide it like `sgRNA=GAGT...` or include a 23-nt guide sequence."
        )
    if not target_sequence:
        raise ValueError(
            "CRISOT requires a target sequence. Provide it like `target=GAGT...` or include a second 23-nt sequence."
        )

    sgrna_filepath = save_sequence(sgrna, prefix="crisot_sgrna")
    state_updates = {
        "current_filepath": sgrna_filepath,
        "crisot_target_sequence": target_sequence,
        "workspace_files": [sgrna_filepath],
    }

    if genome_path and any(k in lowered for k in ["spec", "specificity", "specific", "genome", "cas-offinder", "casoffinder", "off-spec", "off_spec"]):
        state_updates["crisot_genome_path"] = genome_path
        tool_args = {
            "filepath": sgrna_filepath,
            "target_sequence": target_sequence,
            "genome_path": genome_path,
        }
        if mismatches is not None:
            tool_args["mismatches"] = mismatches
        if device:
            tool_args["device"] = device
        return ("search_crispr_off_targets_with_crisot", tool_args, state_updates)

    return (
        "score_crispr_off_target_with_crisot",
        {
            "filepath": sgrna_filepath,
            "target_sequence": target_sequence,
        },
        state_updates,
    )


def router_node(state: AgentState) -> AgentState:
    """Route by deterministic rules without LLM."""
    user_text = state.get("input_sequence", "").lower()
    if _needs_crispr_mode(user_text):
        route = "crispr_specialist"
    elif _needs_evitar_mode(user_text):
        route = "sirna_specialist"
    elif _needs_iresfinder_prediction(user_text) or any(
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
            "lineardesign",
            "linear design",
            "linearfold",
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
            "odesign",
            "iresfinder",
            "internal ribosome",
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
        else "mrna_design"
        if route == "mrna_specialist"
        else "crispr_analysis"
        if route == "crispr_specialist"
        else "unsupported"
    )
    state["route"] = (
        "sirna"
        if route == "sirna_specialist"
        else "mrna"
        if route == "mrna_specialist"
        else "crispr"
        if route == "crispr_specialist"
        else "unsupported"
    )
    state["messages"] = state.get("messages", []) + [
        AIMessage(content=decision_note)
    ]
    return state


def sirna_specialist_node(state: AgentState) -> AgentState:
    """Emit deterministic siRNA tool calls without LLM."""
    raw_text = state.get("input_sequence", "")
    user_text = raw_text.lower()
    filepath = state.get("current_filepath")
    evitar_mode = _needs_evitar_mode(user_text)
    if not filepath:
        if evitar_mode:
            filepath = _extract_named_filepath(raw_text, ("input", "genome", "virus", "fasta"), ("fa", "fasta", "fna"))
            if not filepath:
                filepath = _extract_path_with_suffixes(raw_text, ("fasta", "fa", "fna", "txt", "seq"))
            if not filepath:
                filepath = save_sequence(_extract_rna_sequence(raw_text), prefix="evitar_input")
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        else:
            filepath = save_sequence(_extract_rna_sequence(raw_text), prefix="sirna")
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        state["current_filepath"] = filepath
    state["active_specialist"] = "sirna_specialist"
    if evitar_mode:
        evitar_args = _build_evitar_tool_args(filepath, raw_text)
        tool_calls = [
            {
                "name": "design_sirna_with_evitar",
                "args": evitar_args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "siRNA specialist (rule-based): dispatch Evitar design."
    else:
        tool_calls = [
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
        ]
        content = "siRNA specialist (rule-based): dispatch tool calls."
    ai_msg = AIMessage(
        content=content,
        tool_calls=tool_calls,
    )
    state["messages"] = state.get("messages", []) + [ai_msg]
    return state


def crispr_specialist_node(state: AgentState) -> AgentState:
    """Emit deterministic CRISPR/CRISOT tool calls without LLM."""
    state["active_specialist"] = "crispr_specialist"
    tool_name, tool_args, state_updates = _resolve_crisot_request(state.get("input_sequence", ""))
    workspace_files = state.get("workspace_files", [])
    extra_workspace_files = state_updates.pop("workspace_files", [])
    state["workspace_files"] = workspace_files + extra_workspace_files
    for key, value in state_updates.items():
        state[key] = value
    ai_msg = AIMessage(
        content="CRISPR specialist (rule-based): dispatch CRISOT tool call.",
        tool_calls=[
            {
                "name": tool_name,
                "args": tool_args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ],
    )
    state["messages"] = state.get("messages", []) + [ai_msg]
    return state


def mrna_specialist_node(state: AgentState) -> AgentState:
    """Emit deterministic mRNA tool calls without LLM."""
    raw_text = state.get("input_sequence", "")
    user_text = raw_text.lower()

    # Defensive fallback: if router misroutes an Evitar request to mRNA,
    # force it back onto the Evitar siRNA tool path.
    if _needs_evitar_mode(user_text):
        filepath = state.get("current_filepath")
        if not filepath:
            filepath = _extract_named_filepath(
                raw_text,
                ("input", "genome", "virus", "fasta"),
                ("fa", "fasta", "fna"),
            )
            if not filepath:
                filepath = _extract_path_with_suffixes(raw_text, ("fasta", "fa", "fna", "txt", "seq"))
            if not filepath:
                filepath = save_sequence(_extract_rna_sequence(raw_text), prefix="evitar_input")
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            state["current_filepath"] = filepath
        evitar_args = _build_evitar_tool_args(filepath, raw_text)
        state["active_specialist"] = "sirna_specialist"
        ai_msg = AIMessage(
            content="mRNA specialist fallback (rule-based): reroute Evitar request to siRNA tool.",
            tool_calls=[
                {
                    "name": "design_sirna_with_evitar",
                    "args": evitar_args,
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "tool_call",
                }
            ],
        )
        state["messages"] = state.get("messages", []) + [ai_msg]
        return state

    state["active_specialist"] = "mrna_specialist"
    odesign_mode = _needs_odesign_mode(user_text)
    gernabind_mode = _needs_gernabind_scoring(user_text)
    rnasmol_mode = _needs_rnasmol_scoring(user_text)
    rnastop_mode = _needs_rnastop_prediction(user_text)
    structure_design_mode = _needs_structure_to_sequence_design(user_text)
    rnarl_mode = _needs_rnarl_design(user_text)
    lineardesign_mode = _needs_lineardesign(user_text)
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

    if odesign_mode:
        tool_args, state_updates = _extract_odesign_request(raw_text)
        extra_workspace_files = state_updates.pop("workspace_files", [])
        state["workspace_files"] = state.get("workspace_files", []) + extra_workspace_files
        for key, value in state_updates.items():
            state[key] = value
        tool_calls = [
            {
                "name": "run_odesign_inference",
                "args": tool_args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch ODesign inference."
    elif gernabind_mode:
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
    elif _needs_iresfinder_prediction(user_text):
        filepath, created_workspace_file = _resolve_rnastop_input(raw_text)
        state["current_filepath"] = filepath
        if created_workspace_file or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_calls = [
            {
                "name": "predict_putative_ires_with_iresfinder",
                "args": _build_iresfinder_tool_args(filepath, raw_text),
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch IRESfinder putative IRES scoring."
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
        if lineardesign_mode:
            tool_name = "design_mrna_cds_with_lineardesign"
        elif rnarl_mode:
            tool_name = "design_mrna_cds_with_rnarl"
        else:
            tool_name = "design_mrna_cds_with_gemorna"
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
            "mRNA specialist (rule-based): dispatch LinearDesign design."
            if lineardesign_mode
            else
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
        linearfold_mode = _needs_linearfold(user_text)
        fold_tool: dict[str, Any] = (
            {
                "name": "predict_rna_secondary_structure_with_linearfold",
                "args": _build_linearfold_tool_args(filepath, raw_text),
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
            if linearfold_mode
            else {
                "name": "predict_rna_secondary_structure",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        )
        tool_calls = [
            {
                "name": "mock_codon_optimization",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            },
            fold_tool,
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
            if _needs_evitar_mode(user_text):
                fallback_calls = [
                    {
                        "name": "design_sirna_with_evitar",
                        "args": _build_evitar_tool_args(filepath, state.get("input_sequence", "")),
                    }
                ]
            else:
                fallback_calls = [
                    {"name": "predict_sirna_efficiency", "args": {"filepath": filepath}},
                    {"name": "check_off_target", "args": {"filepath": filepath}},
                ]
        elif state.get("active_specialist") == "crispr_specialist":
            tool_name, tool_args, state_updates = _resolve_crisot_request(state.get("input_sequence", ""))
            extra_workspace_files = state_updates.pop("workspace_files", [])
            state["workspace_files"] = state.get("workspace_files", []) + extra_workspace_files
            for key, value in state_updates.items():
                state[key] = value
            fallback_calls = [{"name": tool_name, "args": tool_args}]
        elif _needs_odesign_mode(user_text):
            tool_args, state_updates = _extract_odesign_request(state.get("input_sequence", ""))
            extra_workspace_files = state_updates.pop("workspace_files", [])
            state["workspace_files"] = state.get("workspace_files", []) + extra_workspace_files
            for key, value in state_updates.items():
                state[key] = value
            fallback_calls = [
                {
                    "name": "run_odesign_inference",
                    "args": tool_args,
                }
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
        elif _needs_iresfinder_prediction(user_text):
            filepath, created_workspace_file = _resolve_rnastop_input(state.get("input_sequence", ""))
            state["current_filepath"] = filepath
            if created_workspace_file or filepath.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            fallback_calls = [
                {
                    "name": "predict_putative_ires_with_iresfinder",
                    "args": _build_iresfinder_tool_args(filepath, state.get("input_sequence", "")),
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
        elif any(k in user_text for k in ["design", "设计", "gemorna", "rnarl", "lineardesign", "linear design", "protein", "cds", "utr", "生成"]):
            if not filepath:
                filepath = save_sequence(
                    _extract_protein_sequence(state.get("input_sequence", "")),
                    prefix="protein",
                )
                state["current_filepath"] = filepath
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            if _needs_lineardesign(user_text):
                tool_name = "design_mrna_cds_with_lineardesign"
            elif _needs_rnarl_design(user_text):
                tool_name = "design_mrna_cds_with_rnarl"
            else:
                tool_name = "design_mrna_cds_with_gemorna"
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
            linearfold_fb = _needs_linearfold(user_text)
            fold_call: dict[str, Any] = (
                {
                    "name": "predict_rna_secondary_structure_with_linearfold",
                    "args": _build_linearfold_tool_args(filepath, state.get("input_sequence", "")),
                }
                if linearfold_fb
                else {"name": "predict_rna_secondary_structure", "args": {"filepath": filepath}}
            )
            fallback_calls = [
                {"name": "mock_codon_optimization", "args": {"filepath": filepath}},
                fold_call,
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
        elif tool_name == "design_sirna_with_evitar":
            output_filepath = str(tool_result.get("output_filepath", ""))
            if output_filepath:
                state["current_filepath"] = output_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_filepath]
            top_results = tool_result.get("top_results", [])
            if isinstance(top_results, list) and top_results:
                first_row = top_results[0]
                if isinstance(first_row, dict):
                    for key in ("siRNA", "siRNA_sequence", "guide", "guide_sequence", "sequence"):
                        value = first_row.get(key)
                        if isinstance(value, str) and value.strip():
                            state["candidate_sequence"] = value.strip().upper().replace("T", "U")
                            break
            state["evitar_mode"] = str(tool_result.get("mode", ""))
            state["evitar_predict"] = str(tool_result.get("predict", ""))
            state["evitar_output_filepath"] = output_filepath
            state["evitar_result_count"] = int(tool_result.get("result_count", 0))
            state["evitar_command"] = str(tool_result.get("command", ""))
        elif tool_name == "score_crispr_off_target_with_crisot":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
                if input_filepath.startswith("workspace/"):
                    state["workspace_files"] = state.get("workspace_files", []) + [input_filepath]
            state["candidate_sequence"] = str(tool_result.get("sgrna", ""))
            state["crisot_target_sequence"] = str(tool_result.get("target_sequence", ""))
            state["crisot_score"] = float(tool_result.get("crisot_score", 0.0))
        elif tool_name == "calculate_crispr_specificity_with_crisot":
            state["crisot_input_csv_filepath"] = str(tool_result.get("input_csv_filepath", ""))
            state["crisot_spec"] = float(tool_result.get("crisot_spec", 0.0))
            scored_csv_filepath = str(tool_result.get("scored_csv_filepath", ""))
            if scored_csv_filepath:
                state["crisot_output_csv_filepath"] = scored_csv_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [scored_csv_filepath]
        elif tool_name == "search_crispr_off_targets_with_crisot":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
                if input_filepath.startswith("workspace/"):
                    state["workspace_files"] = state.get("workspace_files", []) + [input_filepath]
            state["candidate_sequence"] = str(tool_result.get("sgrna", ""))
            state["crisot_target_sequence"] = str(tool_result.get("target_sequence", ""))
            state["crisot_genome_path"] = str(tool_result.get("genome_path", ""))
            state["crisot_spec"] = float(tool_result.get("crisot_spec", 0.0))
            state["crisot_off_target_count"] = int(tool_result.get("off_target_count", 0))
            scored_csv_filepath = str(tool_result.get("scored_csv_filepath", ""))
            if scored_csv_filepath:
                state["crisot_output_csv_filepath"] = scored_csv_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [scored_csv_filepath]
        elif tool_name == "optimize_sgrna_with_crisot":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
                if input_filepath.startswith("workspace/"):
                    state["workspace_files"] = state.get("workspace_files", []) + [input_filepath]
            state["crisot_target_sequence"] = str(tool_result.get("target_sequence", ""))
            state["crisot_genome_path"] = str(tool_result.get("genome_path", ""))
            state["crisot_optimized_available"] = bool(tool_result.get("optimized_available", False))
            state["crisot_best_mutation"] = str(tool_result.get("best_mutation", ""))
            state["crisot_best_delta_spec"] = float(tool_result.get("best_delta_spec", 0.0))
            state["crisot_score"] = float(tool_result.get("best_crisot_score", 0.0))
            state["crisot_spec"] = float(tool_result.get("best_crisot_spec", 0.0))
            best_sgrna = str(tool_result.get("best_sgrna", ""))
            if best_sgrna:
                state["candidate_sequence"] = best_sgrna
            optimization_csv_filepath = str(tool_result.get("optimization_csv_filepath", ""))
            if optimization_csv_filepath:
                state["crisot_optimization_csv_filepath"] = optimization_csv_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [optimization_csv_filepath]
            optimized_sgrna_filepath = str(tool_result.get("optimized_sgrna_filepath", ""))
            if optimized_sgrna_filepath:
                state["crisot_optimized_sgrna_filepath"] = optimized_sgrna_filepath
                state["current_filepath"] = optimized_sgrna_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [optimized_sgrna_filepath]
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
        elif tool_name == "predict_rna_secondary_structure_with_linearfold":
            if isinstance(tool_result, dict):
                state["mfe"] = float(tool_result.get("mfe", 0.0))
                structure = str(tool_result.get("structure", ""))
                if structure:
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
        elif tool_name in {
            "design_mrna_cds_with_gemorna",
            "design_mrna_cds_with_rnarl",
            "design_mrna_cds_with_lineardesign",
        }:
            output_filepath = str(tool_result.get("output_filepath", ""))
            if output_filepath:
                state["current_filepath"] = output_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_filepath]
            state["candidate_sequence"] = str(tool_result.get("generated_sequence", ""))
            state["design_model"] = str(tool_result.get("model", ""))
            state["rnarl_model_type"] = str(tool_result.get("model_type", ""))
            state["rnarl_checkpoint_path"] = str(tool_result.get("checkpoint_path", ""))
            state["rnarl_esm2_model_path"] = str(tool_result.get("esm2_model_path", ""))
            if "cai_score" in tool_result:
                state["cai_score"] = float(tool_result.get("cai_score", 0.0))
            if "mfe" in tool_result:
                state["mfe"] = float(tool_result.get("mfe", 0.0))
            structure = str(tool_result.get("structure", ""))
            if structure:
                structure_filepath = save_sequence(structure, prefix="structure")
                state["structure_filepath"] = structure_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [structure_filepath]

            user_text = state.get("input_sequence", "").lower()
            raw_user = state.get("input_sequence", "")
            if _needs_secondary_structure(user_text):
                if _needs_linearfold(user_text):
                    lf_args = _build_linearfold_tool_args(state["current_filepath"], raw_user)
                    fold_result = predict_rna_secondary_structure_with_linearfold.invoke(lf_args)
                    fold_msg_name = "predict_rna_secondary_structure_with_linearfold"
                else:
                    fold_result = predict_rna_secondary_structure.invoke({"filepath": state["current_filepath"]})
                    fold_msg_name = "predict_rna_secondary_structure"
                out_messages.append(
                    ToolMessage(
                        content=json.dumps(fold_result, ensure_ascii=True),
                        tool_call_id=f"call_{uuid.uuid4().hex[:8]}",
                        name=fold_msg_name,
                    )
                )
                if isinstance(fold_result, dict):
                    state["mfe"] = float(fold_result.get("mfe", 0.0))
                    structure = str(fold_result.get("structure", ""))
                    if structure:
                        structure_filepath = save_sequence(structure, prefix="structure")
                        state["structure_filepath"] = structure_filepath
                        state["workspace_files"] = state.get("workspace_files", []) + [structure_filepath]
                else:
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
        elif tool_name == "predict_putative_ires_with_iresfinder":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
            result_tsv = str(tool_result.get("result_tsv_filepath", ""))
            if result_tsv:
                state["iresfinder_result_tsv_filepath"] = result_tsv
                state["workspace_files"] = state.get("workspace_files", []) + [result_tsv]
            state["iresfinder_has_putative_ires"] = bool(tool_result.get("has_putative_ires", False))
            state["iresfinder_max_score"] = float(tool_result.get("max_score", 0.0))
            state["iresfinder_best_fragment_id"] = str(tool_result.get("best_fragment_id", ""))
            state["iresfinder_positive_count"] = int(tool_result.get("positive_count", 0))
            state["iresfinder_fragment_count"] = int(tool_result.get("fragment_count", 0))
            state["iresfinder_model"] = str(tool_result.get("model", ""))
        elif tool_name == "run_odesign_inference":
            state["odesign_input_json_filepath"] = str(tool_result.get("input_json_filepath", ""))
            state["odesign_output_dir"] = str(tool_result.get("output_dir", ""))
            state["odesign_model_name"] = str(tool_result.get("infer_model_name", ""))
            state["odesign_design_modality"] = str(tool_result.get("design_modality", ""))
            prediction_filepaths = [
                str(path) for path in tool_result.get("prediction_filepaths", []) if str(path)
            ]
            if prediction_filepaths:
                state["odesign_prediction_filepaths"] = prediction_filepaths
                state["workspace_files"] = state.get("workspace_files", []) + prediction_filepaths
            run_log_filepath = str(tool_result.get("run_log_filepath", ""))
            if run_log_filepath:
                state["odesign_run_log_filepath"] = run_log_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [run_log_filepath]
            stdout_filepath = str(tool_result.get("stdout_filepath", ""))
            if stdout_filepath:
                state["workspace_files"] = state.get("workspace_files", []) + [stdout_filepath]
            stderr_filepath = str(tool_result.get("stderr_filepath", ""))
            if stderr_filepath:
                state["workspace_files"] = state.get("workspace_files", []) + [stderr_filepath]
            error_filepaths = [
                str(path) for path in tool_result.get("error_filepaths", []) if str(path)
            ]
            if error_filepaths:
                state["workspace_files"] = state.get("workspace_files", []) + error_filepaths

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
        and not _needs_iresfinder_prediction(user_text)
        and not _needs_structure_to_sequence_design(user_text)
        and any(
            k in user_text
            for k in ["structure", "fold", "rnafold", "二级结构", "linearfold"]
        )
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
            f"crisot_score={state.get('crisot_score', 0.0)}; "
            f"crisot_spec={state.get('crisot_spec', 0.0)}; "
            f"crisot_target_sequence={state.get('crisot_target_sequence', '')}; "
            f"crisot_input_csv_filepath={state.get('crisot_input_csv_filepath', '')}; "
            f"crisot_output_csv_filepath={state.get('crisot_output_csv_filepath', '')}; "
            f"crisot_genome_path={state.get('crisot_genome_path', '')}; "
            f"crisot_off_target_count={state.get('crisot_off_target_count', 0)}; "
            f"crisot_optimization_csv_filepath={state.get('crisot_optimization_csv_filepath', '')}; "
            f"crisot_optimized_sgrna_filepath={state.get('crisot_optimized_sgrna_filepath', '')}; "
            f"crisot_best_mutation={state.get('crisot_best_mutation', '')}; "
            f"crisot_best_delta_spec={state.get('crisot_best_delta_spec', 0.0)}; "
            f"crisot_optimized_available={state.get('crisot_optimized_available', False)}; "
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
            f"iresfinder_result_tsv_filepath={state.get('iresfinder_result_tsv_filepath', '')}; "
            f"iresfinder_has_putative_ires={state.get('iresfinder_has_putative_ires', False)}; "
            f"iresfinder_max_score={state.get('iresfinder_max_score', 0.0)}; "
            f"iresfinder_best_fragment_id={state.get('iresfinder_best_fragment_id', '')}; "
            f"iresfinder_positive_count={state.get('iresfinder_positive_count', 0)}; "
            f"iresfinder_fragment_count={state.get('iresfinder_fragment_count', 0)}; "
            f"iresfinder_model={state.get('iresfinder_model', '')}; "
            f"odesign_input_json_filepath={state.get('odesign_input_json_filepath', '')}; "
            f"odesign_output_dir={state.get('odesign_output_dir', '')}; "
            f"odesign_prediction_filepaths={state.get('odesign_prediction_filepaths', [])}; "
            f"odesign_run_log_filepath={state.get('odesign_run_log_filepath', '')}; "
            f"odesign_model_name={state.get('odesign_model_name', '')}; "
            f"odesign_design_modality={state.get('odesign_design_modality', '')}; "
            f"evitar_mode={state.get('evitar_mode', '')}; "
            f"evitar_predict={state.get('evitar_predict', '')}; "
            f"evitar_output_filepath={state.get('evitar_output_filepath', '')}; "
            f"evitar_result_count={state.get('evitar_result_count', 0)}; "
            f"evitar_command={state.get('evitar_command', '')}; "
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
    if state.get("route") == "crispr":
        return "crispr_specialist"
    return "end"


def route_after_critic(state: AgentState) -> str:
    """Choose whether to retry or finish."""
    if state.get("next_action") != "retry":
        return "end"
    return state.get("active_specialist", "sirna_specialist")
