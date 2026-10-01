#!/usr/bin/env python3
"""Build the v4 public data package (2026-10-01, user-directed final-form reorganization).

v4 reorganizes the deposit around the eight final-form benchmark datasets of the
paper's Methods ("Benchmark datasets and anchor sets"), aligned with the same-day
Methods and Data-availability rewrites:

    01_RNADesign-210                    <- v3 benchmarks/RNA-BioBench-Platform
    02_ProcessAware-31-sessions         <- v3 benchmarks/RNA-BioBench-ProcessAware
                                           + v3 pa_benchmarks.json (session registry)
    03_SelectionPool-5-proteins         <- NEW (absent from v3): the five selection-pool
                                           proteins (A1AT, Insulin, EPO, GFP, IL-2),
                                           byte-identical target copies from the
                                           20-target full-length mRNA benchmark
    04_FullLength-mRNA-25-targets       <- pre_registered_20 (v3 FullLength-mRNA)
                                           + deployment_cohort_5 (from the cohort register)
                                           + pooled dataset_manifest.json (per-target
                                           provenance)
    05_Aptamer-26-targets               <- pre_registered_20 (v3 Aptamer)
                                           + deployment_cohort_6 (copies from the expanded
                                           pool, their definitive records) + manifest
    06_Aptamer-budget-sweep-39-targets  <- expanded_19 (v3 Aptamer-Expanded)
                                           + pooled 39-target manifest cross-referencing 05
    07_Aptamer-claim-audit-45-tasks     <- v3 claim_audit_tasks e5 files
    08_FullLength-claim-audit-20-tasks  <- v3 claim_audit_tasks e18 file

external_anchors / self_model / baseline_evidence / MODEL_API_USAGE.md are carried
byte-identical from v3. MANIFEST.sha256 is regenerated over every file. The
deployment-cohort register README is preserved as cohort_README.md inside both
cohort directories.

Uploaded to Zenodo draft 22736194 the same day (v3 deleted by file id, v4 direct
PUT 201, metadata description updated, read-back md5 verified); see
upload_status.md.
"""

import hashlib
import json
import shutil
from pathlib import Path

SRC = Path(__file__).parent / "RNADesignAgent_paper_data_v3"
DST = Path(__file__).parent / "RNADesignAgent_paper_data_v4"
SELECTION_POOL = ["A1AT", "Insulin", "EPO", "GFP", "IL-2"]


