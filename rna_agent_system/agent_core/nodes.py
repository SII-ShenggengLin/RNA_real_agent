"""Node implementations for the RNA Design multi-agent workflow graph."""

from __future__ import annotations

import json
from pathlib import Path
import re
import uuid
from typing import Any, Optional, Tuple

from langchain_core.messages import AIMessage, ToolMessage

from agent_core.file_manager import read_sequence, save_sequence, save_text_file
from agent_core.state import AgentState
from agent_core.tool_specs import TOOL_SPECS
from agent_core.tools import (
    ALL_LANGCHAIN_AGENT_TOOLS,
    calculate_crispr_specificity_with_crisot,
    compute_aso_target_accessibility_vienna,
    predict_rna_local_accessibility_profile_vienna,
    compute_sirna_duplex_binding_vienna,
    design_sgrna_handle_with_crgpt,
    design_sirna_with_evitar,
    design_mrna_cds_with_lineardesign,
    design_rna_sequence_with_rhodesign,
    design_rna_inverse_fold_with_ribodiffusion,
    design_mrna_cds_with_gemorna,
    design_mrna_cds_with_rnarl,
    inverse_fold_rna_secondary_structure_vienna,
    analyze_cds_codon_metrics_with_codonw_slim,
    compute_rna_sequence_gc_content,
    compute_dot_bracket_unpaired_fraction,
    optimize_sgrna_with_crisot,
    run_blastn_similarity_search,
    predict_mrna_stability_with_rnastop,
    predict_putative_ires_with_iresfinder,
    predict_rna_secondary_structure,
    predict_rna_secondary_structure_with_linearfold,
    predict_rna_tertiary_structure_with_rhofold,
    run_odesign_inference,
    score_crispr_off_target_with_crisot,
    search_crispr_off_targets_with_crisot,
    score_rna_ligand_binding_with_gernabind,
    score_rna_ligand_binding_with_rnasmol,
)

TOOLS = ALL_LANGCHAIN_AGENT_TOOLS
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


def _needs_sirna_duplex_vienna(user_text: str) -> bool:
    keys = (
        "duplex",
        "rnacofold",
        "rna cofold",
        "双链",
        "正反义",
        "sense/antisense",
        "sense and antisense",
        "guide strand",
        "passenger strand",
        "sirna binding energy",
        "sirna duplex",
        "结合能",
    )
    return any(k in user_text for k in keys)


def _needs_codonw_standalone(user_text: str) -> bool:
    """Explicit codonw-slim / codon-usage analysis without default fold-first path."""
    lowered = user_text.lower()
    if "codonw-slim" in lowered or "codonw slim" in lowered:
        return True
    if re.search(r"\bcodonw\b", lowered):
        return True
    if "codon usage" in lowered or "codon metrics" in lowered:
        return True
    if ("密码子" in user_text) and any(
        x in user_text for x in ("分析", "指标", "偏好", "cai", "CAI", "Nc", "ENC", "enc", "fop", "Fop", "cbi")
    ):
        return True
    return False


def _needs_rna_gc_content_metric(user_text: str) -> bool:
    """Explicit GC-content / (G+C) fraction request (not generic sequence design)."""
    lowered = user_text.lower()
    if "gc含量" in user_text or "gc 含量" in user_text:
        return True
    if "gc content" in lowered or "gc-content" in lowered:
        return True
    if re.search(r"\bgc\s*%\b", lowered):
        return True
    if ("g+c" in lowered or "g + c" in lowered) and any(
        x in lowered for x in ("fraction", "content", "ratio", "percent", "proportion")
    ):
        return True
    if ("g+c" in lowered or "g + c" in lowered) and ("比例" in user_text or "含量" in user_text):
        return True
    if "碱基gc" in user_text or "gc比例" in user_text:
        return True
    return False


def _needs_dot_bracket_unpaired_fraction_metric(user_text: str) -> bool:
    """Dot-bracket '.' / length (unpaired fraction) from a secondary structure string or file."""
    lowered = user_text.lower()
    if "未配对" in user_text and any(x in user_text for x in ("比例", "分数", "占比", "率")):
        return True
    if "未配对" in user_text and any(
        k in lowered for k in ("fraction", "ratio", "proportion", "dot-bracket", "dot bracket")
    ):
        return True
    if "unpaired fraction" in lowered or "unpaired ratio" in lowered or "unpaired proportion" in lowered:
        return True
    if "dot fraction" in lowered or "dot-bracket" in lowered or "dot bracket" in lowered:
        return True
    if "点的比例" in user_text or "点括号" in user_text:
        return True
    return False


def _resolve_dot_bracket_structure_filepath(raw_text: str) -> Tuple[str, bool]:
    """Return (filepath, created_workspace_file) for a dot-bracket structure."""
    fp = _extract_path_with_suffixes(raw_text, ("ss", "struct", "dbn", "txt"))
    if fp:
        read_sequence(fp)
        return fp, False

    struct_m = re.search(
        r"(?:structure|dot[- ]?bracket|dbn|ss)\s*[:=]\s*[\"']?([.()[\]{}<>]+)[\"']?",
        raw_text,
        flags=re.IGNORECASE,
    )
    if struct_m:
        content = struct_m.group(1).strip() + "\n"
        return save_text_file(content, prefix="dotbracket_in", suffix=".txt"), True

    raise ValueError(
        "Unpaired fraction needs a dot-bracket structure file (.ss/.struct/.dbn/.txt) under workspace/, "
        "or inline `structure=(((...)))` / `dot-bracket=...` in the request."
    )


