#!/usr/bin/env python3
"""Apply the 2026-08-25 RNADesign-210 data fixes (audit findings A/B).

1. IRES tasks: machine-specific absolute ``sequence_filepath`` → repo-relative
   (``resolve_project_path`` resolves repo-relative paths).
2. Category taxonomy: normalize the 14 ad-hoc values to the manifest's own
   documented 3-value scheme ``basic | edge | full`` (biology stays in
   ``source``/``description``):
     - edgecase, boundary → edge
     - comparison, vaccine, therapeutic, reporter, prokaryotic, fungal,
       algae, archaea (all real-biology full-length targets) → full
     - 02_006 (synthetic prokaryotic test) → edge
     - 02_010 edgecase keeps edge (boundary case by design, real sequence)
3. Full-length rubrics: drop the stale ``junction_mfe_threshold`` key (junction
   repair removed, DECISIONS (b); no current metric consumes it).
4. expected_tool_chain: drop the deleted ``shuffle_cds_junction_codons`` tool
   (regrounding against live traces happens in the benchmark driver).
5. Regenerate ``benchmark_manifest.json`` with true per-workflow counts and a
   BMC-free task_categories description; sync per-directory manifests.

Idempotent: running twice changes nothing the second time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_ROOT = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Platform" / "tasks"
BENCH_MANIFEST = TASKS_ROOT.parent / "benchmark_manifest.json"

REPO_PREFIX = "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/"

# task_id → final category, for everything not already in {basic, edge, full}
CATEGORY_OVERRIDES: dict[str, str] = {
    # 02 full-length: real biology → full, synthetic host tests → edge
    "02_full_length_mrna_design_002_vaccine_spike": "full",
    "02_full_length_mrna_design_003_therapeutic_epo": "full",
    "02_full_length_mrna_design_004_reporter_gfp": "full",
    "02_full_length_mrna_design_005_a1at": "full",
    "02_full_length_mrna_design_006_betagal": "edge",  # synthetic prokaryotic test
    "02_full_length_mrna_design_007_transferrin": "full",
    "02_full_length_mrna_design_008_growth_hormone": "full",
    "02_full_length_mrna_design_009_ovalbumin": "full",
    "02_full_length_mrna_design_010_edgecase": "edge",
    "02_full_length_mrna_design_011_penicylium_model": "full",
    "02_full_length_mrna_design_012_chlamydomonas_model": "full",
    "02_full_length_mrna_design_013_thermococcus_model": "full",
    "02_full_length_mrna_design_014_bsubtilis_cai": "full",
    "02_full_length_mrna_design_015_cho_cai": "full",
    "02_full_length_mrna_design_016_worm_cai": "full",
    "02_full_length_mrna_design_017_zebrafish_cai": "full",
    "02_full_length_mrna_design_019_gc_only": "full",  # real GFP sequence
    "02_full_length_mrna_design_020_mouse_cai": "full",
    "02_full_length_mrna_design_021_rat_cai": "full",
    "02_full_length_mrna_design_022_fly_cai": "full",
    # 02 edgecase → edge
    "02_full_length_mrna_design_018_fold_only": "edge",
}

WORKFLOW_NAMES = {
    "01_mrna_cds_design": "mrna_cds_design",
    "02_full_length_mrna_design": "full_length_mrna_design",
    "03_mrna_sequence_scoring": "mrna_sequence_scoring",
    "04_sirna_design": "sirna_design",
    "05_sgrna_design": "sgrna_design",
    "06_rna_secondary_structure": "rna_secondary_structure_design",
    "07_rna_tertiary_structure": "rna_tertiary_structure_design",
    "08_rna_aptamer_design": "rna_aptamer_design",
    "09_rna_small_molecule": "rna_small_molecule_interaction",
    "10_aso_target_screening": "aso_target_screening",
    "11_ires_prediction": "ires_prediction",
}

DELETED_TOOLS = {"shuffle_cds_junction_codons"}


def main() -> int:
    n_path = n_cat = n_rubric = n_chain = 0
    per_dir_counts: dict[str, int] = {}
    categories_seen: set[str] = set()

    for wf_dir in sorted(TASKS_ROOT.iterdir()):
        if not wf_dir.is_dir():
            continue
        task_files = sorted(p for p in wf_dir.glob("*.json") if p.name != "dataset_manifest.json")
        per_dir_counts[wf_dir.name] = len(task_files)
        cats: dict[str, int] = {}

        for tf in task_files:
            task = json.loads(tf.read_text(encoding="utf-8"))
            tid = task["task_id"]
            changed = False

            # 1. IRES absolute paths → repo-relative
            inp = task.get("input") or {}
            for key in ("sequence_filepath",):
                val = inp.get(key)
                if isinstance(val, str) and val.startswith(REPO_PREFIX):
                    inp[key] = val[len(REPO_PREFIX):]
                    n_path += 1
                    changed = True

            # 2. category normalization
            cat = task.get("category")
            if cat not in {"basic", "edge", "full"}:
                new = CATEGORY_OVERRIDES.get(tid)
                if new is None:
                    # generic rules for stragglers
                    new = "edge" if cat in {"edgecase", "boundary"} else "full"
                task["category"] = new
                cat = new
                n_cat += 1
                changed = True
            cats[cat] = cats.get(cat, 0) + 1
            categories_seen.add(cat)

            # 3. stale rubric keys
            rub = task.get("evaluation_rubric")
            if isinstance(rub, dict) and "junction_mfe_threshold" in rub:
                del rub["junction_mfe_threshold"]
                n_rubric += 1
                changed = True

            # 4. deleted tools in expected chains
            chain = task.get("expected_tool_chain")
            if chain:
                kept = [t for t in chain if t not in DELETED_TOOLS]
                if len(kept) != len(chain):
                    task["expected_tool_chain"] = kept
                    n_chain += 1
                    changed = True

            if changed:
                tf.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # per-directory manifest sync
        dm_path = wf_dir / "dataset_manifest.json"
        dm = json.loads(dm_path.read_text(encoding="utf-8")) if dm_path.exists() else {}
        dm["task_count"] = len(task_files)
        dm["category_counts"] = dict(sorted(cats.items()))
        dm_path.write_text(json.dumps(dm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # top-level manifest regeneration (preserve structure, update values)
    bm = json.loads(BENCH_MANIFEST.read_text(encoding="utf-8"))
    for wf in bm["workflows"]:
        wf["task_count"] = per_dir_counts[wf["id"]]
    bm["total_tasks"] = sum(per_dir_counts.values())
    bm["task_categories"] = {
        "basic": "Canonical inputs for smoke testing",
        "edge": "Boundary-case, mixed-modality or parameter-sweep inputs",
        "full": "Real biological sequences/structures (UniProt proteins, viral genomes, PDB structures)",
    }
    bm["description"] = (
        "Platform coverage benchmark (a.k.a. RNADesign-210): 11 workflows × "
        "curated canonical/edge/full-biology tasks; every task input passes the "
        "current workflow Input models (audited 2026-08-25)."
    )
    bm["last_audited"] = "2026-08-25"
    BENCH_MANIFEST.write_text(json.dumps(bm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"fixed: {n_path} absolute paths, {n_cat} categories, {n_rubric} stale rubric keys, {n_chain} stale tool chains")
    print(f"categories now: {sorted(categories_seen)}")
    print(f"total tasks: {sum(per_dir_counts.values())}")
    for d, c in per_dir_counts.items():
        print(f"  {d}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
