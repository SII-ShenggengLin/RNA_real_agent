#!/usr/bin/env python3
"""One-shot audit of the RNADesign-210 (RNA-BioBench-Platform) task suite.

Checks, per the 2026-08-25 re-run reset:
  A. structural consistency  — task counts, unique ids, dir<->workflow match,
     manifest agreement, required keys, categories;
  B. architecture fit        — every task `input` validated against the current
     workflow Input model (unknown/missing fields flagged), expected_tool_chain
     checked against the 41-tool registry, referenced file paths resolved;
  C. biological validity     — per-workflow sequence/structure/species checks;
  D. innovation coverage     — which opt-in platform features (GenNav
     navigation, ASF reference points, off-target scanning, structural
     validation) the task set actually exercises.

Output: human-readable report to stdout + JSON to experiments/results/rnadesign210_audit.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TASKS_ROOT = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Platform" / "tasks"
BENCH_MANIFEST = TASKS_ROOT.parent / "benchmark_manifest.json"

from agent_core.workflows import (  # noqa: E402
    AsoScreeningInput,
    FullLengthMrnaDesignInput,
    IresPredictionInput,
    MrnaCdsDesignInput,
    MrnaSequenceScoringInput,
    RnaAptamerDesignInput,
    RnaSecondaryStructureDesignInput,
    RnaSmallMoleculeInteractionInput,
    RnaTertiaryStructureDesignInput,
    SgRnaDesignInput,
    SirnaDesignInput,
)
from agent_core.tool_registry import ToolRegistry  # noqa: E402

DIR_TO_INPUT_MODEL = {
    "01_mrna_cds_design": MrnaCdsDesignInput,
    "02_full_length_mrna_design": FullLengthMrnaDesignInput,
    "03_mrna_sequence_scoring": MrnaSequenceScoringInput,
    "04_sirna_design": SirnaDesignInput,
    "05_sgrna_design": SgRnaDesignInput,
    "06_rna_secondary_structure": RnaSecondaryStructureDesignInput,
    "07_rna_tertiary_structure": RnaTertiaryStructureDesignInput,
    "08_rna_aptamer_design": RnaAptamerDesignInput,
    "09_rna_small_molecule": RnaSmallMoleculeInteractionInput,
    "10_aso_target_screening": AsoScreeningInput,
    "11_ires_prediction": IresPredictionInput,
}

RNA_ALPHABET = set("ACGU")
DNA_ALPHABET = set("ACGT")
PROTEIN_ALPHABET = set("ACDEFGHIKLMNPQRSTVWY")
DOT_BRACKET_PK = set("[]{}<>AaBbCcDdEeFf")

issues: list[str] = []
warns: list[str] = []
info: Counter = Counter()


def issue(tid: str, msg: str) -> None:
    issues.append(f"{tid}: {msg}")


def warn(tid: str, msg: str) -> None:
    warns.append(f"{tid}: {msg}")


def check_rna(tid: str, field: str, seq: str, *, allow_t: bool = True) -> None:
    s = seq.upper()
    alpha = RNA_ALPHABET | (set("T") if allow_t else set())
    bad = set(s) - alpha
    if bad:
        issue(tid, f"{field}: non-RNA characters {sorted(bad)}")
    if len(s) < 8:
        issue(tid, f"{field}: suspiciously short ({len(s)} nt)")


def check_protein(tid: str, field: str, seq: str) -> None:
    s = seq.upper().replace("*", "")
    bad = set(s) - PROTEIN_ALPHABET
    if bad:
        issue(tid, f"{field}: non-standard amino acids {sorted(bad)}")
    if len(s) < 5:
        issue(tid, f"{field}: suspiciously short ({len(s)} aa)")


def check_dot_bracket(tid: str, field: str, struct: str) -> None:
    pk = set(struct) & DOT_BRACKET_PK
    if pk:
        issue(tid, f"{field}: pseudoknot characters {sorted(pk)} (ViennaRNA inverse-fold endpoint rejects these since DECISIONS (x))")
    depth = 0
    for ch in struct:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                issue(tid, f"{field}: unbalanced dot-bracket")
                return
    if depth != 0:
        issue(tid, f"{field}: unbalanced dot-bracket (depth {depth})")
    if not set(struct) <= set(".()"):
        warn(tid, f"{field}: unusual characters {sorted(set(struct) - set('.()'))}")


def resolve_path(tid: str, field: str, value: str, task_dir: Path) -> Path | None:
    p = Path(value)
    if p.is_absolute():
        warn(tid, f"{field}: absolute path {value} (fragile; prefer repo-relative)")
    else:
        # repo-relative (current convention, e.g. 07 tasks) or task-dir-relative
        cand = PROJECT_ROOT / p
        p = cand if cand.exists() else task_dir / p
    if not p.exists():
        issue(tid, f"{field}: referenced file does not exist: {value}")
        return None
    return p


def fasta_sequences(path: Path) -> list[str]:
    seqs, cur = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(">"):
            if cur:
                seqs.append("".join(cur))
            cur = []
        else:
            cur.append(line.strip())
    if cur:
        seqs.append("".join(cur))
    return seqs


def main() -> int:
    from agent_core.tool_executor import build_default_tool_registry  # noqa: E402

    tool_names: set[str] = set(build_default_tool_registry().list_names())

    bench_manifest = json.loads(BENCH_MANIFEST.read_text(encoding="utf-8"))
    per_dir_counts: dict[str, int] = {}
    all_task_ids: set[str] = set()
    nav_tasks: list[str] = []
    feature_usage: Counter = Counter()

    for wf_dir in sorted(TASKS_ROOT.iterdir()):
        if not wf_dir.is_dir() or wf_dir.name not in DIR_TO_INPUT_MODEL:
            continue
        model = DIR_TO_INPUT_MODEL[wf_dir.name]
        model_fields = set(model.model_fields)
        task_files = sorted(p for p in wf_dir.glob("*.json") if p.name != "dataset_manifest.json")
        per_dir_counts[wf_dir.name] = len(task_files)

        # per-directory manifest agreement
        dir_manifest_p = wf_dir / "dataset_manifest.json"
        if dir_manifest_p.exists():
            dm = json.loads(dir_manifest_p.read_text(encoding="utf-8"))
            dm_count = dm.get("task_count") or dm.get("num_tasks")
            if dm_count not in (None, len(task_files)):
                warn(wf_dir.name, f"dataset_manifest.json task_count={dm_count} but {len(task_files)} files on disk")

        for tf in task_files:
            try:
                task = json.loads(tf.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                issue(tf.name, f"invalid JSON ({e})")
                continue
            tid = task.get("task_id", tf.stem)
            info["tasks"] += 1
            if tid in all_task_ids:
                issue(tid, "duplicate task_id")
            all_task_ids.add(tid)

            for key in ("task_id", "workflow", "category", "description", "input"):
                if key not in task:
                    issue(tid, f"missing key {key}")
            wf_name = task.get("workflow", "")
            if wf_dir.name.split("_", 1)[1].removesuffix("_design").removesuffix("_structure") not in wf_name \
                    and wf_name not in wf_dir.name:
                issue(tid, f"workflow field '{wf_name}' mismatches directory {wf_dir.name}")

            raw = task.get("input") or {}
            extra = set(raw) - model_fields
            if extra:
                issue(tid, f"input has fields unknown to current {model.__name__}: {sorted(extra)}")
            try:
                model.model_validate(raw)
            except Exception as e:
                issue(tid, f"input fails {model.__name__} validation: {str(e)[:400]}")

            for tool in task.get("expected_tool_chain") or []:
                if tool not in tool_names:
                    issue(tid, f"expected_tool_chain references unknown tool: {tool}")

            # ---- per-workflow biological / reference checks ----
            if wf_name == "mrna_cds_design":
                if raw.get("protein_sequence"):
                    check_protein(tid, "protein_sequence", raw["protein_sequence"])
                if raw.get("navigation"):
                    nav_tasks.append(tid)
            if wf_name == "full_length_mrna_design":
                if raw.get("protein_sequence"):
                    check_protein(tid, "protein_sequence", raw["protein_sequence"])
                for fld in ("utr5_sequence", "utr3_sequence"):
                    if raw.get(fld):
                        check_rna(tid, fld, raw[fld])
            if wf_name == "mrna_sequence_scoring":
                seqs = raw.get("sequences") or ([raw["sequence"]] if raw.get("sequence") else [])
                for i, s in enumerate(seqs):
                    check_rna(tid, f"sequences[{i}]", s)
            if wf_name == "sirna_design":
                if raw.get("target_sequence"):
                    check_rna(tid, "target_sequence", raw["target_sequence"])
                    gc = (raw["target_sequence"].upper().count("G") + raw["target_sequence"].upper().count("C")) / len(raw["target_sequence"])
                    if not 0.15 <= gc <= 0.85:
                        warn(tid, f"target_sequence GC={gc:.2f} outside 0.15-0.85 (Evitar scan reliability)")
                if raw.get("off_target_scan"):
                    feature_usage["sirna_off_target_scan"] += 1
                if raw.get("target_sequence_fasta"):
                    resolve_path(tid, "target_sequence_fasta", raw["target_sequence_fasta"], wf_dir)
            if wf_name == "sgrna_design":
                for fld in ("target_sequence",):
                    if raw.get(fld):
                        check_rna(tid, fld, raw[fld])
                seed = raw.get("seed_sequence") or ""
                if raw.get("seed_filepath"):
                    sp = resolve_path(tid, "seed_filepath", raw["seed_filepath"], wf_dir)
                    if sp:
                        seed = "".join(
                            l.strip() for l in sp.read_text(encoding="utf-8").splitlines() if not l.startswith(">")
                        ).upper()
                if not seed:
                    warn(tid, "no seed provided (CRGPT handle scoring will fail)")
                elif len(seed) < 40:
                    issue(tid, f"seed len {len(seed)} < 40 nt — CRGPT seed must be the sgRNA handle scaffold (DECISIONS (x))")
            if wf_name == "rna_secondary_structure_design":
                struct = raw.get("target_structure") or ""
                seq = raw.get("sequence") or ""
                check_dot_bracket(tid, "target_structure", struct)
                if seq:
                    check_rna(tid, "sequence", seq)
                    if len(seq) != len(struct):
                        issue(tid, f"sequence len {len(seq)} != target_structure len {len(struct)}")
            if wf_name == "rna_tertiary_structure":
                if raw.get("sequence"):
                    check_rna(tid, "sequence", raw["sequence"])
                if raw.get("template_pdb_path"):
                    resolve_path(tid, "template_pdb_path", raw["template_pdb_path"], wf_dir)
            if wf_name == "rna_aptamer_design":
                if raw.get("protein_sequence"):
                    check_protein(tid, "protein_sequence", raw["protein_sequence"])
                if raw.get("navigation"):
                    nav_tasks.append(tid)
                    feature_usage["aptamer_navigation"] += 1
                if raw.get("pdb_path"):
                    resolve_path(tid, "pdb_path", raw["pdb_path"], wf_dir)
            if wf_name == "rna_small_molecule_interaction":
                if raw.get("sequence"):
                    check_rna(tid, "sequence", raw["sequence"])
            if wf_name == "aso_target_screening":
                if raw.get("sequence"):
                    check_rna(tid, "sequence", raw["sequence"])
                if raw.get("sequence_fasta"):
                    resolve_path(tid, "sequence_fasta", raw["sequence_fasta"], wf_dir)
            if wf_name == "ires_prediction":
                if raw.get("sequence"):
                    check_rna(tid, "sequence", raw["sequence"])
                if raw.get("sequence_filepath"):
                    p = resolve_path(tid, "sequence_filepath", raw["sequence_filepath"], wf_dir)
                    if p and p.suffix.lower() in {".fa", ".fasta"}:
                        for i, s in enumerate(fasta_sequences(p)):
                            check_rna(tid, f"sequence_filepath[{i}]", s)
                if raw.get("run_structural_validation"):
                    feature_usage["ires_structural_validation"] += 1

            if task.get("category"):
                info[f"category:{task['category']}"] += 1

    # ---- top-level manifest agreement ----
    for wf in bench_manifest.get("workflows", []):
        declared = wf.get("task_count")
        actual = per_dir_counts.get(wf["id"])
        if declared != actual:
            issue("benchmark_manifest.json", f"{wf['id']}: declared task_count={declared}, disk has {actual}")
    declared_total = bench_manifest.get("total_tasks")
    actual_total = sum(per_dir_counts.values())
    if declared_total != actual_total:
        issue("benchmark_manifest.json", f"declared total_tasks={declared_total}, disk has {actual_total}")

    print("=" * 70)
    print(f"Tasks audited: {info['tasks']} across {len(per_dir_counts)} workflows")
    for d, c in per_dir_counts.items():
        print(f"  {d}: {c}")
    print("\n--- Categories ---")
    for k, v in sorted(info.items()):
        if k.startswith("category:"):
            print(f"  {k}: {v}")
    print("\n--- Feature usage (innovation coverage) ---")
    for k, v in feature_usage.items():
        print(f"  {k}: {v} tasks")
    print(f"  navigation tasks: {nav_tasks or 'NONE'}")
    print(f"\n--- ISSUES ({len(issues)}) ---")
    for i in issues:
        print(f"  [ISSUE] {i}")
    print(f"\n--- WARNINGS ({len(warns)}) ---")
    for w in warns:
        print(f"  [warn] {w}")

    out = {
        "audit_date": "2026-08-25",
        "total_tasks": actual_total,
        "per_workflow": per_dir_counts,
        "issues": issues,
        "warnings": warns,
        "feature_usage": dict(feature_usage),
        "navigation_tasks": nav_tasks,
    }
    outp = PROJECT_ROOT / "experiments" / "results" / "rnadesign210_audit.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON report -> {outp}")
    return 1 if issues else 0


def regategy_fallback() -> set[str]:
    """Fallback tool-name source if list_specs API differs."""
    from agent_core import tool_registry as tr
    names: set[str] = set()
    for attr in dir(tr.ToolRegistry):
        pass
    reg = tr.ToolRegistry()
    for name in dir(reg):
        if name.startswith("list") or name.startswith("get"):
            try:
                val = getattr(reg, name)()
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, str):
                            names.add(item)
                        elif isinstance(item, dict) and "name" in item:
                            names.add(item["name"])
            except Exception:
                continue
    return names


if __name__ == "__main__":
    sys.exit(main())
