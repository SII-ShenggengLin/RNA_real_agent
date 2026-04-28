"""Common parsers and predicates for the rule-based planning layer."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ViennaRNA INTERFACE LOCK (v0.4.0) —— 禁止单方面变更
# 关联文件清单见 microservices/viennarna_fold/main.py 顶部的 INTERFACE LOCK。
# 任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# LinearFold INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 microservices/linearfold_service/main.py 顶部的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# BLAST+ INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 run_blastn_similarity_search 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

from agent_core.file_manager import read_sequence, save_sequence, save_text_file
from agent_core.state import AgentState

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


def _needs_rnaup_vienna(user_text: str) -> bool:
    keys = (
        "rnaup",
        "rna up",
        "rna-rna interaction",
        "rna rna interaction",
        "interaction thermodynamics",
        "accessibility + binding",
        "结合热力学",
        "相互作用",
        "rnaup",
    )
    return any(k in user_text.lower() for k in keys)


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


# ═══════════════════════════════════════════════════════════════════════════════
# RNA sequence metrics (GC content) INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 compute_rna_sequence_gc_content
# 的 INTERFACE LOCK 注释。任何字段增删必须同步更新全部关联文件。
# ═══════════════════════════════════════════════════════════════════════════════

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
        path_obj = Path(fp)
        if not path_obj.is_absolute():
            path_obj = (PROJECT_ROOT / fp).resolve()
        if not path_obj.is_file():
            raise ValueError(f"Structure file not found: {fp}")
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


# ═══════════════════════════════════════════════════════════════════════════════
# codonw-slim INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 CodonwSlimOutput 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

def _build_codonw_tool_args(filepath: str, raw_text: str) -> dict[str, Any]:
    """Extract codonw-slim tool arguments from raw user text.

    Supports explicit key=value patterns (e.g. genetic_code=1, cai_ref=2)
    as well as keyword heuristics (e.g. "dinucleotide", "codon table").
    """
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
    if re.search(r"aa_usage|amino[-\s]?acid\s*usage|raau|relative\s*amino[-\s]?acid", raw_text, flags=re.IGNORECASE):
        args["include_aa_tables"] = True
    if re.search(r"include_bases|base\s*composition\s*(by\s*position|matrix)", raw_text, flags=re.IGNORECASE):
        args["include_bases"] = True
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


def _needs_sgrna_handle_score(text: str) -> bool:
    lowered = text.lower()
    has_score = any(k in lowered for k in ["score", "评分", "打分", "scoring"])
    has_sgrna = any(k in lowered for k in ["sgrna", "handle", "crgpt"])
    return has_score and has_sgrna


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


# ═══════════════════════════════════════════════════════════════════════════════
# RiboDiffusion INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
# 关联文件清单（修改时必须全部同步）：
#   - microservices/ribodiffusion_service/main.py
#   - agent_core/tools.py
#   - agent_core/tool_specs.py
#   - agent_core/state.py
#   - agent_core/nodes.py  ← 本文件
#   - docs/RNA_AGENT_SYSTEM_GUIDE.md
# 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
# 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
# ═══════════════════════════════════════════════════════════════════════════════


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
    ckpt = _extract_string_setting(raw_text, ("checkpoint_name", "checkpoint"))
    if ckpt is not None:
        args["checkpoint_name"] = ckpt
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


def _needs_lineardesign_batch(text: str) -> bool:
    """Detect batch-design intent for LinearDesign."""
    lowered = text.lower()
    has_batch_kw = any(k in lowered for k in ["batch", "bulk", "multiple", "批量", "批量设计"])
    has_ld_kw = any(k in lowered for k in ["lineardesign", "linear design"])
    return has_batch_kw and has_ld_kw


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
    if "sharpturn" in lowered:
        args["sharpturn"] = True
    return args


def _build_linearfold_eval_tool_args(
    sequence_filepath: str, structure_filepath: str, raw_text: str
) -> dict[str, Any]:
    args: dict[str, Any] = {
        "sequence_filepath": sequence_filepath,
        "structure_filepath": structure_filepath,
    }
    lowered = raw_text.lower()
    if "linearfold-v" in lowered or "linearfold_v" in lowered:
        args["use_vienna"] = True
    elif "linearfold" in lowered and "vienna" in lowered:
        args["use_vienna"] = True
    dangles = _extract_int_setting(raw_text, ("dangles", "dangle"))
    if dangles in (0, 2):
        args["dangles"] = dangles
    if "verbose" in lowered:
        args["verbose"] = True
    return args


def _build_linearfold_zuker_tool_args(filepath: str, raw_text: str) -> dict[str, Any]:
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
    if "sharpturn" in lowered:
        args["sharpturn"] = True
    delta = _extract_float_setting(raw_text, ("delta",))
    if delta is not None and delta >= 0:
        args["delta"] = delta
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
    if _needs_lineardesign_batch(user_text):
        tool_name = "design_mrna_cds_batch_with_lineardesign"
    elif _needs_lineardesign(user_text):
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


# ═══════════════════════════════════════════════════════════════════════════════
# RNAsmOL 接口冻结声明 (v0.2.0) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
# 关联文件清单（修改时必须全部同步）：
#   - microservices/rnasmol_service/main.py
#   - agent_core/tools.py
#   - agent_core/tool_specs.py
#   - agent_core/state.py
#   - agent_core/nodes.py  ← 本文件
#   - docs/tools/score_rna_ligand_binding_with_rnasmol.md
# 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
# 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_rnasmol_overrides(text: str) -> dict[str, str]:
    """Extract RNAsmol-specific overrides (dataset, perturbation_type, device) from user text."""
    overrides: dict[str, str] = {}
    dataset_match = re.search(
        r"(?:dataset|data[_\s]?source|source)\s*[:=]\s*[\"']?(pdb|robin)[\"']?",
        text,
        re.IGNORECASE,
    )
    if dataset_match:
        overrides["dataset"] = dataset_match.group(1).lower()
    pert_match = re.search(
        r"(?:perturbation|perturbation[_\s]?type|augmentation)\s*[:=]\s*[\"']?(molperturbation|netperturbation|rnaperturbation)[\"']?",
        text,
        re.IGNORECASE,
    )
    if pert_match:
        overrides["perturbation_type"] = pert_match.group(1).lower()
    device_match = re.search(
        r"(?:rnasmol[_\s]?device|device)\s*[:=]\s*[\"']?(cuda:\d+|cpu)[\"']?",
        text,
        re.IGNORECASE,
    )
    if device_match:
        overrides["device"] = device_match.group(1).lower()
    return overrides


def _resolve_rna_ligand_inputs(text: str) -> Tuple[str, str, bool]:
    smiles = _extract_smiles(text)
    if not smiles:
        raise ValueError(
            "RNA-ligand scoring requires a ligand SMILES string. "
            "Please provide it like `SMILES=CCO` or `SMILES: C1=CC=CC=C1`."
        )

    filepath = _extract_path_with_suffixes(text, ("fasta", "fa", "txt", "seq"))
    if filepath:
        return filepath, smiles, False

    rna_sequence = _extract_long_rna_sequence(text)
    if not rna_sequence:
        raise ValueError(
            "RNA-ligand scoring requires an RNA sequence or a `.fasta/.fa/.txt/.seq` filepath."
        )

    return save_sequence(rna_sequence, prefix="rna_ligand"), smiles, True


def _update_state_with_ligand_inputs(
    state: AgentState, filepath: str, smiles: str, created_workspace_file: bool
) -> None:
    """Attach RNA-ligand inputs to shared state and track workspace files."""
    state["current_filepath"] = filepath
    state["ligand_smiles"] = smiles
    if created_workspace_file or filepath.startswith("workspace/"):
        state["workspace_files"] = state.get("workspace_files", []) + [filepath]


def _resolve_sequence_input(text: str) -> Tuple[str, bool]:
    """Resolve a nucleic-acid sequence input into a filepath.

    If *text* is already a filepath with a recognised suffix, return it as-is.
    Otherwise extract the longest RNA-like stretch, save it to the workspace,
    and return the new filepath.
    """
    filepath = _extract_path_with_suffixes(text, ("fasta", "fa", "txt", "seq"))
    if filepath:
        return filepath, False

    rna_sequence = _extract_long_rna_sequence(text)
    if not rna_sequence:
        raise ValueError(
            "Sequence input requires an RNA sequence or a `.fasta/.fa/.txt/.seq` filepath."
        )

    return save_sequence(rna_sequence, prefix="sequence_input"), True


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

    outfmt = _extract_string_setting(raw_text, ("outfmt", "out_fmt", "output_format"))
    if outfmt is not None:
        args["outfmt"] = outfmt

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


# ═══════════════════════════════════════════════════════════════════════════════
# Evitar INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 design_sirna_with_evitar 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_evitar_input_filepath(raw_text: str, current_filepath: Optional[str] = None) -> str:
    """Resolve an Evitar input FASTA path from user text or fall back to current_filepath.

    Search order:
        1. current_filepath if already present.
        2. Named file references (input=..., genome=..., virus=..., fasta=...).
        3. Any path with FASTA-like suffix.
        4. Generate a FASTA from an inline RNA sequence.
    """
    if current_filepath:
        return current_filepath
    filepath = _extract_named_filepath(
        raw_text, ("input", "genome", "virus", "fasta"), ("fa", "fasta", "fna")
    )
    if not filepath:
        filepath = _extract_path_with_suffixes(raw_text, ("fasta", "fa", "fna", "txt", "seq"))
    if not filepath:
        filepath = save_sequence(_extract_rna_sequence(raw_text), prefix="evitar_input")
    return filepath


def _build_evitar_tool_args(filepath: str, raw_text: str) -> dict[str, Any]:
    """Extract all Evitar-relevant arguments from natural-language user text.

    Mirrors the upstream Evitar CLI options so the agent can fully exploit
    the tool's capabilities without hand-coding every permutation.
    """
    lowered = raw_text.lower()
    args: dict[str, Any] = {
        "filepath": filepath,
        "mode": "predesign"
        if any(key in lowered for key in ["predesign", "future virus", "future viruses", "未来"])
        else "existing",
        "predict": "CRISPR"
        if any(key in lowered for key in ["cas13", "grna", "crispr"])
        else "rnaxs"
        if "rnaxs" in lowered
        else "multifapredsi"
        if "multifapredsi" in lowered
        else "predsi",
        "off_target": any(key in lowered for key in ["offtarget", "off-target", "脱靶"]),
    }
    ncores = _extract_int_setting(raw_text, ("ncores", "threads", "cores"))
    if ncores is not None and ncores > 0:
        args["ncores"] = ncores

    # --- File paths ---
    strains_path = _extract_named_filepath(raw_text, ("strains", "strain", "variants"), ("fa", "fasta", "fna"))
    if strains_path:
        args["strains_path"] = strains_path

    p3utr_path = _extract_named_filepath(raw_text, ("p3utr", "3utr", "3'utr"), ("fa", "fasta", "fna", "txt"))
    if p3utr_path:
        args["p3utr_path"] = p3utr_path

    transcriptome_path = _extract_named_filepath(
        raw_text, ("transcriptome", "transcriptome_path", "transcriptome_path"), ("fa", "fasta", "fna", "txt")
    )
    if transcriptome_path:
        args["transcriptome_path"] = transcriptome_path

    weight_path = _extract_named_filepath(raw_text, ("weight", "weight_path"), ("txt", "tsv", "csv"))
    if weight_path:
        args["weight_path"] = weight_path

    allow_path = _extract_named_filepath(raw_text, ("allow", "allowlist", "allow_list"), ("txt", "tsv", "csv"))
    if allow_path:
        args["allow_path"] = allow_path

    ban_path = _extract_named_filepath(raw_text, ("ban", "banlist", "ban_list"), ("txt", "tsv", "csv"))
    if ban_path:
        args["ban_path"] = ban_path

    # --- Summary / selection (predesign mode) ---
    sumtype = _extract_string_setting(raw_text, ("sumtype", "sum_type", "algorithm"))
    if sumtype and sumtype.lower() in {"sgar", "greedy"}:
        args["sumtype"] = sumtype

    limitnum = _extract_int_setting(raw_text, ("limitnum", "limit_num", "limit"))
    if limitnum is not None and limitnum > 0:
        args["limitnum"] = limitnum

    repeatnum = _extract_int_setting(raw_text, ("repeatnum", "repeat_num", "repeat"))
    if repeatnum is not None and repeatnum > 0:
        args["repeatnum"] = repeatnum

    # --- Off-target cutoffs ---
    pmcuff = _extract_int_setting(raw_text, ("pmcuff", "pm_cuff", "perfect_match_cutoff"))
    if pmcuff is not None and pmcuff >= 0:
        args["pmcuff"] = pmcuff

    umcuff = _extract_float_setting(raw_text, ("umcuff", "um_cuff", "unperfect_match_cutoff"))
    if umcuff is not None and umcuff >= 0:
        args["umcuff"] = umcuff

    mircuff = _extract_float_setting(raw_text, ("mircuff", "mir_cuff", "mirna_cutoff"))
    if mircuff is not None and mircuff >= 0:
        args["mircuff"] = mircuff

    # --- GC-content filters ---
    maxgc = _extract_float_setting(raw_text, ("maxgc", "max_gc", "max_gc_content"))
    if maxgc is not None and 0.0 <= maxgc <= 1.0:
        args["maxgc"] = maxgc

    mingc = _extract_float_setting(raw_text, ("mingc", "min_gc", "min_gc_content"))
    if mingc is not None and 0.0 <= mingc <= 1.0:
        args["mingc"] = mingc

    middlegc = _extract_float_setting(raw_text, ("middlegc", "middle_gc", "middle_gc_content"))
    if middlegc is not None and 0.0 <= middlegc <= 1.0:
        args["middlegc"] = middlegc

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


# ═══════════════════════════════════════════════════════════════════════════════
# sgrna_design INTERFACE LOCK (v0.3.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 design_sgrna_handle_with_crgpt
# 的 INTERFACE LOCK 注释。任何修改必须全部同步。
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_sgrna_design_request(text: str) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Resolve sgRNA design request from natural language text.

    Priority:
      1. Explicit seed_sequence=... in text
      2. Bare DNA/RNA sequence (40-140 nt)
      3. File path with fasta/fa/txt/seq extension
      4. Default wildtype sequence
    """
    # 1. Try explicit seed_sequence= assignment
    explicit_match = re.search(
        r"seed_sequence\s*[:=]\s*[\"']?([ACGUTacgut\s]{40,140})[\"']?",
        text,
        re.IGNORECASE,
    )
    raw_sequence = ""
    if explicit_match:
        raw_sequence = explicit_match.group(1).strip().upper().replace("U", "T").replace(" ", "")
    if not raw_sequence:
        # 2. Try bare sequence
        raw_sequence = _extract_sgrna_seed_sequence(text)

    filepath_candidate: Optional[str] = None
    if not raw_sequence:
        # 3. Try file path
        filepath_candidate = _extract_path_with_suffixes(text, ("fasta", "fa", "txt", "seq"))

    workspace_files: list[str] = []
    tool_args: dict[str, Any] = {}

    if raw_sequence:
        tool_args["seed_sequence"] = raw_sequence
        state_updates: dict[str, Any] = {"sgrna_design_seed_sequence": raw_sequence}
    elif filepath_candidate:
        tool_args["filepath"] = filepath_candidate
        state_updates = {"current_filepath": filepath_candidate}
    else:
        # 4. Default wildtype
        default_wildtype = "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG"
        tool_args["seed_sequence"] = default_wildtype
        state_updates = {"sgrna_design_seed_sequence": default_wildtype}

    # Extract optional parameters
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
    sampling_mode = _extract_string_setting(text, ("sampling_mode", "mode", "sampling"))
    if sampling_mode and sampling_mode.lower() in ("mcmc", "naive"):
        tool_args["sampling_mode"] = sampling_mode.lower()
    max_length = _extract_int_setting(text, ("max_length", "maxlen"))
    if max_length is not None and max_length > 0:
        tool_args["max_length"] = max_length
    path_to_model = _extract_string_setting(text, ("path_to_model", "model_path", "model_dir"))
    if path_to_model:
        tool_args["path_to_model"] = path_to_model

    if workspace_files:
        state_updates["workspace_files"] = workspace_files
    return tool_args, state_updates