def _build_codonw_tool_args(filepath: str, raw_text: str) -> dict[str, Any]:
    args: dict[str, Any] = {"filepath": filepath}
    gc_m = re.search(r"genetic_code\s*[:=]\s*(\d+)", raw_text, flags=re.IGNORECASE)
    if gc_m:
        args["genetic_code"] = max(0, min(7, int(gc_m.group(1))))
    cai_m = re.search(r"cai_ref\s*[:=]\s*(\d+)", raw_text, flags=re.IGNORECASE)
    if cai_m:
        args["cai_ref"] = max(0, min(2, int(cai_m.group(1))))
    fop_m = re.search(r"fop_ref\s*[:=]\s*(\d+)", raw_text, flags=re.IGNORECASE)
    if fop_m:
        args["fop_ref"] = max(0, min(7, int(fop_m.group(1))))
    if re.search(r"factor_in_rare\s*[:=]\s*(1|true|yes)\b", raw_text, flags=re.IGNORECASE):
        args["factor_in_rare"] = True
    if re.search(
        r"include_codon_tables|codon\s*table|full\s*rscu|rscu\s*table",
        raw_text,
        flags=re.IGNORECASE,
    ):
        args["include_codon_tables"] = True
    if re.search(r"dinuc|dinucleotide", raw_text, flags=re.IGNORECASE):
        args["include_dinucleotide"] = True
    return args


def _needs_aso_region_plfold_accessibility(raw_text: str) -> bool:
    """ASO / explicit binding region + RNAplfold-style accessibility (region summary tool)."""
    u = raw_text.lower()
    if any(k in u for k in ("aso", "gapmer", "morpholino", "antisense oligo")):
        return True
    if "binding site accessibility" in u:
        return True
    rs, _re = _extract_aso_region_bounds(raw_text)
    if rs is not None and any(
        k in u for k in ("accessibility", "可及性", "plfold", "rnaplfold", "rna plfold", "lunp")
    ):
        return True
    if any(k in raw_text for k in ("结合区域", "靶区")) and any(
        k in u for k in ("accessibility", "可及性", "plfold", "rnaplfold", "lunp")
    ):
        return True
    return False


def _needs_rna_plfold_local_profile(raw_text: str) -> bool:
    """Whole-sequence RNAplfold (``RNAplfold``) local unpaired probability profile (not ASO-only summary)."""
    if _needs_aso_region_plfold_accessibility(raw_text):
        return False
    u = raw_text.lower()
    cn_markers = (
        "局部结构",
        "局部折叠",
        "可及性曲线",
        "位点可及性",
        "滑动窗口",
        "每个碱基",
        "逐位点",
    )
    if any(k in raw_text for k in cn_markers):
        return True
    en_markers = (
        "local structure",
        "local folding",
        "lunp",
        "accessibility profile",
        "unpaired profile",
        "sliding window",
        "per-nucleotide",
        "per nucleotide",
    )
    if any(k in u for k in en_markers):
        return True
    if any(k in u for k in ("rnaplfold", "rna plfold")):
        return True
    if "plfold" in u:
        return True
    if "accessibility" in u or "可及性" in raw_text:
        return True
    if "unpaired probability" in u:
        return True
    return False


def _needs_inverse_fold_vienna(user_text: str) -> bool:
    keys = (
        "inverse fold",
        "inverse-fold",
        "inverse_folding",
        "逆折叠",
        "rnainverse",
        "rna inverse",
        "序列逆推",
    )
    return any(k in user_text for k in keys)


def _extract_aso_region_bounds(text: str) -> Tuple[Optional[int], Optional[int]]:
    patterns = (
        r"(?:region|aso|target)[_-]?(?:region|site)?\s*[:=]\s*(\d+)\s*[-～~,]\s*(\d+)",
        r"(?:start|begin)\s*[:=]\s*(\d+).*?(?:end|stop)\s*[:=]\s*(\d+)",
    )
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            return int(m.group(1)), int(m.group(2))
    m2 = re.search(r"\b(\d{1,7})\s*[-～~]\s*(\d{1,7})\b", text)
    if m2:
        return int(m2.group(1)), int(m2.group(2))
    return None, None


def _normalize_plain_rna_from_text(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith(">")]
    merged = "".join(lines).upper().replace("T", "U")
    return "".join(ch for ch in merged if ch in "AUGC")


def _parse_two_lines_for_duplex_check(body: str) -> bool:
    if body.count(">") >= 2:
        return True
    lines = [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.lstrip().startswith(">")]
    if len(lines) < 2:
        return False
    return all(
        len("".join(c for c in ln.upper().replace("T", "U") if c in "AUGC")) >= 8 for ln in lines[:2]
    )


def _ensure_duplex_fasta_workspace_path(raw_text: str, filepath: Optional[str]) -> str:
    """Return workspace path with two FASTA records (sense then antisense)."""
    sense_m = re.search(
        r"(?:sense|guide|链1|正链)\s*[:=]\s*[\"']?([ACGUTacgut]{8,})[\"']?",
        raw_text,
        flags=re.IGNORECASE,
    )
    anti_m = re.search(
        r"(?:antisense|antis|passenger|反义|链2)\s*[:=]\s*[\"']?([ACGUTacgut]{8,})[\"']?",
        raw_text,
        flags=re.IGNORECASE,
    )
    if sense_m and anti_m:
        sense = sense_m.group(1).upper().replace("T", "U")
        anti = anti_m.group(1).upper().replace("T", "U")
        content = f">sense\n{sense}\n>antisense\n{anti}\n"
        return save_sequence(content, prefix="sirna_duplex")

    if filepath:
        try:
            body = read_sequence(filepath)
            if body.count(">") >= 2 or _parse_two_lines_for_duplex_check(body):
                return filepath
        except OSError:
            pass

    long_seq = _extract_long_rna_sequence(raw_text)
    if long_seq and len(long_seq) >= 16:
        half = len(long_seq) // 2
        sense = long_seq[:half]
        anti = long_seq[half:]
        content = f">sense\n{sense}\n>antisense\n{anti}\n"
        return save_sequence(content, prefix="sirna_duplex_split")

    raise ValueError(
        "Duplex mode needs two strands: use FASTA (two records) in a file, or "
        "`sense=...` / `antisense=...` in the request, or one long RNA split heuristically."
    )