def cp(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def build() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    B = DST / "benchmarks"
    B.mkdir(parents=True)

    cp(SRC / "benchmarks/RNA-BioBench-Platform", B / "01_RNADesign-210")
    cp(SRC / "benchmarks/RNA-BioBench-ProcessAware", B / "02_ProcessAware-31-sessions")
    cp(SRC / "pa_benchmarks.json", B / "02_ProcessAware-31-sessions/pa_benchmarks.json")

    sel = B / "03_SelectionPool-5-proteins"
    (sel / "targets").mkdir(parents=True)
    for name in SELECTION_POOL:
        cp(SRC / f"benchmarks/RNA-BioBench-FullLength-mRNA/targets/{name}.json",
           sel / f"targets/{name}.json")
    json.dump({
        "dataset_name": "SelectionPool-5-proteins",
        "final_form_of": "the five-protein selection pool of the paper "
                         "(Methods, Benchmark datasets; Fig. 5a)",
        "targets": SELECTION_POOL,
        "provenance": "Five therapeutic-protein targets measured under the legacy "
                      "selection-step pool protocol (Supplementary Methods M3); all five "
                      "are members of the 20-target full-length mRNA pre-registered "
                      "benchmark, and the target files are byte-identical copies of the "
                      "corresponding files in "
                      "04_FullLength-mRNA-25-targets/pre_registered_20/targets/.",
    }, open(sel / "dataset_manifest.json", "w"), indent=2)

    d4 = B / "04_FullLength-mRNA-25-targets"
    cp(SRC / "benchmarks/RNA-BioBench-FullLength-mRNA", d4 / "pre_registered_20")
    mreg = json.load(open(SRC / "benchmarks/deployment_cohorts/mrna_targets.json"))
    c5 = d4 / "deployment_cohort_5"
    c5.mkdir()
    for t in mreg["targets"]:
        json.dump(t, open(c5 / f"{t['gene']}.json", "w"), indent=2)
    cp(SRC / "benchmarks/deployment_cohorts/mrna_targets.json",
       c5 / "deployment_cohort_register.json")
    cp(SRC / "benchmarks/deployment_cohorts/README.md", c5 / "cohort_README.md")
    base20 = sorted(p.stem for p in (d4 / "pre_registered_20/targets").glob("*.json"))
    json.dump({
        "dataset_name": "FullLength-mRNA-25-targets",
        "final_form_of": "the 25-target pooled full-length mRNA set of the paper (Fig. 5b-d)",
        "composition": [
            {"target": t, "source": "pre_registered_benchmark",
             "path": f"pre_registered_20/targets/{t}.json"} for t in base20]
        + [{"target": t["gene"], "source": "deployment_cohort",
            "path": f"deployment_cohort_5/{t['gene']}.json"} for t in mreg["targets"]],
        "note": "Per-target provenance (pre-registered 20-target benchmark versus "
                "five-target deployment cohort) is recorded per entry; the pooled "
                "analyses of the paper use all 25 targets.",
    }, open(d4 / "dataset_manifest.json", "w"), indent=2)

    d5 = B / "05_Aptamer-26-targets"
    cp(SRC / "benchmarks/RNA-BioBench-Aptamer", d5 / "pre_registered_20")
    areg = json.load(open(SRC / "benchmarks/deployment_cohorts/aptamer_targets.json"))
    c6 = d5 / "deployment_cohort_6"
    c6.mkdir()
    for t in areg["targets"]:
        cp(SRC / f"benchmarks/RNA-BioBench-Aptamer-Expanded/targets/{t['target_id']}.json",
           c6 / f"{t['target_id']}.json")
    cp(SRC / "benchmarks/deployment_cohorts/aptamer_targets.json",
       c6 / "deployment_cohort_register.json")
    cp(SRC / "benchmarks/deployment_cohorts/README.md", c6 / "cohort_README.md")
    base20a = sorted(p.stem for p in (d5 / "pre_registered_20/targets").glob("*.json"))
    json.dump({
        "dataset_name": "Aptamer-26-targets",
        "final_form_of": "the 26-target pooled aptamer set of the paper (Fig. 5e-g)",
        "composition": [
            {"target": t, "source": "pre_registered_benchmark",
             "path": f"pre_registered_20/targets/{t}.json"} for t in base20a]
        + [{"target": t["target_id"], "source": "deployment_cohort",
            "path": f"deployment_cohort_6/{t['target_id']}.json"} for t in areg["targets"]],
        "note": "The six deployment-cohort targets are members of the expanded "
                "19-target pool (see 06); their definitive records live there and the "
                "copies here are byte-identical.",
    }, open(d5 / "dataset_manifest.json", "w"), indent=2)

    d6 = B / "06_Aptamer-budget-sweep-39-targets"
    cp(SRC / "benchmarks/RNA-BioBench-Aptamer-Expanded", d6 / "expanded_19")
    exp19 = sorted(p.stem for p in (d6 / "expanded_19/targets").glob("*.json"))
    json.dump({
        "dataset_name": "Aptamer-budget-sweep-39-targets",
        "final_form_of": "the 39-target aptamer budget-sweep pool of the paper "
                         "(Supplementary Fig. S2)",
        "composition": [
            {"target": t, "source": "pre_registered_benchmark",
             "path": f"../05_Aptamer-26-targets/pre_registered_20/targets/{t}.json"}
            for t in base20a]
        + [{"target": t, "source": "expanded_pool",
            "path": f"expanded_19/targets/{t}.json"} for t in exp19],
        "note": "The 39-target pool combines the 20-target pre-registered benchmark "
                "with the 19-target expanded pool; the six deployment-cohort targets "
                "of 05 are among the expanded 19.",
    }, open(d6 / "dataset_manifest.json", "w"), indent=2)

    a7 = B / "07_Aptamer-claim-audit-45-tasks"
    a7.mkdir()
    cp(SRC / "benchmarks/claim_audit_tasks/e5_audit_tasks.json", a7 / "e5_audit_tasks.json")
    cp(SRC / "benchmarks/claim_audit_tasks/e5_legacy_audit_tasks_reference.json",
       a7 / "e5_legacy_audit_tasks_reference.json")
    open(a7 / "README.md", "w").write(
        "# Aptamer claim-audit set (45 tasks)\n\n"
        "`e5_audit_tasks.json` — the 45-task aptamer claim-overreach audit set: 24\n"
        "trusted-deterministic tasks with exactly recomputable ground truth and 21\n"
        "untrusted-predictor ranking/screening tasks spanning the nine-target anchor set. "
        "Built\nfrom an earlier registered 20-task set carried byte-verbatim plus "
        "pre-registered,\nassertion-checked extension rules (the legacy reference is "
        "retained alongside as\n`e5_legacy_audit_tasks_reference.json`). Consumed by the "
        "ungated-control and\ngated-treatment conditions of the paper's gating experiments "
        "(Supplementary Methods M2).\n")
    a8 = B / "08_FullLength-claim-audit-20-tasks"
    a8.mkdir()
    cp(SRC / "benchmarks/claim_audit_tasks/e18_audit_tasks_mrna.json",
       a8 / "e18_audit_tasks_mrna.json")
    open(a8 / "README.md", "w").write(
        "# Full-length mRNA claim-audit set (20 tasks)\n\n"
        "`e18_audit_tasks_mrna.json` — the 20-task full-length mRNA audit set: ten\n"
        "trusted-deterministic and ten untrusted-predictor tasks built from the 20-target\n"
        "full-length benchmark's real design assets (production CDS deliveries, "
        "top-ranked\nfull-length constructs, live predictor scores). Consumed by the "
        "two-condition gating\nreplication of the paper (Supplementary Methods M2).\n")

    cp(SRC / "benchmarks/external_anchors", B / "external_anchors")
    cp(SRC / "self_model", DST / "self_model")
    cp(SRC / "baseline_evidence", DST / "baseline_evidence")
    cp(SRC / "MODEL_API_USAGE.md", DST / "MODEL_API_USAGE.md")

    open(DST / "README.md", "w").write(
        "# RNADesignAgent — Research Data Deposit (v4.0)\n\n"
        "Data supporting the manuscript \"A multi-agent system for RNA design with\n"
        "capability-gated prediction and constraint-navigated generation\" (system name\n"
        "RNADesignAgent; benchmark name RNADesign-210).\n\n"
        "v4.0 reorganizes the deposit around the eight final-form benchmark datasets of "
        "the\npaper's Methods (Benchmark datasets and anchor sets). Each pooled dataset "
        "carries a\n`dataset_manifest.json` recording per-target provenance "
        "(pre-registered benchmark\nversus deployment cohort versus expanded pool).\n\n"
        "## Contents\n\n"
        "### The eight benchmark datasets (benchmarks/)\n\n"
        "1. `01_RNADesign-210` — the 210-task system benchmark covering the eleven "
        "workflows.\n"
        "2. `02_ProcessAware-31-sessions` — the 31-session process-aware benchmark (the "
        "task set\n   of the external-baseline comparison; includes the session "
        "registry).\n"
        "3. `03_SelectionPool-5-proteins` — the five-protein selection pool (A1AT, "
        "insulin, EPO,\n   GFP, IL-2).\n"
        "4. `04_FullLength-mRNA-25-targets` — the 25-target pooled full-length mRNA set\n"
        "   (pre-registered 20 + deployment cohort 5).\n"
        "5. `05_Aptamer-26-targets` — the 26-target pooled aptamer set (pre-registered "
        "20 +\n   deployment cohort 6).\n"
        "6. `06_Aptamer-budget-sweep-39-targets` — the 39-target budget-sweep pool\n"
        "   (pre-registered 20 + expanded 19).\n"
        "7. `07_Aptamer-claim-audit-45-tasks` — the 45-task aptamer claim-audit set.\n"
        "8. `08_FullLength-claim-audit-20-tasks` — the 20-task full-length mRNA "
        "claim-audit set.\n\n"
        "### Reference and evidence assets\n\n"
        "- `benchmarks/external_anchors/` — the external anchor sets used for "
        "capability\n  profiling and the biological-validity comparisons (wild-type CDSs "
        "with the 200 random\n  synonymous controls, aptamer binder and negative groups, "
        "measured-MRL 5'UTR\n  libraries, IRES anchor set, small-molecule binder and "
        "non-binder pairs,\n  vaccine-mRNA assemblies, mRNA-stability set).\n"
        "- `self_model/` — the packaged capability map with its generator.\n"
        "- `baseline_evidence/` — the frozen records of the comparison against external "
        "agent\n  baselines (bare-model and same-tool agent-loop campaign records; "
        "three-condition\n  comparison output).\n"
        "- `MODEL_API_USAGE.md` — the per-experiment model-usage register.\n\n"
        "`MANIFEST.sha256` lists the SHA-256 checksum of every file.\n")

    files = sorted(p for p in DST.rglob("*")
                   if p.is_file() and p.name != "MANIFEST.sha256")
    with open(DST / "MANIFEST.sha256", "w") as f:
        for p in files:
            f.write(hashlib.sha256(open(p, "rb").read()).hexdigest()
                    + "  " + str(p.relative_to(DST)) + "\n")
    print(f"v4 built: {len(files) + 1} files under {DST}")


if __name__ == "__main__":
    build()
