#!/usr/bin/env python3
"""Fig 2a/3c null generator: WT, random-synonymous, and CAI-only CDS baselines.

Implements `docs/MANUSCRIPT.md` §4.2 step 2 for the 20 Fig-3 targets:

- Arm `wt`            — wild-type CDS from `data/benchmarks/external_anchors/wt_cds/`
- Arm `random_syn`    — 10 random synonymous CDS per protein (uniform codon choice,
                        seed derived from target id; stop codon excluded)
- Arm `cai_only`      — `mrna_cds_design` with design_tool="lineardesign", lambda_value=0
                        (pure CAI optimization, no MFE term)

WT + random-synonymous sequences are scored with the `mrna_sequence_scoring`
workflow (one batched run per target, `sequences` list). The CAI-only arm runs
the full design workflow. Records go to
`experiments/results/fig2_cds_nulls.jsonl`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/make_cds_nulls.py \
        [--targets T1,T2] [--skip-design] [--limit N] [--timeout SEC]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT, run_task_dict  # noqa: E402

BENCH = PROJECT_ROOT / "data" / "benchmarks"
TARGETS_DIR = BENCH / "RNA-BioBench-FullLength-mRNA" / "targets"
WT_DIR = BENCH / "external_anchors" / "wt_cds"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig2_cds_nulls.jsonl"

CODONS: dict[str, list[str]] = {}
_GENETIC = {
    "F": ["TTT", "TTC"], "L": ["TTA", "TTG", "CTT", "CTC", "CTA", "CTG"],
    "I": ["ATT", "ATC", "ATA"], "M": ["ATG"], "V": ["GTT", "GTC", "GTA", "GTG"],
    "S": ["TCT", "TCC", "TCA", "TCG", "AGT", "AGC"], "P": ["CCT", "CCC", "CCA", "CCG"],
    "T": ["ACT", "ACC", "ACA", "ACG"], "A": ["GCT", "GCC", "GCA", "GCG"],
    "Y": ["TAT", "TAC"], "H": ["CAT", "CAC"], "Q": ["CAA", "CAG"], "N": ["AAT", "AAC"],
    "K": ["AAA", "AAG"], "D": ["GAT", "GAC"], "E": ["GAA", "GAG"],
    "C": ["TGT", "TGC"], "W": ["TGG"], "R": ["CGT", "CGC", "CGA", "CGG", "AGA", "AGG"],
    "G": ["GGT", "GGC", "GGA", "GGG"],
}
CODONS = _GENETIC


def read_fasta_seq(path: Path) -> str:
    return "".join(
        line.strip() for line in path.read_text().splitlines() if not line.startswith(">")
    ).upper().replace("U", "T")


def random_synonymous(protein: str, rng: random.Random) -> str:
    return "".join(rng.choice(CODONS[aa]) for aa in protein)


def extract_candidate_scores(record: dict) -> list[dict]:
    """Pull (sequence, cai, mfe, gc, total_score) per candidate from a scoring record."""
    out = []
    for c in record.get("candidates") or []:
        m = c.get("metrics") or {}
        s = c.get("scores") or {}
        out.append({
            "sequence": c.get("sequence"),
            "cai_score": m.get("cai_score", s.get("cai_score")),
            "mfe_kcal_per_mol": m.get("mfe_kcal_per_mol", s.get("mfe_kcal_per_mol")),
            "mfe_per_nt": m.get("mfe_per_nt", s.get("mfe_per_nt")),
            "gc_content": m.get("gc_content", s.get("gc_content")),
            "total_score": c.get("total_score"),
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--targets", default=None, help="comma-separated target ids (default: all 20)")
    parser.add_argument("--skip-design", action="store_true", help="only score WT + random synonymous")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    target_files = sorted(TARGETS_DIR.glob("*.json"))
    if args.targets:
        wanted = set(args.targets.split(","))
        target_files = [p for p in target_files if p.stem in wanted]
    if args.limit:
        target_files = target_files[: args.limit]

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)

    for i, tf in enumerate(target_files, 1):
        meta = json.loads(tf.read_text())
        target_id = meta["target_id"]
        protein = meta["protein_sequence"].upper()
        cai_species = meta.get("species_for_codon_optimization") or "human"
        wt_fa = WT_DIR / f"{target_id}.fa"
        if not wt_fa.exists():
            print(f"[{i}/{len(target_files)}] {target_id}: MISSING wt_cds fasta, skipped")
            continue
        wt = read_fasta_seq(wt_fa)
        rng = random.Random(f"cdsnull_{target_id}")
        randoms = [random_synonymous(protein, rng) for _ in range(10)]

        print(f"[{i}/{len(target_files)}] {target_id}: scoring WT + 10 random-synonymous ...", flush=True)
        seqs = [wt, *randoms]
        task = {
            "task_id": f"null_{target_id}_score",
            "workflow": "mrna_sequence_scoring",
            "category": "null_scoring",
            "description": f"WT + random synonymous scoring for {target_id}",
            "input": {"sequences": seqs, "cai_species": cai_species},
            "evaluation_rubric": None,
        }
        rec = run_task_dict(task, timeout=args.timeout, env=env, session_prefix="fig2null",
                            keep_candidate_sequences=True)
        cand_scores = extract_candidate_scores(rec)
        by_seq = {c["sequence"]: c for c in cand_scores if c.get("sequence")}
        arms = [("wt", wt)] + [("random_syn", s) for s in randoms]
        for rep, (arm, seq) in enumerate(arms):
            cs = by_seq.get(seq.replace("T", "U")) or by_seq.get(seq) or {}
            out = {
                "target_id": target_id,
                "arm": arm,
                "rep": 0 if arm == "wt" else rep - 1,
                "workflow": "mrna_sequence_scoring",
                "success": rec["success"] and bool(cs),
                "error": rec.get("error") if not cs else None,
                "cai_species": cai_species,
                "length_nt": len(seq),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                **{k: cs.get(k) for k in ("cai_score", "mfe_kcal_per_mol", "mfe_per_nt", "gc_content", "total_score")},
            }
            with args.output.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(out, ensure_ascii=False) + "\n")

        if args.skip_design:
            continue
        print(f"           {target_id}: CAI-only design (lambda=0) ...", flush=True)
        task = {
            "task_id": f"null_{target_id}_cai_only",
            "workflow": "mrna_cds_design",
            "category": "null_design",
            "description": f"CAI-only LinearDesign for {target_id}",
            "input": {
                "protein_sequence": protein,
                "design_tool": "lineardesign",
                "lambda_value": 0.0,
                "cai_species": cai_species,
            },
            "evaluation_rubric": None,
        }
        rec = run_task_dict(task, timeout=args.timeout, env=env, session_prefix="fig2null",
                            keep_candidate_sequences=True)
        for c in extract_candidate_scores(rec):
            out = {
                "target_id": target_id,
                "arm": "cai_only",
                "rep": 0,
                "workflow": "mrna_cds_design",
                "success": rec["success"],
                "error": rec.get("error"),
                "cai_species": cai_species,
                "length_nt": len(protein) * 3,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                **{k: c.get(k) for k in ("cai_score", "mfe_kcal_per_mol", "mfe_per_nt", "gc_content", "total_score")},
            }
            with args.output.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"\nNull records -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