def _ensure_inverse_fold_structure_file(raw_text: str, filepath: Optional[str]) -> str:
    struct_m = re.search(
        r"(?:structure|dot[- ]?bracket|dbn)\s*[:=]\s*[\"']?([.()[\]{}<>]+)[\"']?",
        raw_text,
        flags=re.IGNORECASE,
    )
    hint_m = re.search(
        r"(?:start|hint|constraint)\s*[:=]\s*[\"']?([ACGUTNacgutn]+)[\"']?",
        raw_text,
        flags=re.IGNORECASE,
    )
    if struct_m:
        lines = [struct_m.group(1).strip()]
        if hint_m:
            lines.append(hint_m.group(1).strip())
        content = "\n".join(lines) + "\n"
        return save_text_file(content, prefix="inverse_fold_in", suffix=".txt")

    if filepath:
        try:
            body = read_sequence(filepath).strip()
            if body:
                return filepath
        except OSError:
            pass

    raise ValueError(
        "Inverse fold needs a dot-bracket structure: put it in a .txt file (first line), "
        "or write `structure=(((...)))` in the request."
    )


def _rna_sequence_length_from_workspace(filepath: str) -> int:
    raw = read_sequence(filepath)
    return len(_normalize_plain_rna_from_text(raw))


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


def _extract_sgrna_seed_sequence(text: str) -> Optional[str]:
    """Extract sgRNA-handle seed/template sequence (typically 40-120 nt)."""
    pattern = re.compile(
        r"""(?:seed|template|handle|wildtype|wild_type)\s*[:=]\s*["']?([ACGUTacgut]{40,140})["']?""",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        return match.group(1).strip().upper().replace("U", "T")

    candidates = re.findall(r"[ACGUTacgut]{40,140}", text)
    if not candidates:
        return None
    return max(candidates, key=len).upper().replace("U", "T")


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
            "sgrna handle",
            "sgrna design",
            "crgpt",
            "sgrna_design",
            "guide rna",
            "guide-rna",
            "off-spec",
            "off_spec",
        ]
    )


