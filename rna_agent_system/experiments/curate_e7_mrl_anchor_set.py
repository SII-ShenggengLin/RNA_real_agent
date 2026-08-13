#!/usr/bin/env python3
"""Curate the E7 measured-MRL anchor set (2026-08-11).

Anchor set for E7: capability profiling of the mRNA workflow's expression
oracle (GEMORNA 5'UTR MRL predictor, service :8004) on measured-MRL anchor
sets — the mRNA-side counterpart of the E1 aptamer-oracle profiling.
Pre-registration: `experiments/run_e7_mrna_oracle_profiling.py` docstring.

SOURCE DATA (raw files cached in experiments/lit_cache/mrl/, fetched
2026-08-11, md5-verified copies of the GEO supplementary files):

  Sample et al. 2019, "Human 5' UTR design and variant effect prediction
  from a massively parallel translation assay", Nat Biotechnol 37:803-809;
  GEO GSE114002 (MPRA polysome profiling, EGFP reporter, unmodified RNA,
  HEK293T; `rl` column = measured mean ribosome load, MRL).

  - GSM3130435_egfp_unmod_1.csv.gz (63.7 MB, 326,033 rows): random 50-nt
    5'UTR library. https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM3130nnn/
    GSM3130435/suppl/GSM3130435_egfp_unmod_1.csv.gz
  - GSM4084997_varying_length_25to100.csv.gz (15.4 MB, 106,530 rows):
    designed varying-length (25-100 nt) library with a `set` column:
    random (87,000) / human (16,739, human endogenous UTR-derived) /
    controls (1,017) / with_uaugs (900) / no_uaugs (874).
    https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM4084nnn/GSM4084997/suppl/
    GSM4084997_varying_length_25to100.csv.gz

FAMILIES (the `set` column justifies splitting GSM4084997 by content):

  1. sample2019_egfp_random50      GSM3130435, all rows (random 50-nt).
     IN-TRAINING-DISTRIBUTION for MRL models trained on this assay
     (GEMORNA's 5'UTR MRL head was trained on the Sample-2019 random-50
     library) — registered in known_limitations.
  2. sample2019_varying_length_random   GSM4084997, set == "random".
  3. sample2019_varying_length_human    GSM4084997, set == "human".

EXCLUDED subsets (registered, not in the set): GSM4084997 `controls`
(1,017 rows, 27 pass the read filter), `with_uaugs` (900, 17) and
`no_uaugs` (874, 17) are small engineered uAUG-manipulation/control
panels, not natural-distribution libraries; after filtering they are far
below the 60+60+120 selection protocol and would confound the
screening/ranking gates with a designed perturbation contrast.

SELECTION PROTOCOL (per family, deterministic; seed 0 recorded per
protocol — selection is purely rank-based, no RNG is consumed):

  1. Filter: total_reads >= 1000; ACGT-only (uppercase DNA as printed).
  2. Dedupe by utr (keep the row with the highest total_reads; ties keep
     the first occurrence — file order is deterministic).  Both source
     files are in fact duplicate-free under this filter (checked 2026-08-11).
  3. Sort the filtered pool by (rl, utr) ascending -> rl rank 0..N-1.
  4. High tier = top 60 by rl (role "binder" — the screening positives);
     low tier = bottom 60 (role "negative").
  5. Ranking subset = 120 anchors evenly spaced across the pool's rl
     ranks (floor(i*(N-1)/119), i=0..119; asserted unique). Tier overlap
     is allowed: overlapping tier entries are flagged ranking_eligible
     in place; mid-pool picks enter as role "ranking_only"
     (screening analyses filter on role, ranking analyses on
     ranking_eligible, so the two never contaminate each other).

ASSERTIONS (ANCHORS.md §3 assertion-first pattern): n_entries ==
len(entries); no duplicate sequences; every high-tier rl strictly greater
than every low-tier rl (per family); length_nt == len(sequence) for every
entry; ranking subset size == 120 per family; 60 binder + 60 negative per
family; GSM4084997 `len` column == len(utr) row-level; GSM3130435 rows
all 50 nt. Generator is deterministic end-to-end: re-running reproduces
the JSON byte-for-byte.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/curate_e7_mrl_anchor_set.py
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIT_CACHE = PROJECT_ROOT / "experiments" / "lit_cache" / "mrl"
OUT = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "utr_mrl" / "e7_mrl_anchor_set.json"

MIN_READS = 1000
TIER_N = 60
RANKING_N = 120
SEED = 0  # recorded per protocol; selection is purely rank-based (no RNG consumed)

REFERENCE = ("Sample et al. 2019 Nat Biotechnol 37:803-809; GEO GSE114002 {gsm}; "
             "MPRA mean ribosome load")
KD_METHOD = "MPRA polysome profiling, EGFP reporter, unmodified RNA"

FAMILIES = [
    {
        "family": "sample2019_egfp_random50",
        "gsm": "GSM3130435",
        "file": "GSM3130435_egfp_unmod_1.csv.gz",
        "set_value": None,  # single-library file (all random 50-nt)
        "suffix": "egfp_random50",
        "blurb": "random 50-nt 5'UTR library",
        "expected_len": 50,
    },
    {
        "family": "sample2019_varying_length_random",
        "gsm": "GSM4084997",
        "file": "GSM4084997_varying_length_25to100.csv.gz",
        "set_value": "random",
        "suffix": "vl_random",
        "blurb": "random varying-length (25-100 nt) 5'UTR library",
        "expected_len": None,
    },
    {
        "family": "sample2019_varying_length_human",
        "gsm": "GSM4084997",
        "file": "GSM4084997_varying_length_25to100.csv.gz",
        "set_value": "human",
        "suffix": "vl_human",
        "blurb": "human endogenous varying-length (25-100 nt) 5'UTR library",
        "expected_len": None,
    },
]

# Registered exclusions (not in the set) — see docstring.
EXCLUDED_SUBSETS = {
    "GSM4084997 set=controls": ("engineered control panel, not a natural-distribution library; "
                                "only 27 rows pass total_reads>=1000"),
    "GSM4084997 set=with_uaugs": ("designed uAUG-introduction perturbation panel; "
                                  "only 17 rows pass total_reads>=1000"),
    "GSM4084997 set=no_uaugs": ("designed uAUG-removal perturbation panel; "
                                "only 17 rows pass total_reads>=1000"),
}


def load_pool(spec: dict) -> list[dict]:
    """Filter (reads >= MIN_READS, ACGT-only) and dedupe by utr (max reads)."""
    path = LIT_CACHE / spec["file"]
    assert path.is_file(), f"missing cached source file: {path}"
    pool: dict[str, dict] = {}
    n_rows = n_reads = 0
    with gzip.open(path, "rt") as fh:
        for row in csv.DictReader(fh):
            if spec["set_value"] is not None and row.get("set") != spec["set_value"]:
                continue
            n_rows += 1
            utr = row["utr"].strip().upper()
            reads = int(float(row["total_reads"]))
            if reads < MIN_READS:
                continue
            n_reads += 1
            if set(utr) - set("ACGT"):
                continue
            # Row-level internal-consistency checks (assertion-first).
            if spec["expected_len"] is not None:
                assert len(utr) == spec["expected_len"], f"{spec['family']}: row length {len(utr)} != {spec['expected_len']}"
            if "len" in row and row["len"]:
                assert len(utr) == int(row["len"]), f"{spec['family']}: utr length != len column ({utr})"
            rl = float(row["rl"])
            prev = pool.get(utr)
            if prev is None or reads > prev["total_reads"]:
                pool[utr] = {"utr": utr, "total_reads": reads, "rl": rl}
    entries = sorted(pool.values(), key=lambda r: (r["rl"], r["utr"]))
    print(f"  {spec['family']}: {n_rows} rows -> {n_reads} reads>={MIN_READS} -> "
          f"{len(entries)} unique ACGT pool, rl [{entries[0]['rl']:.3f}, {entries[-1]['rl']:.3f}]",
          flush=True)
    assert len(entries) >= 2 * TIER_N + RANKING_N, f"{spec['family']}: pool too small ({len(entries)})"
    return entries


def select_family(spec: dict) -> list[dict]:
    pool = load_pool(spec)
    n = len(pool)
    fam, suffix, gsm = spec["family"], spec["suffix"], spec["gsm"]

    def make_entry(eid: str, name: str, rec: dict, role: str, rank: int) -> dict:
        return {
            "id": eid,
            "name": name,
            "target": fam,
            "sequence": rec["utr"],
            "alphabet": "dna",
            "length_nt": len(rec["utr"]),
            "kd_nm": None,
            "measured_mrl": rec["rl"],
            "total_reads": rec["total_reads"],
            "role": role,
            "ranking_eligible": False,
            "reference": REFERENCE.format(gsm=gsm),
            "kd_method": KD_METHOD,
            "rl_rank_in_pool": rank,
            "pool_size": n,
        }

    by_utr: dict[str, dict] = {}
    # High tier: top TIER_N by rl (hi01 = highest); low tier: bottom TIER_N.
    for i, rec in enumerate(reversed(pool[-TIER_N:]), 1):
        rank = n - TIER_N + (TIER_N - i)
        e = make_entry(f"hi{i:02d}_{suffix}",
                       f"{fam} high-MRL tier #{i} (rl {rec['rl']:.3f}, reads {rec['total_reads']})",
                       rec, "binder", rank)
        by_utr[rec["utr"]] = e
    for i, rec in enumerate(pool[:TIER_N], 1):
        e = make_entry(f"lo{i:02d}_{suffix}",
                       f"{fam} low-MRL tier #{i} (rl {rec['rl']:.3f}, reads {rec['total_reads']})",
                       rec, "negative", i - 1)
        by_utr[rec["utr"]] = e
    # Ranking subset: RANKING_N anchors evenly spaced across rl ranks.
    idxs = sorted({(i * (n - 1)) // (RANKING_N - 1) for i in range(RANKING_N)})
    assert len(idxs) == RANKING_N, f"{fam}: ranking index collision ({len(idxs)} != {RANKING_N})"
    n_rk_new = 0
    for rank in idxs:
        rec = pool[rank]
        e = by_utr.get(rec["utr"])
        if e is not None:
            e["ranking_eligible"] = True  # tier overlap, flagged in place (allowed)
            continue
        n_rk_new += 1
        by_utr[rec["utr"]] = make_entry(
            f"rk{n_rk_new:02d}_{suffix}",
            f"{fam} ranking anchor rl-rank {rank}/{n - 1} (rl {rec['rl']:.3f}, reads {rec['total_reads']})",
            rec, "ranking_only", rank)
        by_utr[rec["utr"]]["ranking_eligible"] = True

    entries = sorted(by_utr.values(),
                     key=lambda e: ({"binder": 0, "ranking_only": 1, "negative": 2}[e["role"]],
                                    -e["measured_mrl"], e["sequence"]))
    # ── per-family assertions ────────────────────────────────────────────
    high = [e for e in entries if e["role"] == "binder"]
    low = [e for e in entries if e["role"] == "negative"]
    ranking = [e for e in entries if e["ranking_eligible"]]
    assert len(high) == TIER_N and len(low) == TIER_N, f"{fam}: tier sizes wrong"
    assert len(ranking) == RANKING_N, f"{fam}: ranking subset {len(ranking)} != {RANKING_N}"
    assert min(e["measured_mrl"] for e in high) > max(e["measured_mrl"] for e in low), \
        f"{fam}: high/low tiers overlap in rl"
    assert len({e["sequence"] for e in entries}) == len(entries), f"{fam}: duplicate sequences"
    n_overlap = sum(1 for e in ranking if e["role"] != "ranking_only")
    print(f"  {fam}: {len(entries)} entries (60 binder / 60 negative / {len(entries) - 120} ranking_only; "
          f"ranking subset 120, tier overlap {n_overlap})", flush=True)
    return entries


def main() -> int:
    print("E7 anchor curation: loading filtered pools ...", flush=True)
    all_entries: list[dict] = []
    per_family: dict[str, int] = {}
    for spec in FAMILIES:
        fam_entries = select_family(spec)
        per_family[spec["family"]] = len(fam_entries)
        all_entries.extend(fam_entries)

    # ── global assertions ────────────────────────────────────────────────
    assert len({e["id"] for e in all_entries}) == len(all_entries), "duplicate entry ids"
    assert len({e["sequence"] for e in all_entries}) == len(all_entries), "duplicate sequences across families"
    for e in all_entries:
        assert e["length_nt"] == len(e["sequence"]), f"{e['id']}: length_nt mismatch"
        assert set(e["sequence"]) <= set("ACGT"), f"{e['id']}: non-ACGT"
        assert e["total_reads"] >= MIN_READS, f"{e['id']}: below read filter"

    out = {
        "description": (
            "E7 measured-MRL anchor set for capability profiling of the GEMORNA 5'UTR MRL "
            "expression oracle (mRNA-side counterpart of the E1 aptamer-oracle profiling). "
            "Three families from the Sample et al. 2019 MPRA (EGFP reporter, unmodified RNA, "
            "HEK293T): the random 50-nt library (in-training-distribution for MRL models "
            "trained on this assay), the varying-length random library, and the varying-length "
            "human-endogenous library. Per family: 60 high-MRL + 60 low-MRL screening tiers "
            "and a 120-anchor ranking subset evenly spaced across the read-filtered pool's "
            "rl ranks (tier overlap flagged in place)."),
        "curated": "2026-08-11",
        "convention": "DNA UTRs scored as RNA via T->U by the service",
        "preregistration": "experiments/run_e7_mrna_oracle_profiling.py docstring, E7 PRE-REGISTRATION (2026-08-11)",
        "selection_seed": SEED,
        "selection_protocol": {
            "filter": f"total_reads >= {MIN_READS}, ACGT-only, dedupe by utr (max total_reads)",
            "screening_tiers": f"top {TIER_N} by rl = role 'binder'; bottom {TIER_N} = role 'negative'",
            "ranking_subset": f"{RANKING_N} anchors evenly spaced across rl ranks (floor(i*(N-1)/{RANKING_N - 1})), ranking_eligible=true",
        },
        "n_entries": len(all_entries),
        "entries_per_family": per_family,
        "excluded_subsets": EXCLUDED_SUBSETS,
        "known_limitations": [
            "Reporter-context MRL: values are mean ribosome load of an EGFP reporter in HEK293T, not endogenous gene expression.",
            "Single assay: both libraries come from one MPRA study (Sample et al. 2019); cross-assay transfer is untested.",
            "sample2019_egfp_random50 is IN-TRAINING-DISTRIBUTION for MRL models trained on this assay (GEMORNA's 5'UTR MRL head was trained on the Sample-2019 random-50 library); a pass there is the expected positive control, not evidence of generalization.",
            "Tiers are relative to each family's own rl distribution; 'binder'/'negative' roles denote high/low-MRL screening poles, not molecular binding.",
        ],
        "entries": all_entries,
    }
    assert out["n_entries"] == len(out["entries"]), "n_entries != len(entries)"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"\nwrote {OUT} ({out['n_entries']} entries: {per_family})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