# ═══════════════════════════════════════════════════════════════════════════════
# CRISOT INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 CRISOT ToolSpec 注册区域的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_crisot_request(text: str) -> Tuple[str, dict[str, Any], dict[str, Any]]:
    lowered = text.lower()
    csv_path = _extract_path_with_suffixes(text, ("csv",))
    txt_path = _extract_path_with_suffixes(text, ("txt",))
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

    # ── CRISOT-FP XGBoost prediction (csv + fp keywords) ──
    if csv_path and any(k in lowered for k in ["crisot_fp", "crisot-fp", "fp", "fingerprint", "xgboost"]):
        xgb_model = "Circle-seq"
        for candidate in ["circle-seq", "circleseq", "site-seq", "siteseq", "change-seq", "changeseq"]:
            if candidate.replace("-", "") in lowered or candidate in lowered:
                if "site" in candidate:
                    xgb_model = "Site-seq"
                elif "change" in candidate:
                    xgb_model = "Change-seq"
                else:
                    xgb_model = "Circle-seq"
                break
        state_updates = {
            "crisot_input_csv_filepath": csv_path,
            "crisot_fp_xgb_model": xgb_model,
            "workspace_files": [],
        }
        return (
            "predict_crispr_off_target_with_crisot_fp",
            {
                "csv_filepath": csv_path,
                "xgb_model": xgb_model,
            },
            state_updates,
        )

    # ── Batch scoring (csv + score keywords, but not spec) ──
    if csv_path and any(k in lowered for k in ["scores", "batch", "batch_score"]):
        state_updates = {
            "crisot_input_csv_filepath": csv_path,
            "workspace_files": [],
        }
        return (
            "score_batch_crispr_off_targets_with_crisot",
            {"csv_filepath": csv_path},
            state_updates,
        )

    # ── Specificity from CSV ──
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

    # ── Rescore / rerank (txt + genome) ──
    if txt_path and any(k in lowered for k in ["rescore", "rerank", "re-score", "re-rank"]):
        if not genome_path:
            raise ValueError(
                "CRISOT rescore requires a reference genome FASTA path for Cas-OFFinder."
            )
        tool_args: dict[str, Any] = {
            "txt_filepath": txt_path,
            "genome_path": genome_path,
        }
        if mismatches is not None:
            tool_args["mismatches"] = mismatches
        if device:
            tool_args["device"] = device
        state_updates = {
            "crisot_genome_path": genome_path,
            "workspace_files": [],
        }
        return (
            "rescore_sgrnas_with_crisot",
            tool_args,
            state_updates,
        )

    # ── Optimization ──
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
        tool_args = {
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

    # ── Gen FP (requires both sgrna and target) ──
    if sgrna and target_sequence and any(k in lowered for k in ["gen_fp", "gen-fp", "generate fingerprint", "encode"]):
        state_updates = {
            "crisot_target_sequence": target_sequence,
            "workspace_files": [],
        }
        return (
            "generate_crispr_fingerprint_with_crisot",
            {
                "sgrna": sgrna,
                "target_sequence": target_sequence,
            },
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


