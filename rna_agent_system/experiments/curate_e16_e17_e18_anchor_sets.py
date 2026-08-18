#!/usr/bin/env python3
"""E16/E17/E18 anchor-set curation (2026-08-18) — assertion-checked, deterministic.

Builds the three anchor sets for the pending-oracle profiling campaigns
(DECISIONS.md (j), E16+ backlog):

  E16 IRESfinder  : data/benchmarks/external_anchors/ires/e16_ires_anchor_set.json
      Upstream-held-out IRES/non-IRES sets shipped with IRESfinder
      (external_repos/IRESfinder/dataset/*.seq). Three families:
      independent 5'UTR-IRES (13/13), independent core-IRES (13/13) and the
      upstream internal testing split (40/40). Binary labels only.
  E17 GerNA-Bind  : data/benchmarks/external_anchors/small_molecule/e17_gernabind_anchor_set.json
      The 17 curated RNA-small-molecule pairs (4 binder / 13 non-binder;
      PDB-derived sequences + benchmark-task SMILES, see SOURCES.md).
  E18 RNASTOP     : data/benchmarks/external_anchors/mrna_stability/e18_rnastop_anchor_set.json
      The upstream public test set shipped with RNASTOP
      (external_repos/RNASTOP/data/test_dataset_public.json; 400 x 107-nt
      OpenVaccine-style constructs with measured reactivity / deg_Mg_pH10 /
      deg_Mg_50C). Measured label = overall degradation burden, mirroring the
      service's overall_stability definition (global mean of the three
      per-position metrics). E7-style screening tiers (top/bottom 60) and a
      120-anchor rank-stratified ranking subset.

Every set carries internal-consistency assertions (alphabet, dedupe, tier
counts, measured-label range) that run at build time; the build fails loudly
on any violation. Zero LLM. Deterministic (seed 0 where sampling exists).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANCHORS = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors"
IRES_UPSTREAM = PROJECT_ROOT / "external_repos" / "IRESfinder" / "dataset"
RNASTOP_UPSTREAM = PROJECT_ROOT / "external_repos" / "RNASTOP" / "data"
CURATED = "2026-08-18"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read_seq_lines(path: Path) -> tuple[list[str], int]:
    """Return (deduped uppercase lines, number of removed duplicates)."""
    lines = [ln.strip().upper() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for ln in lines:
        _assert(set(ln) <= set("ACGT"), f"{path.name}: non-ACGT character in {ln[:30]}...")
    _assert(len(lines) > 0, f"{path.name}: empty")
    seen: set[str] = set()
    unique = [ln for ln in lines if not (ln in seen or seen.add(ln))]
    return unique, len(lines) - len(unique)


def build_e16_ires() -> dict:
    pos_5utr, _ = _read_seq_lines(IRES_UPSTREAM / "independent_testing_dataset_5utr_ires.seq")
    pos_core, _ = _read_seq_lines(IRES_UPSTREAM / "independent_testing_dataset_core_ires.seq")
    neg_ind, neg_dups = _read_seq_lines(IRES_UPSTREAM / "independent_testing_dataset_nonires.seq")
    pos_test, _ = _read_seq_lines(IRES_UPSTREAM / "testing_dataset_ires.seq")
    neg_test, _ = _read_seq_lines(IRES_UPSTREAM / "testing_dataset_nonires.seq")
    _assert((len(pos_5utr), len(pos_core), len(neg_ind), len(pos_test), len(neg_test)) == (13, 13, 12, 40, 40),
            "upstream IRESfinder dataset sizes drifted from the vendored upstream")

    entries = []
    for family, pos, neg in (
        ("independent_5utr_ires_vs_nonires", pos_5utr, neg_ind),
        ("independent_core_ires_vs_nonires", pos_core, neg_ind),
        ("upstream_testing_ires_vs_nonires", pos_test, neg_test),
    ):
        for i, seq in enumerate(pos, 1):
            entries.append({
                "id": f"{family}_pos{i:02d}",
                "name": f"{family} IRES positive #{i}",
                "target": family,
                "sequence": seq,
                "alphabet": "dna",
                "length_nt": len(seq),
                "role": "binder",
                "ranking_eligible": False,
                "reference": "IRESfinder upstream dataset (vendored external_repos/IRESfinder/dataset); independent/testing splits as released",
            })
        for i, seq in enumerate(neg, 1):
            entries.append({
                "id": f"{family}_neg{i:02d}",
                "name": f"{family} non-IRES negative #{i}",
                "target": family,
                "sequence": seq,
                "alphabet": "dna",
                "length_nt": len(seq),
                "role": "negative",
                "ranking_eligible": False,
                "reference": "IRESfinder upstream dataset (vendored external_repos/IRESfinder/dataset); independent/testing splits as released",
            })

    per_family = {f: sum(1 for e in entries if e["target"] == f) for f in
                  ("independent_5utr_ires_vs_nonires", "independent_core_ires_vs_nonires", "upstream_testing_ires_vs_nonires")}
    _assert(per_family == {"independent_5utr_ires_vs_nonires": 25, "independent_core_ires_vs_nonires": 25, "upstream_testing_ires_vs_nonires": 80}, per_family)
    return {
        "description": "E16 IRESfinder screening anchor set: upstream-held-out IRES vs non-IRES sequences as released with IRESfinder (independent 5'UTR-IRES and core-IRES sets, plus the internal testing split). Binary screening labels only.",
        "curated": CURATED,
        "convention": "sequences passed verbatim to the service in the upstream DNA alphabet (the service's model input format); IRES positives are role 'binder'",
        "preregistration": "experiments/run_e16_e17_e18_oracle_profiling.py docstring, E16-E18 PRE-REGISTRATION (2026-08-18)",
        "selection_seed": 0,
        "excluded_subsets": {"independent_testing_dataset_nonires duplicate rows": f"{neg_dups} exact duplicate negative line(s) removed (upstream data quirk, first occurrence kept)"},
        "n_entries": len(entries),
        "entries_per_family": per_family,
        "known_limitations": [
            "Binary labels only: IRESfinder grades screen on AUROC; no ranking grade is computable from these anchors.",
            "The upstream testing split (40/40) is held out from IRESfinder's training by the upstream authors' design; both independent sets are fully held-out.",
            "Positive counts (13/13/40) are small; bootstrap CIs are reported and the thin-positive limitation is carried into the verdict.",
        ],
        "entries": entries,
    }


def build_e17_gernabind() -> dict:
    pairs = json.loads((ANCHORS / "small_molecule" / "pairs.json").read_text(encoding="utf-8"))
    _assert(len(pairs) == 17, "pairs.json size drifted")
    roles = [p["expected"] for p in pairs]
    _assert(roles.count("binder") == 4 and roles.count("non_binder") == 13, roles)
    entries = []
    for p in pairs:
        seq = p["rna_sequence"].upper()
        _assert(set(seq) <= set("ACGU"), f"{p['pair_id']}: non-RNA alphabet")
        entries.append({
            "id": p["pair_id"],
            "name": p.get("rna_name", p["pair_id"]),
            "target": "pdb_pairs_perturbation",
            "sequence": seq,
            "smiles": p["smiles"],
            "alphabet": "rna",
            "length_nt": len(seq),
            "role": "binder" if p["expected"] == "binder" else "negative",
            "original_label": p["expected"],
            "ranking_eligible": False,
            "reference": p.get("reference", "see data/benchmarks/external_anchors/SOURCES.md"),
        })
    _assert(len({e["id"] for e in entries}) == 17, "duplicate pair ids")
    _assert(len({e["sequence"] for e in entries}) >= 3, "degenerate anchor pool")
    return {
        "description": "E17 GerNA-Bind screening anchor set: the 17 curated RNA-small-molecule pairs (4 binder / 13 non-binder; three RNA scaffolds x ligand perturbations, PDB-derived).",
        "curated": CURATED,
        "convention": "RNA sequence + SMILES scored by the deployed GerNA-Bind affinity head (probability_positive); anchors share the RNAsmol boundary-panel provenance (SOURCES.md)",
        "preregistration": "experiments/run_e16_e17_e18_oracle_profiling.py docstring, E16-E18 PRE-REGISTRATION (2026-08-18)",
        "selection_seed": 0,
        "n_entries": len(entries),
        "entries_per_family": {"pdb_pairs_perturbation": 17},
        "known_limitations": [
            "Small set (17 pairs) on three RNA scaffolds; AUROC CI is correspondingly wide and reported.",
            "Screening grade only: no continuous affinity labels, hence no ranking grade.",
            "Same pair set was used for the RNAsmol boundary panel's PDB-pair arm; GerNA-Bind is scored here for the first time.",
        ],
        "entries": entries,
    }


def build_e18_rnastop() -> dict:
    data = json.loads((RNASTOP_UPSTREAM / "test_dataset_public.json").read_text(encoding="utf-8"))
    cols = ("sequence", "reactivity", "deg_Mg_pH10", "deg_Mg_50C", "id")
    for c in cols:
        _assert(c in data, f"missing column {c}")
    keys = sorted(data["sequence"], key=int)
    _assert(len(keys) == 400, f"expected 400 rows, got {len(keys)}")

    rows = []
    for k in keys:
        seq = data["sequence"][k].upper()
        _assert(set(seq) <= set("ACGU"), f"row {k}: non-RNA alphabet")
        # overall_stability mirror: global mean of the three per-position metrics
        measured = sum(
            sum(data[m][k]) / len(data[m][k]) for m in ("reactivity", "deg_Mg_pH10", "deg_Mg_50C")
        ) / 3.0
        rows.append({"key": k, "id": data["id"][k], "sequence": seq, "measured_overall": measured})
    _assert(len({r["sequence"] for r in rows}) == 400, "duplicate sequences")
    values = sorted(r["measured_overall"] for r in rows)
    _assert(0.0 < values[0] < values[-1], "degenerate measured range")

    # E7-style selection, seed-free (deterministic rank spacing).
    by_rank = sorted(rows, key=lambda r: (r["measured_overall"], r["key"]))
    n = len(by_rank)
    top = set(by_rank[-60:][i]["key"] for i in range(60))
    bottom = set(by_rank[:60][i]["key"] for i in range(60))
    ranking_keys = set(by_rank[int(i * (n - 1) / 119)]["key"] for i in range(120))

    entries = []
    for r in by_rank:
        if r["key"] in top:
            role = "binder"  # high-degradation tier (least stable)
        elif r["key"] in bottom:
            role = "negative"  # low-degradation tier (most stable)
        else:
            role = "unranked_middle"
        entries.append({
            "id": f"rnastop_{r['key']}_{r['id']}",
            "name": f"RNASTOP public test row {r['key']} ({r['id']})",
            "target": "rnastop_public_test_107nt",
            "sequence": r["sequence"],
            "alphabet": "rna",
            "length_nt": len(r["sequence"]),
            "measured_overall_stability": round(r["measured_overall"], 6),
            "role": role,
            "ranking_eligible": r["key"] in ranking_keys,
            "reference": "RNASTOP upstream public test set (external_repos/RNASTOP/data/test_dataset_public.json); measured = global mean of reactivity/deg_Mg_pH10/deg_Mg_50C per-position arrays, mirroring the service's overall_stability definition",
        })
    n_top = sum(1 for e in entries if e["role"] == "binder")
    n_bottom = sum(1 for e in entries if e["role"] == "negative")
    n_rank = sum(1 for e in entries if e["ranking_eligible"])
    _assert((n_top, n_bottom, n_rank) == (60, 60, 120), (n_top, n_bottom, n_rank))
    return {
        "description": "E18 RNASTOP anchor set: the upstream public test set (400 x 107-nt constructs, measured per-position reactivity and degradation rates). Screening tiers: top/bottom 60 by measured overall degradation burden; ranking subset: 120 anchors evenly spaced across measured ranks.",
        "curated": CURATED,
        "convention": "higher predicted overall_stability = higher predicted degradation burden (less stable); tiers: role 'binder' = most-degraded top 60, 'negative' = most-stable bottom 60; sequences scored without truncation (107 nt << 512-nt service cap)",
        "preregistration": "experiments/run_e16_e17_e18_oracle_profiling.py docstring, E16-E18 PRE-REGISTRATION (2026-08-18)",
        "selection_seed": 0,
        "selection_protocol": {
            "filter": "all 400 public-test rows kept (upstream already filtered); dedupe asserted",
            "screening_tiers": "top 60 by measured_overall_stability = role binder; bottom 60 = role negative",
            "ranking_subset": "120 anchors evenly spaced across measured ranks (floor(i*(N-1)/119)), ranking_eligible=true",
        },
        "n_entries": len(entries),
        "entries_per_family": {"rnastop_public_test_107nt": len(entries)},
        "known_limitations": [
            "107-nt OpenVaccine-style constructs, not therapeutic-length mRNAs; the deployed 512-nt truncation never triggers here, so full-length behaviour remains unprofiled.",
            "Single upstream assay (RNASTOP authors' public test split); in-training-distribution for RNASTOP if the checkpoint was trained on this data family.",
            "Measured label is a degradation-burden composite, not half-life.",
        ],
        "entries": entries,
    }


def main() -> int:
    outputs = {
        ANCHORS / "ires" / "e16_ires_anchor_set.json": build_e16_ires,
        ANCHORS / "small_molecule" / "e17_gernabind_anchor_set.json": build_e17_gernabind,
        ANCHORS / "mrna_stability" / "e18_rnastop_anchor_set.json": build_e18_rnastop,
    }
    for path, builder in outputs.items():
        payload = builder()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(PROJECT_ROOT)}: {payload['n_entries']} entries, families={payload['entries_per_family']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
