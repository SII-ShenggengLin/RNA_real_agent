#!/usr/bin/env python3
"""Fig 2h/2i literature panels: known-binder and known-IRES validation.

Implements `docs/MANUSCRIPT.md` §4.2 step 3:

- Panel `ires`       — run `ires_prediction` (mode 0, full-sequence scoring) on the
                       curated positives (`ires_positive.fa`) and random-UTR negatives
                       (`utr_negative.fa`); collect the best IRES probability per
                       sequence for the AUROC analysis.
- Panel `small_mol`  — run `rna_small_molecule_interaction` on the 8 curated
                       binder/non-binder pairs (`pairs.json`); collect `total_score`.

Output: `experiments/results/fig2_literature_panels.jsonl`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_literature_panels.py \
        [--panel ires|small_mol|all] [--limit N] [--timeout SEC]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT, run_task_dict  # noqa: E402

ANCHORS = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig2_literature_panels.jsonl"


def parse_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header, buf = None, []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(buf)))
            header, buf = line[1:].strip(), []
        else:
            buf.append(line.strip())
    if header is not None:
        records.append((header, "".join(buf)))
    return records


def run_ires_panel(env: dict[str, str], timeout: int, limit: int | None, out_fh) -> None:
    panels = [
        ("positive", ANCHORS / "ires" / "ires_positive.fa"),
        ("negative", ANCHORS / "ires" / "utr_negative.fa"),
    ]
    seq_dir = PROJECT_ROOT / "workspace" / "fig2lit_ires_seqs"
    seq_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for label, fasta in panels:
        for header, seq in parse_fasta(fasta):
            n += 1
            if limit and n > limit:
                return
            seq_id = header.split()[0].replace("|", "_")[:60]
            seq_file = seq_dir / f"{label}_{seq_id}.fa"
            seq_file.write_text(f">{header}\n{seq}\n", encoding="utf-8")
            rel_path = seq_file.relative_to(PROJECT_ROOT)
            task = {
                "task_id": f"lit_ires_{label}_{seq_id}",
                "workflow": "ires_prediction",
                "category": "literature_panel",
                "description": f"IRES {label}: {header[:60]}",
                # mode 2 (sliding window) is the workflow's intended operating mode;
                # threshold 0.0 keeps every window so the AUROC uses raw probabilities.
                "input": {
                    "sequence_filepath": str(rel_path),
                    "iresfinder_mode": 2,
                    "probability_threshold": 0.0,
                    "window_size": 174,
                    "step_size": 50,
                },
                "evaluation_rubric": None,
            }
            rec = run_task_dict(task, timeout=timeout, env=env, session_prefix="fig2lit")
            all_probs = []
            for c in rec.get("candidates") or []:
                v = (c.get("scores") or {}).get("ires_probability")
                if isinstance(v, (int, float)):
                    all_probs.append(round(float(v), 4))
            all_probs.sort(reverse=True)
            out = {
                "panel": "ires",
                "label": label,
                "seq_id": seq_id,
                "length_nt": len(seq),
                "params": {"iresfinder_mode": 2, "probability_threshold": 0.0,
                           "window_size": 174, "step_size": 50},
                "success": rec["success"],
                "error": rec.get("error"),
                "elapsed_seconds": rec.get("elapsed_seconds"),
                "best_ires_probability": all_probs[0] if all_probs else None,
                "all_window_probs": all_probs[:20],
                "n_candidates": rec.get("candidate_count"),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            out_fh.write(json.dumps(out, ensure_ascii=False) + "\n")
            out_fh.flush()
            print(f"  ires/{label}/{seq_id}: prob={out['best_ires_probability']} "
                  f"({'OK' if rec['success'] else rec.get('error')})", flush=True)


def run_small_mol_panel(env: dict[str, str], timeout: int, limit: int | None, out_fh) -> None:
    pairs = json.loads((ANCHORS / "small_molecule" / "pairs.json").read_text())
    for i, pair in enumerate(pairs, 1):
        if limit and i > limit:
            return
        task = {
            "task_id": f"lit_smol_{pair['pair_id']}",
            "workflow": "rna_small_molecule_interaction",
            "category": "literature_panel",
            "description": f"{pair['rna_name']} x {pair['molecule_name']} ({pair['expected']})",
            "input": {"rna_sequence": pair["rna_sequence"], "smiles": pair["smiles"]},
            "evaluation_rubric": None,
        }
        rec = run_task_dict(task, timeout=timeout, env=env, session_prefix="fig2lit")
        best = rec.get("best_candidate") or {}
        out = {
            "panel": "small_mol",
            "pair_id": pair["pair_id"],
            "rna_name": pair["rna_name"],
            "molecule_name": pair["molecule_name"],
            "expected": pair["expected"],
            "negative_class": pair.get("negative_class", "near_cognate" if pair["expected"] == "non_binder" else None),
            "success": rec["success"],
            "error": rec.get("error"),
            "elapsed_seconds": rec.get("elapsed_seconds"),
            "total_score": best.get("total_score"),
            "scores": best.get("scores"),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        out_fh.write(json.dumps(out, ensure_ascii=False) + "\n")
        out_fh.flush()
        print(f"  smol/{pair['pair_id']}: score={out['total_score']} "
              f"({'OK' if rec['success'] else rec.get('error')})", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--panel", choices=["ires", "small_mol", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as out_fh:
        if args.panel in ("ires", "all"):
            print("[panel] ires", flush=True)
            run_ires_panel(env, args.timeout, args.limit, out_fh)
        if args.panel in ("small_mol", "all"):
            print("[panel] small_mol", flush=True)
            run_small_mol_panel(env, args.timeout, args.limit, out_fh)
    print(f"\nPanel records -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