def _needs_sgrna_handle_design(text: str) -> bool:
    return any(
        k in text
        for k in [
            "sgrna handle",
            "handle design",
            "sgrna design",
            "crgpt",
            "sgrna_design",
            "design sgrna",
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


def _needs_ribodiffusion_design(text: str) -> bool:
    lowered = text.lower()
    return any(
        k in lowered
        for k in [
            "ribodiffusion",
            "ribo diffusion",
            "ribo-diffusion",
            "inverse folding diffusion",
            "diffusion inverse fold",
            "扩散逆折叠",
            "结构扩散逆折叠",
        ]
    )


def _build_ribodiffusion_tool_args(raw_text: str) -> dict[str, Any]:
    pdb_path = _extract_path_with_suffixes(raw_text, ("pdb", "cif"))
    if not pdb_path:
        pdb_path = "rna_agent_system/external_repos/RiboDiffusion/example/R1107.pdb"
    args: dict[str, Any] = {"pdb_filepath": pdb_path}
    ns = _extract_int_setting(raw_text, ("n_samples", "samples", "num_samples"))
    if ns is not None and ns > 0:
        args["n_samples"] = ns
    steps = _extract_int_setting(raw_text, ("sampling_steps", "diffusion_steps"))
    if steps is not None and steps > 0:
        args["sampling_steps"] = steps
    cs = _extract_float_setting(raw_text, ("cond_scale", "guidance_scale"))
    if cs is not None:
        args["cond_scale"] = cs
    dt = _extract_bool_setting(raw_text, ("dynamic_threshold",))
    if dt is not None:
        args["dynamic_threshold"] = dt
    det = _extract_bool_setting(raw_text, ("deterministic",))
    if det is not None:
        args["deterministic"] = det
    dev = _extract_int_setting(raw_text, ("cuda_device", "gpu_id"))
    if dev is not None and dev >= 0:
        args["device"] = dev
    return args


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


def _needs_5utr_design(text: str) -> bool:
    lowered = text.lower()
    return "5utr" in lowered or "5'utr" in lowered or "5 utr" in lowered


def _needs_3utr_design(text: str) -> bool:
    lowered = text.lower()
    return "3utr" in lowered or "3'utr" in lowered or "3 utr" in lowered


def _extract_utr_length(text: str) -> str:
    lowered = text.lower()
    if "short" in lowered:
        return "short"
    if "long" in lowered:
        return "long"
    return "medium"


def _resolve_utr_tool(user_text: str) -> tuple[str, dict[str, Any]]:
    """Resolve UTR design tool name and args (GEMORNA 5'UTR / 3'UTR)."""
    if _needs_5utr_design(user_text):
        return "design_5utr_with_gemorna", {}
    return "design_3utr_with_gemorna", {}


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
    """Resolve protein-to-CDS design model type from natural language.

    INTERFACE LOCK (v0.2.0): The 7 returned strings are the canonical
    model_type values accepted by RNARL. They must match
    microservices/rnarl_service/main.py :: MODEL_TYPE_TO_CHECKPOINT exactly.
    """
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


def _resolve_protein_to_cds_tool(user_text: str, raw_text: str) -> tuple[str, dict[str, Any]]:
    """Resolve protein-to-CDS design tool name and args (LinearDesign / RNARL / GEMORNA).

    INTERFACE LOCK (v0.2.0): The dispatch logic and RNARL model_type extraction
    must stay in sync with docs/tools/design_mrna_cds_with_rnarl.md.
    """
    if _needs_lineardesign(user_text):
        tool_name = "design_mrna_cds_with_lineardesign"
    elif _needs_rnarl_design(user_text):
        tool_name = "design_mrna_cds_with_rnarl"
    else:
        tool_name = "design_mrna_cds_with_gemorna"
    tool_args: dict[str, Any] = {}
    if tool_name == "design_mrna_cds_with_rnarl":
        tool_args["model_type"] = _extract_rnarl_model_type(raw_text)
    return tool_name, tool_args


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


def _needs_blast_search(user_text: str) -> bool:
    lowered = user_text.lower()
    return any(
        k in lowered
        for k in (
            "blast",
            "blastn",
            "megablast",
            "dc-megablast",
            "相似性搜索",
        )
    )


def _extract_blast_path_token(text: str, labels: Tuple[str, ...]) -> Optional[str]:
    joined = "|".join(re.escape(lbl) for lbl in labels)
    pattern = re.compile(rf"(?:{joined})\s*[:=]\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    pattern2 = re.compile(rf"(?:{joined})\s*[:=]\s*(\S+)", re.IGNORECASE)
    m2 = pattern2.search(text)
    if m2:
        return m2.group(1).strip().strip(",").strip(";")
    return None


def _build_blast_tool_args(filepath: str, raw_text: str) -> dict[str, Any]:
    """Resolve blastn tool kwargs from natural language (subject FASTA or BLAST DB prefix)."""
    lowered = raw_text.lower()
    args: dict[str, Any] = {"filepath": filepath}

    subject_db = _extract_blast_path_token(
        raw_text,
        ("subject_db", "blast_db", "blastdb", "database"),
    )
    subject_fasta = _extract_blast_path_token(
        raw_text,
        ("subject_fasta", "subject", "target_fasta"),
    )
    if not subject_fasta:
        subject_fasta = _extract_named_filepath(
            raw_text,
            ("subject", "subject_fasta", "target"),
            ("fa", "fasta", "fna", "fas"),
        )

    if subject_db:
        args["subject_db"] = subject_db
    elif subject_fasta:
        args["subject_fasta_path"] = subject_fasta
    else:
        raise ValueError(
            "BLAST search needs a subject. Provide `subject_fasta=/path/to.fa` or `subject_db=/path/to/db_prefix` "
            "(existing nucleotide BLAST database)."
        )

    if "megablast" in lowered or "dc-megablast" in lowered or "dc_megablast" in lowered:
        args["task"] = "dc-megablast" if "dc" in lowered else "megablast"
    elif "blastn-short" in lowered or "short" in lowered and "blast" in lowered:
        args["task"] = "blastn-short"
    elif "blastn" in lowered:
        args["task"] = "blastn"

    ev = _extract_float_setting(raw_text, ("evalue", "e-value", "e_value"))
    if ev is not None and ev > 0:
        args["evalue"] = ev
    ws = _extract_int_setting(raw_text, ("word_size", "wordsize"))
    if ws is not None and ws > 0:
        args["word_size"] = ws
    mts = _extract_int_setting(raw_text, ("max_target_seqs", "maxtargetseqs", "max_hits"))
    if mts is not None and mts > 0:
        args["max_target_seqs"] = mts
    pid = _extract_float_setting(raw_text, ("perc_identity", "pident", "identity"))
    if pid is not None and pid > 0:
        args["perc_identity"] = pid
    if "strand=plus" in lowered or "strand plus" in lowered:
        args["strand"] = "plus"
    elif "strand=minus" in lowered or "strand minus" in lowered:
        args["strand"] = "minus"
    return args


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


def _resolve_sgrna_design_request(text: str) -> Tuple[dict[str, Any], dict[str, Any]]:
    raw_sequence = _extract_sgrna_seed_sequence(text)
    if not raw_sequence:
        filepath_candidate = _extract_path_with_suffixes(text, ("fasta", "fa", "txt", "seq"))
    else:
        filepath_candidate = None

    workspace_files: list[str] = []
    if filepath_candidate:
        seed_filepath = filepath_candidate
    else:
        if not raw_sequence:
            discovered = _extract_crispr_sequences(text)
            raw_sequence = discovered[0] if discovered else (
                "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG"
            )
        seed_filepath = save_sequence(raw_sequence, prefix="sgrna_seed")
        workspace_files.append(seed_filepath)

    tool_args: dict[str, Any] = {"filepath": seed_filepath}
    n_samples = _extract_int_setting(text, ("n_samples", "samples", "num_samples"))
    if n_samples is not None and n_samples > 0:
        tool_args["n_samples"] = n_samples
    mutation_number = _extract_int_setting(
        text,
        ("mutation_number", "mutation", "mutations", "mut_num"),
    )
    if mutation_number is not None and mutation_number > 0:
        tool_args["mutation_number"] = mutation_number
    max_overlap = _extract_int_setting(text, ("max_overlap", "overlap"))
    if max_overlap is not None and max_overlap > 0:
        tool_args["max_overlap"] = max_overlap
    temperature = _extract_float_setting(text, ("temperature", "temp"))
    if temperature is not None and temperature > 0:
        tool_args["temperature"] = temperature
    device = _extract_string_setting(text, ("device", "torch_device", "dev"))
    if device:
        tool_args["device"] = device

    state_updates = {
        "current_filepath": seed_filepath,
        "workspace_files": workspace_files,
    }
    return tool_args, state_updates


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
    elif _needs_iresfinder_prediction(user_text) or _needs_blast_search(user_text) or any(
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
            "ribodiffusion",
            "ribo diffusion",
            "二级结构",
            "密码子",
            "codon",
            "codonw",
            "codonw-slim",
            "codon bias",
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
            "aso",
            "gapmer",
            "morpholino",
            "accessibility",
            "可及性",
            "plfold",
            "rnaplfold",
            "lunp",
            "局部结构",
            "local structure",
            "local folding",
            "sliding window",
            "滑动窗口",
            "inverse fold",
            "逆折叠",
            "rnainverse",
            "gc content",
            "gc含量",
            "unpaired fraction",
            "未配对比例",
            "dot-bracket",
            "dot bracket",
        ]
    ):
        route = "mrna_specialist"
    elif _needs_sirna_duplex_vienna(user_text):
        route = "sirna_specialist"
    elif any(k in user_text for k in ["sirna", "脱靶", "off-target"]):
        route = "end"
        state["final_report"] = (
            "Unsupported request: siRNA efficiency/off-target capability was previously provided by mock services "
            "(ports 8001/8002) and has been removed. No production implementation is available in this repository. "
            "Supported siRNA-related tasks: Evitar design and ViennaRNA duplex energy."
        )
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
    duplex_mode = _needs_sirna_duplex_vienna(user_text) and not evitar_mode
    if not filepath:
        if evitar_mode:
            filepath = _extract_named_filepath(raw_text, ("input", "genome", "virus", "fasta"), ("fa", "fasta", "fna"))
            if not filepath:
                filepath = _extract_path_with_suffixes(raw_text, ("fasta", "fa", "fna", "txt", "seq"))
            if not filepath:
                filepath = save_sequence(_extract_rna_sequence(raw_text), prefix="evitar_input")
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        elif not duplex_mode:
            filepath = save_sequence(_extract_rna_sequence(raw_text), prefix="sirna")
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        if filepath:
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
    elif duplex_mode:
        try:
            duplex_fp = _ensure_duplex_fasta_workspace_path(raw_text, filepath)
        except ValueError as exc:
            ai_msg = AIMessage(
                content=(
                    "siRNA duplex specialist: could not build sense/antisense input for ViennaRNA cofold. "
                    f"Detail: {exc}"
                ),
                tool_calls=[],
            )
            state["messages"] = state.get("messages", []) + [ai_msg]
            return state
        state["current_filepath"] = duplex_fp
        if duplex_fp.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [duplex_fp]
        tool_calls = [
            {
                "name": "compute_sirna_duplex_binding_vienna",
                "args": {"filepath": duplex_fp},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "siRNA specialist (rule-based): ViennaRNA sense/antisense duplex (cofold) energy."
    else:
        tool_calls = []
        content = (
            "siRNA specialist (rule-based): unsupported request. "
            "siRNA efficiency/off-target mock services were removed; "
            "no production implementation is available in this repository."
        )
    ai_msg = AIMessage(
        content=content,
        tool_calls=tool_calls,
    )
    state["messages"] = state.get("messages", []) + [ai_msg]
    return state


def crispr_specialist_node(state: AgentState) -> AgentState:
    """Emit deterministic CRISPR/CRISOT tool calls without LLM."""
    state["active_specialist"] = "crispr_specialist"
    user_text = state.get("input_sequence", "")
    lowered = user_text.lower()
    if _needs_sgrna_handle_design(lowered):
        tool_args, state_updates = _resolve_sgrna_design_request(user_text)
        tool_name = "design_sgrna_handle_with_crgpt"
    else:
        tool_name, tool_args, state_updates = _resolve_crisot_request(user_text)
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
    ribodiffusion_mode = _needs_ribodiffusion_design(user_text)
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
    elif _needs_inverse_fold_vienna(user_text):
        inv_fp = _ensure_inverse_fold_structure_file(raw_text, state.get("current_filepath"))
        state["current_filepath"] = inv_fp
        if inv_fp.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [inv_fp]
        rep_m = re.search(r"repeats?\s*[:=]\s*(\d+)", raw_text, flags=re.IGNORECASE)
        repeats = int(rep_m.group(1)) if rep_m else 1
        tool_calls = [
            {
                "name": "inverse_fold_rna_secondary_structure_vienna",
                "args": {"filepath": inv_fp, "repeats": repeats},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): ViennaRNA RNAinverse secondary-structure inverse fold."
    elif _needs_aso_region_plfold_accessibility(raw_text):
        filepath_aso, created_workspace_file = _resolve_rnastop_input(raw_text)
        state["current_filepath"] = filepath_aso
        if created_workspace_file or filepath_aso.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath_aso]
        nlen = _rna_sequence_length_from_workspace(filepath_aso)
        rs, re_aso = _extract_aso_region_bounds(raw_text)
        if rs is None or re_aso is None:
            rs, re_aso = 1, min(20, nlen)
        rs = max(1, min(rs, nlen))
        re_aso = max(rs, min(re_aso, nlen))
        tool_calls = [
            {
                "name": "compute_aso_target_accessibility_vienna",
                "args": {"filepath": filepath_aso, "region_start": rs, "region_end": re_aso},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): ViennaRNA RNAplfold ASO / binding-site accessibility."
    elif _needs_rna_plfold_local_profile(raw_text):
        filepath_pf, created_workspace_file = _resolve_rnastop_input(raw_text)
        state["current_filepath"] = filepath_pf
        if created_workspace_file or filepath_pf.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath_pf]
        tool_calls = [
            {
                "name": "predict_rna_local_accessibility_profile_vienna",
                "args": {"filepath": filepath_pf},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): ViennaRNA RNAplfold full-sequence local accessibility profile."
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
    elif _needs_codonw_standalone(raw_text):
        filepath, created_workspace_file = _resolve_rnastop_input(raw_text)
        state["current_filepath"] = filepath
        if created_workspace_file or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_calls = [
            {
                "name": "analyze_cds_codon_metrics_with_codonw_slim",
                "args": _build_codonw_tool_args(filepath, raw_text),
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch codonw-slim CDS codon metrics."
    elif _needs_rna_gc_content_metric(user_text):
        filepath, created_workspace_file = _resolve_rnastop_input(raw_text)
        state["current_filepath"] = filepath
        if created_workspace_file or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        tool_calls = [
            {
                "name": "compute_rna_sequence_gc_content",
                "args": {"filepath": filepath},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): RNA sequence GC content (G+C)/N."
    elif _needs_dot_bracket_unpaired_fraction_metric(user_text):
        try:
            ss_fp, created_ss = _resolve_dot_bracket_structure_filepath(raw_text)
        except ValueError as exc:
            ai_msg = AIMessage(
                content=f"mRNA specialist (unpaired fraction): {exc}",
                tool_calls=[],
            )
            state["messages"] = state.get("messages", []) + [ai_msg]
            return state
        state["current_filepath"] = ss_fp
        if created_ss or ss_fp.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [ss_fp]
        tool_calls = [
            {
                "name": "compute_dot_bracket_unpaired_fraction",
                "args": {"filepath": ss_fp},
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dot-bracket unpaired fraction (dot count / length)."
    elif _needs_blast_search(user_text):
        filepath, created_workspace_file = _resolve_rnastop_input(raw_text)
        state["current_filepath"] = filepath
        if created_workspace_file or filepath.startswith("workspace/"):
            state["workspace_files"] = state.get("workspace_files", []) + [filepath]
        try:
            blast_args = _build_blast_tool_args(filepath, raw_text)
        except ValueError as exc:
            ai_msg = AIMessage(
                content=f"mRNA specialist (BLAST): {exc}",
                tool_calls=[],
            )
            state["messages"] = state.get("messages", []) + [ai_msg]
            return state
        tool_calls = [
            {
                "name": "run_blastn_similarity_search",
                "args": blast_args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch NCBI blastn via blast_service."
    elif ribodiffusion_mode:
        rb_args = _build_ribodiffusion_tool_args(raw_text)
        state["design_input_pdb_filepath"] = rb_args["pdb_filepath"]
        tool_calls = [
            {
                "name": "design_rna_inverse_fold_with_ribodiffusion",
                "args": rb_args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        ]
        content = "mRNA specialist (rule-based): dispatch RiboDiffusion diffusion inverse folding."
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
        tool_name, tool_args = _resolve_protein_to_cds_tool(user_text, raw_text)
        tool_args["filepath"] = filepath
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
                "name": "analyze_cds_codon_metrics_with_codonw_slim",
                "args": _build_codonw_tool_args(filepath, raw_text),
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
            raw_si = state.get("input_sequence", "")
            if _needs_sirna_duplex_vienna(user_text) and not _needs_evitar_mode(user_text):
                try:
                    duplex_fp = _ensure_duplex_fasta_workspace_path(raw_si, filepath)
                    state["current_filepath"] = duplex_fp
                    if duplex_fp.startswith("workspace/"):
                        state["workspace_files"] = state.get("workspace_files", []) + [duplex_fp]
                    fallback_calls = [
                        {"name": "compute_sirna_duplex_binding_vienna", "args": {"filepath": duplex_fp}}
                    ]
                except ValueError:
                    state["messages"] = state.get("messages", []) + [
                        AIMessage(
                            content=(
                                "Tool executor: ViennaRNA duplex mode requires two strands (sense/antisense). "
                                "Mock siRNA fallback tools were removed; please provide a file with two FASTA records "
                                "(sense then antisense) or explicit `sense=` and `antisense=` sequences."
                            )
                        )
                    ]
                    return state
            else:
                if not filepath:
                    filepath = save_sequence(_extract_rna_sequence(raw_si), prefix="sirna")
                    state["current_filepath"] = filepath
                    state["workspace_files"] = state.get("workspace_files", []) + [filepath]
                if _needs_evitar_mode(user_text):
                    fallback_calls = [
                        {
                            "name": "design_sirna_with_evitar",
                            "args": _build_evitar_tool_args(filepath, raw_si),
                        }
                    ]
                else:
                    state["messages"] = state.get("messages", []) + [
                        AIMessage(
                            content=(
                                "Tool executor: unsupported siRNA request. "
                                "siRNA efficiency/off-target mock tools were removed; no production implementation "
                                "is available in this repository."
                            )
                        )
                    ]
                    return state
        elif state.get("active_specialist") == "crispr_specialist":
            raw_crispr_text = state.get("input_sequence", "")
            if _needs_sgrna_handle_design(raw_crispr_text.lower()):
                tool_args, state_updates = _resolve_sgrna_design_request(raw_crispr_text)
                tool_name = "design_sgrna_handle_with_crgpt"
            else:
                tool_name, tool_args, state_updates = _resolve_crisot_request(raw_crispr_text)
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
        elif _needs_inverse_fold_vienna(user_text):
            raw_inv = state.get("input_sequence", "")
            inv_fp = _ensure_inverse_fold_structure_file(raw_inv, filepath)
            state["current_filepath"] = inv_fp
            if inv_fp.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [inv_fp]
            rep_m = re.search(r"repeats?\s*[:=]\s*(\d+)", raw_inv, flags=re.IGNORECASE)
            repeats = int(rep_m.group(1)) if rep_m else 1
            fallback_calls = [
                {
                    "name": "inverse_fold_rna_secondary_structure_vienna",
                    "args": {"filepath": inv_fp, "repeats": repeats},
                }
            ]
        elif _needs_aso_region_plfold_accessibility(state.get("input_sequence", "")):
            raw_aso = state.get("input_sequence", "")
            fp_aso, created_workspace_file = _resolve_rnastop_input(raw_aso)
            state["current_filepath"] = fp_aso
            if created_workspace_file or fp_aso.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [fp_aso]
            nlen = _rna_sequence_length_from_workspace(fp_aso)
            rs, re_fb = _extract_aso_region_bounds(raw_aso)
            if rs is None or re_fb is None:
                rs, re_fb = 1, min(20, nlen)
            rs = max(1, min(rs, nlen))
            re_fb = max(rs, min(re_fb, nlen))
            fallback_calls = [
                {
                    "name": "compute_aso_target_accessibility_vienna",
                    "args": {"filepath": fp_aso, "region_start": rs, "region_end": re_fb},
                }
            ]
        elif _needs_rna_plfold_local_profile(state.get("input_sequence", "")):
            raw_pf = state.get("input_sequence", "")
            fp_pf, created_workspace_file = _resolve_rnastop_input(raw_pf)
            state["current_filepath"] = fp_pf
            if created_workspace_file or fp_pf.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [fp_pf]
            fallback_calls = [
                {"name": "predict_rna_local_accessibility_profile_vienna", "args": {"filepath": fp_pf}}
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
        elif _needs_rna_gc_content_metric(user_text):
            filepath, created_workspace_file = _resolve_rnastop_input(state.get("input_sequence", ""))
            state["current_filepath"] = filepath
            if created_workspace_file or filepath.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            fallback_calls = [{"name": "compute_rna_sequence_gc_content", "args": {"filepath": filepath}}]
        elif _needs_dot_bracket_unpaired_fraction_metric(user_text):
            raw_u = state.get("input_sequence", "")
            try:
                ss_fp, created_ss = _resolve_dot_bracket_structure_filepath(raw_u)
            except ValueError as exc:
                state["messages"] = state.get("messages", []) + [
                    AIMessage(content=f"mRNA tool executor (unpaired fraction): {exc}")
                ]
                return state
            state["current_filepath"] = ss_fp
            if created_ss or ss_fp.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [ss_fp]
            fallback_calls = [{"name": "compute_dot_bracket_unpaired_fraction", "args": {"filepath": ss_fp}}]
        elif _needs_ribodiffusion_design(user_text):
            rb_args = _build_ribodiffusion_tool_args(state.get("input_sequence", ""))
            state["design_input_pdb_filepath"] = rb_args["pdb_filepath"]
            fallback_calls = [
                {"name": "design_rna_inverse_fold_with_ribodiffusion", "args": rb_args},
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
        elif _needs_5utr_design(user_text) or _needs_3utr_design(user_text):
            tool_name, tool_args = _resolve_utr_tool(user_text)
            tool_args["utr_length"] = _extract_utr_length(user_text)
            fallback_calls = [{"name": tool_name, "args": tool_args}]
        elif any(k in user_text for k in ["design", "设计", "gemorna", "rnarl", "lineardesign", "linear design", "protein", "cds", "utr", "生成"]):
            if not filepath:
                filepath = save_sequence(
                    _extract_protein_sequence(state.get("input_sequence", "")),
                    prefix="protein",
                )
                state["current_filepath"] = filepath
                state["workspace_files"] = state.get("workspace_files", []) + [filepath]
            tool_name, tool_args = _resolve_protein_to_cds_tool(user_text, state.get("input_sequence", ""))
            tool_args["filepath"] = filepath
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
                {
                    "name": "analyze_cds_codon_metrics_with_codonw_slim",
                    "args": _build_codonw_tool_args(filepath, state.get("input_sequence", "")),
                },
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
        try:
            tool_result = tool_obj.invoke(tool_args)
        except ValueError as exc:
            # Deterministic fallback for fold: if ViennaRNA is unavailable, try LinearFold.
            if tool_name == "predict_rna_secondary_structure":
                fallback_tool = TOOLS_BY_NAME.get("predict_rna_secondary_structure_with_linearfold")
                fp = str(tool_args.get("filepath") or state.get("current_filepath") or "")
                if fallback_tool and fp:
                    tool_result = fallback_tool.invoke({"filepath": fp})
                    tool_name = "predict_rna_secondary_structure_with_linearfold"
                else:
                    raise
            else:
                raise

        spec = TOOL_SPECS.get(tool_name)
        if spec and spec.output_model:
            # Validate minimal contract for auditability; allow extra fields.
            spec.output_model.model_validate(tool_result)
        out_messages.append(
            ToolMessage(
                content=json.dumps(tool_result, ensure_ascii=True),
                tool_call_id=call["id"],
                name=tool_name,
            )
        )

        if tool_name == "design_sirna_with_evitar":
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
        elif tool_name == "design_sgrna_handle_with_crgpt":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
                if input_filepath.startswith("workspace/"):
                    state["workspace_files"] = state.get("workspace_files", []) + [input_filepath]
            best_sequence = str(tool_result.get("best_sequence", ""))
            if best_sequence:
                state["candidate_sequence"] = best_sequence
            state["sgrna_design_generated_count"] = int(tool_result.get("generated_count", 0))
            state["sgrna_design_best_nn_score"] = float(tool_result.get("best_nn_score", 0.0))
            state["sgrna_design_best_mutation_count"] = int(tool_result.get("best_mutation_count", 0))
            state["sgrna_design_model_path"] = str(tool_result.get("model_path", ""))
            output_fasta_filepath = str(tool_result.get("output_fasta_filepath", ""))
            if output_fasta_filepath:
                state["sgrna_design_output_filepath"] = output_fasta_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_fasta_filepath]
            summary_json_filepath = str(tool_result.get("summary_json_filepath", ""))
            if summary_json_filepath:
                state["sgrna_design_summary_filepath"] = summary_json_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [summary_json_filepath]
            best_sequence_filepath = str(tool_result.get("best_sequence_filepath", ""))
            if best_sequence_filepath:
                state["current_filepath"] = best_sequence_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [best_sequence_filepath]
        elif tool_name == "run_blastn_similarity_search":
            state["blast_hit_count"] = int(tool_result.get("hit_count", 0))
            state["blast_subject_mode"] = str(tool_result.get("subject_mode", ""))
            tab_fp = str(tool_result.get("tabular_tsv_filepath", ""))
            if tab_fp:
                state["blast_tabular_tsv_filepath"] = tab_fp
                if tab_fp.startswith("workspace/"):
                    state["workspace_files"] = state.get("workspace_files", []) + [tab_fp]
        elif tool_name == "compute_rna_sequence_gc_content":
            state["sequence_gc_content"] = float(tool_result.get("gc_content", 0.0))
        elif tool_name == "compute_dot_bracket_unpaired_fraction":
            state["dot_bracket_unpaired_fraction"] = float(tool_result.get("unpaired_fraction", 0.0))
        elif tool_name == "analyze_cds_codon_metrics_with_codonw_slim":
            state["cai_score"] = float(tool_result.get("cai_score", 0.0))
            state["codonw_enc"] = float(tool_result.get("enc", 0.0))
            state["codonw_fop"] = float(tool_result.get("fop", 0.0))
            state["codonw_cbi"] = float(tool_result.get("cbi", 0.0))
            metrics_json_filepath = str(tool_result.get("metrics_json_filepath", ""))
            if metrics_json_filepath:
                state["codonw_metrics_filepath"] = metrics_json_filepath
                if metrics_json_filepath.startswith("workspace/"):
                    state["workspace_files"] = state.get("workspace_files", []) + [metrics_json_filepath]
        elif tool_name == "predict_rna_secondary_structure":
            if isinstance(tool_result, dict):
                state["mfe"] = float(tool_result.get("mfe_kcal_per_mol", 0.0))
                structure = str(tool_result.get("structure", ""))
            else:
                structure = ""
            if structure:
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
            "design_5utr_with_gemorna",
            "design_3utr_with_gemorna",
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
        elif tool_name == "design_rna_inverse_fold_with_ribodiffusion":
            state["design_input_pdb_filepath"] = str(tool_result.get("input_pdb_filepath", ""))

            output_filepath = str(tool_result.get("output_filepath", ""))
            if output_filepath:
                state["current_filepath"] = output_filepath
                state["workspace_files"] = state.get("workspace_files", []) + [output_filepath]

            outs = tool_result.get("output_fasta_filepaths")
            if isinstance(outs, list) and outs:
                joined = [str(x) for x in outs if str(x)]
                if joined:
                    state["designed_sequence_fasta_filepath"] = joined[0]
                    state["workspace_files"] = state.get("workspace_files", []) + joined

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
        elif tool_name == "compute_sirna_duplex_binding_vienna":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
            state["vienna_sirna_duplex_mfe"] = float(tool_result.get("mfe_kcal_per_mol", 0.0))
            sense = str(tool_result.get("sense", ""))
            anti = str(tool_result.get("antisense", ""))
            if sense and anti:
                state["candidate_sequence"] = f"{sense}&{anti}"
        elif tool_name == "compute_aso_target_accessibility_vienna":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
            mu = tool_result.get("mean_unpaired_prob_single_nt")
            if mu is not None:
                state["vienna_aso_mean_unpaired"] = float(mu)
            ju = tool_result.get("joint_unpaired_prob_stretch_ending_at_region_end")
            if ju is not None:
                state["vienna_aso_joint_unpaired"] = float(ju)
        elif tool_name == "predict_rna_local_accessibility_profile_vienna":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
            lunp_fp = str(tool_result.get("lunp_profile_tsv_filepath", ""))
            if lunp_fp.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [lunp_fp]
        elif tool_name == "inverse_fold_rna_secondary_structure_vienna":
            input_filepath = str(tool_result.get("input_filepath", state.get("current_filepath", "")))
            if input_filepath:
                state["current_filepath"] = input_filepath
            best = str(tool_result.get("best_sequence", ""))
            state["vienna_inverse_best_sequence"] = best
            if best:
                state["candidate_sequence"] = best
            best_fp = str(tool_result.get("best_sequence_filepath", ""))
            if best_fp.startswith("workspace/"):
                state["workspace_files"] = state.get("workspace_files", []) + [best_fp]
                state["current_filepath"] = best_fp
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
    user_text = state.get("input_sequence", "").lower()
    raw_user = state.get("input_sequence", "")
    if (
        specialist == "mrna_specialist"
        and not _needs_rnastop_prediction(user_text)
        and not _needs_iresfinder_prediction(user_text)
        and not _needs_structure_to_sequence_design(user_text)
        and not _needs_ribodiffusion_design(user_text)
        and not _needs_rna_gc_content_metric(user_text)
        and not _needs_dot_bracket_unpaired_fraction_metric(user_text)
        and not _needs_rna_plfold_local_profile(raw_user)
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
                    f"specialist={specialist}, mfe={mfe}, retry={retry_count + 1}"
                )
            )
        ]
    else:
        state["next_action"] = "finish"
        state["critic_verdict"] = "pass"
        state["final_report"] = (
            f"specialist={specialist}; "
            f"filepath={state.get('current_filepath', '')}; "
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
            f"sgrna_design_generated_count={state.get('sgrna_design_generated_count', 0)}; "
            f"sgrna_design_best_nn_score={state.get('sgrna_design_best_nn_score', 0.0)}; "
            f"sgrna_design_best_mutation_count={state.get('sgrna_design_best_mutation_count', 0)}; "
            f"sgrna_design_output_filepath={state.get('sgrna_design_output_filepath', '')}; "
            f"sgrna_design_summary_filepath={state.get('sgrna_design_summary_filepath', '')}; "
            f"sgrna_design_model_path={state.get('sgrna_design_model_path', '')}; "
            f"cai_score={cai_score}; "
            f"codonw_metrics_filepath={state.get('codonw_metrics_filepath', '')}; "
            f"codonw_enc={state.get('codonw_enc', 0.0)}; "
            f"codonw_fop={state.get('codonw_fop', 0.0)}; "
            f"codonw_cbi={state.get('codonw_cbi', 0.0)}; "
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
            f"vienna_sirna_duplex_mfe={state.get('vienna_sirna_duplex_mfe', 0.0)}; "
            f"vienna_aso_mean_unpaired={state.get('vienna_aso_mean_unpaired', 0.0)}; "
            f"vienna_aso_joint_unpaired={state.get('vienna_aso_joint_unpaired', 0.0)}; "
            f"vienna_inverse_best_sequence={state.get('vienna_inverse_best_sequence', '')}; "
            f"blast_hit_count={state.get('blast_hit_count', 0)}; "
            f"blast_tabular_tsv_filepath={state.get('blast_tabular_tsv_filepath', '')}; "
            f"blast_subject_mode={state.get('blast_subject_mode', '')}; "
            f"sequence_gc_content={state.get('sequence_gc_content', 0.0)}; "
            f"dot_bracket_unpaired_fraction={state.get('dot_bracket_unpaired_fraction', 0.0)}; "
            f"retries={retry_count}"
        )
        state["messages"] = state.get("messages", []) + [
            AIMessage(
                content=(
                    f"Critic (rule-based): pass. "
                    f"specialist={specialist}, mfe={mfe}"
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
