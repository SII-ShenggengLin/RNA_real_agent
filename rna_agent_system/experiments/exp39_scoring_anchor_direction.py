#!/usr/bin/env python3
"""EXP 39 — mRNA sequence-scoring anchor direction (Supplementary Note 2,
section "mRNA sequence scoring").

Validates the scoring direction of the deterministic
``mrna_sequence_scoring`` stack (GC + LinearFold MFE + CAI, composite
``total_score = -mfe + codon_count * log(CAI)``,
``agent_core/sequence_utils.py::score_mrna_candidate``) on external anchors
through the production tool path (``ToolExecutor.run_tool``, advisory
CapGate, platform audit trail).

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
* Hypothesis (primary): the platform's sequence score reproduces the
  direction of biological optimization — wild-type CDSs score above
  random-synonymous controls of the same protein, and clinically
  validated codon-optimized vaccine CDSs (BNT162b2, mRNA-1273) score
  above random-synonymous controls.
* Arms: vaccine = the BNT162b2 and mRNA-1273 spike CDSs (n = 2;
  ``data/benchmarks/external_anchors/vaccine_mrna/`` putative assembled
  contigs, longest-ORF extraction exactly as registered in Exp 37,
  terminal stop stripped to match the WT convention); WT = the 20
  FullLength-mRNA benchmark RefSeq CDS anchors (n = 20,
  ``data/benchmarks/external_anchors/wt_cds/``, terminal stop stripped);
  random = 10 seeded synonymous resamples of each WT (n = 200; uniform
  choice over the standard genetic code's synonymous set,
  ``random.Random("exp2:<target>:<draw>")`` — the identical generator and
  seeds as the frozen Exp-2 null arm, so the random arm regenerates the
  Exp-2 corpus verbatim).
* CAI species: Homo sapiens for every arm (the anchors are human-expression
  constructs; task instruction). Note the frozen Exp-2 panel used
  species-resolved tables — this experiment is deliberately single-table
  to isolate the scoring formula; cross-era comparisons stay out.
* Metrics per sequence: ``total_score`` (primary), plus CAI, MFE,
  MFE/nt and GC as components — all via ``ToolExecutor.run_tool``
  (``compute_rna_sequence_gc_content`` :8020,
  ``predict_rna_secondary_structure_with_linearfold`` :8015,
  ``compute_cai_for_cds_sequence`` local Kazusa) and the production
  ``compute_mrna_metric_bundle`` / ``score_mrna_candidate``; no metric is
  re-implemented in this driver.
* Endpoints: (primary, length-controlled) per-target stratified contrast
  WT vs its own 10 random draws on total_score — two-sided sign test on
  the 20 per-target signs and Wilcoxon signed-rank on the per-target
  deltas (WT minus draw); (secondary, as directed) pooled Mann–Whitney
  P + Cliff's delta on total_score for WT vs random (20 vs 200),
  vaccine vs random (2 vs 200) and vaccine+WT vs random (22 vs 200);
  (descriptive) vaccine vs the 10 Spike-WT random draws (2 vs 10) and
  vaccine vs WT (2 vs 20 — underpowered, reported as measured); the same
  pooled contrasts on CAI and MFE/nt as components. A violated ordering
  is reported, never dropped.
* Gate: pilot (2 vaccine + 2 WT + their 20 draws) all scored with
  non-null metrics before the full matrix; full run requires 222/222
  successful records.
* CapGate policy: ``RNADA_CAPGATE=advisory`` (the documented regression
  convention; deterministic CAI/GC/MFE tools are not gated).
* ``--verify`` checks the frozen records: regenerates every arm sequence
  from its anchor/seed and asserts equality with the recorded sequence,
  then rebuilds summary.json from records.jsonl and byte-compares.
  (Service recomputation is deterministic but is not re-run on verify;
  the sequence-equality check pins the arm construction.)

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp39_scoring_anchor_direction.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp39_scoring_anchor_direction.py
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp39_scoring_anchor_direction.py --verify

Outputs under ``experiments/results/exp39_scoring_anchor_direction/``:
    records.jsonl, summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
WT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "wt_cds"
VACCINE_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "vaccine_mrna"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp39_scoring_anchor_direction"
RECORDS_PATH = RESULTS_DIR / "records.jsonl"
SUMMARY_PATH = RESULTS_DIR / "summary.json"

N_RANDOM_DRAWS = 10
CAI_SPECIES = "Homo sapiens"
PILOT_TARGETS = ["Insulin", "GFP"]

# ── standard genetic code (verbatim copy of the Exp-2 generator — the random
# arm must regenerate the frozen Exp-2 corpus) ──────────────────────────────
_BASES = "AUGC"
_AAS = "".join([
    "KNKN",  # AAx
    "IIMI",  # AUx  (AUG = Met)
    "RSRS",  # AGx  (AGA/AGG = Arg; AGU/AGC = Ser)
    "TTTT",  # ACx
    "*Y*Y",  # UA UAA UAU UAG UAC
    "LFLF",  # UUx  (UUA/UUG = Leu)
    "*CWC",  # UG UGA UGU UGG UGC (UGG = Trp)
    "SSSS",  # UCx
    "EDED",  # GAx
    "VVVV",  # GUx
    "GGGG",  # GGx
    "AAAA",  # GCx
    "QHQH",  # CAx
    "LLLL",  # CUx
    "RRRR",  # CGx
    "PPPP",  # CCx
])
CODON_TABLE: dict[str, str] = {
    b1 + b2 + b3: _AAS[i]
    for i, (b1, b2, b3) in enumerate(
        (x, y, z) for x in _BASES for y in _BASES for z in _BASES
    )
}
SYNONYMOUS_CODONS: dict[str, list[str]] = {}
for _codon, _aa in CODON_TABLE.items():
    if _aa == "*":
        continue
    SYNONYMOUS_CODONS.setdefault(_aa, []).append(_codon)
STOPS = {"UAA", "UAG", "UGA"}


# ── sequence inputs ──────────────────────────────────────────────────────────

def read_fasta(path: Path) -> str:
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.lstrip().startswith(">")]
    return "".join(lines).upper().replace("T", "U")


def load_wt_cds(target_id: str) -> str:
    """WT CDS anchor, terminal stop stripped (Exp-2 convention)."""
    seq = read_fasta(WT_DIR / f"{target_id}.fa")
    if len(seq) % 3 != 0:
        raise ValueError(f"{target_id}: WT CDS length {len(seq)} not multiple of 3")
    codons = [seq[i:i + 3] for i in range(0, len(seq), 3)]
    if codons and codons[-1] in STOPS:
        codons = codons[:-1]
    internal_stops = [i for i, c in enumerate(codons) if c in STOPS]
    if internal_stops:
        raise ValueError(f"{target_id}: internal stop codons at {internal_stops[:5]}")
    return "".join(codons)


def random_synonymous(wt_cds: str, target_id: str, draw: int) -> str:
    """Uniform synonymous resample of the WT CDS — identical to Exp 2."""
    rng = random.Random(f"exp2:{target_id}:{draw}")
    out = []
    for i in range(0, len(wt_cds), 3):
        codon = wt_cds[i:i + 3]
        out.append(rng.choice(SYNONYMOUS_CODONS[CODON_TABLE[codon]]))
    return "".join(out)


def longest_orf_cds(contig_rna: str) -> str:
    """Longest in-frame AUG→stop ORF of the contig — the registered
    extraction rule for the putative vaccine assembled contigs (Exp 37)."""
    best = ""
    for frame in range(3):
        seq = contig_rna[frame:]
        start = 0
        while True:
            aug = seq.find("AUG", start)
            if aug < 0:
                break
            stop = None
            for i in range(aug + 3, len(seq) - 2, 3):
                if seq[i:i + 3] in ("UAA", "UAG", "UGA"):
                    stop = i
                    break
            if stop is not None:
                orf = seq[aug:stop + 3]
                if len(orf) > len(best):
                    best = orf
            start = aug + 3
    return best


def vaccine_cds(name: str) -> str:
    """Vaccine optimized CDS, terminal stop stripped (WT convention)."""
    rna = read_fasta(VACCINE_DIR / f"{name}_full.fa")
    cds = longest_orf_cds(rna)
    assert len(cds) >= 3000, f"{name} ORF too short: {len(cds)}"
    codons = [cds[i:i + 3] for i in range(0, len(cds), 3)]
    if codons and codons[-1] in STOPS:
        codons = codons[:-1]
    return "".join(codons)


def load_target_ids() -> list[str]:
    return sorted(json.loads(p.read_text(encoding="utf-8"))["target_id"]
                  for p in TARGETS_DIR.glob("*.json"))


def build_arm_sequences(only_targets: list[str] | None = None,
                        draws_per_target: int = N_RANDOM_DRAWS
                        ) -> list[dict[str, Any]]:
    """The full scoring matrix: (arm, target_id, draw, sequence)."""
    items: list[dict[str, Any]] = []
    if only_targets is None:
        for name in ("bnt162b2", "mrna1273"):
            items.append({"arm": "vaccine", "target_id": name,
                          "draw": None, "sequence": vaccine_cds(name)})
    for tid in (only_targets or load_target_ids()):
        wt = load_wt_cds(tid)
        items.append({"arm": "wt", "target_id": tid, "draw": None,
                      "sequence": wt})
        for draw in range(draws_per_target):
            items.append({"arm": "random", "target_id": tid, "draw": draw,
                          "sequence": random_synonymous(wt, tid, draw)})
    return items


# ── production scoring path ──────────────────────────────────────────────────

def _ensure_services() -> None:
    """Pre-flight the two CPU microservices exactly as the workflow does."""
    from agent_core.services.service_manager import (
        ensure_services_ready,
        get_services_for_capabilities,
    )
    services = get_services_for_capabilities([
        "compute_rna_sequence_gc_content",
        "predict_rna_secondary_structure_with_linearfold",
    ])
    ok, errors = ensure_services_ready(services, timeout=300)
    if not ok:
        raise RuntimeError(f"service pre-flight failed: {errors}")


def _score_sequence(executor: Any, item: dict[str, Any]) -> dict[str, Any]:
    """One sequence through the production tool path + production scorer."""
    from agent_core.file_manager import save_sequence
    from agent_core.sequence_utils import (
        compute_mrna_metric_bundle,
        score_mrna_candidate,
    )

    seq = item["sequence"]
    draw_tag = "" if item["draw"] is None else f"_d{item['draw']}"
    fp = save_sequence(seq, prefix=f"exp39_{item['arm']}_{item['target_id']}{draw_tag}")

    def call(tool: str, **kwargs: Any) -> dict[str, Any]:
        res = executor.run_tool(tool, **kwargs)
        if not res.success:
            raise RuntimeError(f"tool {tool} failed for "
                               f"{item['arm']}:{item['target_id']}:{item['draw']}: "
                               f"{res.error}")
        return res.artifacts.get("result") or {}

    gc = call("compute_rna_sequence_gc_content", filepath=fp)
    fold = call("predict_rna_secondary_structure_with_linearfold", filepath=fp)
    cai = call("compute_cai_for_cds_sequence", filepath=fp, species=CAI_SPECIES)

    bundle = compute_mrna_metric_bundle(
        sequence=seq,
        gc_from_tools=gc.get("gc_content"),
        sequence_length_from_tools=gc.get("sequence_length"),
        mfe_kcal_per_mol=fold.get("mfe"),
        cai_score=cai.get("cai_score"),
    )
    scores = score_mrna_candidate(bundle)
    return {
        "arm": item["arm"],
        "target_id": item["target_id"],
        "draw": item["draw"],
        "sequence": seq,
        "length_nt": len(seq),
        "cai_species": CAI_SPECIES,
        "gc_content": bundle["gc_content"],
        "mfe_kcal_per_mol": bundle["mfe_kcal_per_mol"],
        "mfe_per_nt": bundle["mfe_per_nt"],
        "cai_score": bundle["cai_score"],
        "total_score": scores.get("total_score"),
        "success": True,
    }


def load_records() -> list[dict[str, Any]]:
    if not RECORDS_PATH.exists():
        return []
    out = []
    for line in RECORDS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def run_matrix(items: list[dict[str, Any]]) -> int:
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    _ensure_services()
    executor = ToolExecutor(build_default_tool_registry())

    done = {(r["arm"], r["target_id"], r.get("draw"))
            for r in load_records() if r.get("success")}
    todo = [it for it in items
            if (it["arm"], it["target_id"], it.get("draw")) not in done]
    print(f"[score] {len(done)} already frozen, {len(todo)} to score", flush=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    n_fail = 0
    with RECORDS_PATH.open("a", encoding="utf-8") as fh:
        for i, item in enumerate(todo, 1):
            try:
                rec = _score_sequence(executor, item)
            except Exception as exc:  # recorded, never silently dropped
                rec = {"arm": item["arm"], "target_id": item["target_id"],
                       "draw": item["draw"], "success": False,
                       "error": str(exc)[:500]}
                n_fail += 1
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 20 == 0 or i == len(todo):
                print(f"[score] {i}/{len(todo)} done ({n_fail} failed)", flush=True)
    return 0 if n_fail == 0 else 1


# ── statistics ───────────────────────────────────────────────────────────────

def cliffs_delta(x: list[float], y: list[float]) -> float:
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (len(x) * len(y))


def pairwise(x: list[float], y: list[float]) -> dict[str, Any]:
    from scipy.stats import mannwhitneyu
    if len(x) < 2 or len(y) < 2:
        return {"n_x": len(x), "n_y": len(y)}
    u = mannwhitneyu(x, y, alternative="two-sided")
    return {
        "n_x": len(x), "n_y": len(y),
        "median_x": round(statistics.median(x), 4),
        "median_y": round(statistics.median(y), 4),
        "mannwhitney_p": float(u.pvalue),
        "cliffs_delta": round(cliffs_delta(x, y), 4),
    }


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    from scipy.stats import binomtest, wilcoxon

    ok = [r for r in records if r.get("success")]
    arms: dict[str, list[dict[str, Any]]] = {"vaccine": [], "wt": [], "random": []}
    for r in ok:
        arms[r["arm"]].append(r)

    def vals(arm: str, key: str, target: str | None = None) -> list[float]:
        return [r[key] for r in arms[arm]
                if r[key] is not None and (target is None or r["target_id"] == target)]

    def arm_stats(key: str) -> dict[str, Any]:
        return {
            arm: ({"n": len(v), "median": round(statistics.median(v), 4),
                   "q1": round(statistics.quantiles(v, n=4)[0], 4),
                   "q3": round(statistics.quantiles(v, n=4)[2], 4)}
                  if (v := vals(arm, key)) else None)
            for arm in ("vaccine", "wt", "random")
        }

    # primary: per-target stratified WT vs own random draws on total_score
    stratified = []
    for tid in sorted({r["target_id"] for r in arms["wt"]}):
        wt_ts = vals("wt", "total_score", tid)
        rnd_ts = vals("random", "total_score", tid)
        deltas = [wt_ts[0] - d for d in rnd_ts]
        stratified.append({
            "target_id": tid,
            "wt_total_score": wt_ts[0],
            "random_median_total_score": statistics.median(rnd_ts),
            "n_draws": len(rnd_ts),
            "wt_above_all_draws": all(d > 0 for d in deltas),
            "wt_above_median": wt_ts[0] > statistics.median(rnd_ts),
            "delta_vs_median": wt_ts[0] - statistics.median(rnd_ts),
            "cliffs_delta": round(cliffs_delta(wt_ts, rnd_ts), 4),
        })
    n_above = sum(1 for s in stratified if s["wt_above_median"])
    sign_p = float(binomtest(n_above, len(stratified), 0.5).pvalue)
    delta_medians = [s["delta_vs_median"] for s in stratified]
    wilcoxon_p = (float(wilcoxon(delta_medians).pvalue)
                  if any(abs(d) > 1e-12 for d in delta_medians) else None)

    spike_random = vals("random", "total_score", "SARS-CoV-2_Spike_WT")
    comparisons = {
        "wt_vs_random": pairwise(vals("wt", "total_score"),
                                 vals("random", "total_score")),
        "vaccine_vs_random": pairwise(vals("vaccine", "total_score"),
                                      vals("random", "total_score")),
        "vaccine_plus_wt_vs_random": pairwise(
            vals("vaccine", "total_score") + vals("wt", "total_score"),
            vals("random", "total_score")),
        "vaccine_vs_wt": pairwise(vals("vaccine", "total_score"),
                                  vals("wt", "total_score")),
        "vaccine_vs_spike_random": pairwise(vals("vaccine", "total_score"),
                                            spike_random),
    }
    components = {}
    for key in ("cai_score", "mfe_per_nt", "gc_content", "mfe_kcal_per_mol"):
        components[key] = {
            "arms": arm_stats(key),
            "wt_vs_random": pairwise(vals("wt", key), vals("random", key)),
            "vaccine_vs_random": pairwise(vals("vaccine", key),
                                          vals("random", key)),
            "vaccine_plus_wt_vs_random": pairwise(
                vals("vaccine", key) + vals("wt", key), vals("random", key)),
        }

    return {
        "experiment": "exp39_scoring_anchor_direction",
        "workflow": "mrna_sequence_scoring",
        "scoring_path": ("ToolExecutor.run_tool: compute_rna_sequence_gc_content "
                         "(:8020) + predict_rna_secondary_structure_with_linearfold "
                         "(:8015) + compute_cai_for_cds_sequence (Kazusa, "
                         f"{CAI_SPECIES}); total_score = -mfe + codon_count*log(CAI) "
                         "via agent_core.sequence_utils.score_mrna_candidate"),
        "cai_species": CAI_SPECIES,
        "random_arm": ("10 seeded synonymous draws per WT (uniform, standard code, "
                       "seed 'exp2:<target>:<draw>') — regenerates the frozen "
                       "Exp-2 null corpus verbatim"),
        "vaccine_arm": ("BNT162b2 / mRNA-1273 putative assembled contigs, "
                        "longest-ORF extraction as registered in Exp 37, "
                        "terminal stop stripped"),
        "n_records": len(ok),
        "n_failed": len(records) - len(ok),
        "arm_sizes": {arm: len(v) for arm, v in arms.items()},
        "arms_total_score": arm_stats("total_score"),
        "primary_stratified": {
            "metric": "total_score",
            "n_targets": len(stratified),
            "n_wt_above_random_median": n_above,
            "n_wt_above_all_draws": sum(1 for s in stratified
                                        if s["wt_above_all_draws"]),
            "sign_test_p": sign_p,
            "wilcoxon_signed_rank_p_on_delta_vs_median": wilcoxon_p,
            "median_delta_vs_median": round(statistics.median(delta_medians), 4),
            "median_cliffs_delta": round(statistics.median(
                [s["cliffs_delta"] for s in stratified]), 4),
            "per_target": stratified,
        },
        "pooled_comparisons_total_score": comparisons,
        "components": components,
        "notes": ("Pooled total_score contrasts mix lengths across proteins "
                  "(total_score scales with length); the per-target stratified "
                  "contrast is the length-controlled primary. Vaccine n = 2 — "
                  "its Mann–Whitney P is descriptive only."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pilot", action="store_true",
                    help="score the pilot matrix only (2 vaccine + 2 WT + 20 draws)")
    ap.add_argument("--verify", action="store_true",
                    help="rebuild summary from records and byte-compare; assert "
                         "arm sequences regenerate from anchors/seeds")
    ap.add_argument("--summary", action="store_true",
                    help="(re)write summary.json from the frozen records")
    args = ap.parse_args()

    if args.verify:
        return verify()

    if args.pilot:
        items = build_arm_sequences(only_targets=PILOT_TARGETS)
        print(f"[pilot] {len(items)} sequences "
              f"(2 vaccine + {len(PILOT_TARGETS)} WT + "
              f"{len(PILOT_TARGETS) * N_RANDOM_DRAWS} random)")
        rc = run_matrix(items)
        if rc != 0:
            print("[pilot] FAIL — see records.jsonl")
            return rc
        recs = [r for r in load_records() if r.get("success")]
        missing = [r for r in recs if r.get("total_score") is None]
        gate = len(recs) == len(items) and not missing
        print(f"[pilot] gate: {len(recs)}/{len(items)} scored, "
              f"{len(missing)} null metrics — {'PASS' if gate else 'FAIL'}")
        return 0 if gate else 1

    if args.summary:
        return write_summary()

    items = build_arm_sequences()
    print(f"[full] {len(items)} sequences "
          f"(2 vaccine + 20 WT + {20 * N_RANDOM_DRAWS} random)")
    rc = run_matrix(items)
    if rc != 0:
        return rc
    return write_summary()


def write_summary() -> int:
    records = load_records()
    summary = build_summary(records)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(_summary_text(summary), encoding="utf-8")
    prim = summary["primary_stratified"]
    comp = summary["pooled_comparisons_total_score"]
    print(f"wrote {SUMMARY_PATH}")
    print(f"  arms {summary['arm_sizes']}, failed {summary['n_failed']}")
    print(f"  stratified: WT > random median in "
          f"{prim['n_wt_above_random_median']}/{prim['n_targets']} targets "
          f"(above all draws: {prim['n_wt_above_all_draws']}), "
          f"sign P = {prim['sign_test_p']:.3e}, "
          f"Wilcoxon P = {prim['wilcoxon_signed_rank_p_on_delta_vs_median']:.3e}")
    for name, c in comp.items():
        if "mannwhitney_p" in c:
            print(f"  {name}: median {c['median_x']} vs {c['median_y']}, "
                  f"MWU P = {c['mannwhitney_p']:.3e}, Cliff's d = {c['cliffs_delta']}")
    return 0 if summary["n_failed"] == 0 else 1


def _summary_text(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def verify() -> int:
    records = load_records()
    # 1. arm construction pinned: every recorded sequence must regenerate
    #    from its anchor/seed
    expected = {(it["arm"], it["target_id"], it.get("draw")): it["sequence"]
                for it in build_arm_sequences()}
    n_checked = 0
    for r in records:
        if not r.get("success"):
            continue
        key = (r["arm"], r["target_id"], r.get("draw"))
        if key not in expected:
            print(f"VERIFY FAIL — unexpected record {key}")
            return 1
        if r["sequence"] != expected[key]:
            print(f"VERIFY FAIL — sequence mismatch for {key}")
            return 1
        n_checked += 1
    if n_checked != len(expected):
        print(f"VERIFY FAIL — {n_checked} records vs {len(expected)} expected")
        return 1
    # 2. summary rebuilds byte-identically from the frozen records
    fresh = _summary_text(build_summary(records))
    stored = SUMMARY_PATH.read_text(encoding="utf-8")
    if stored != fresh:
        print("VERIFY FAIL — summary.json differs from recomputation")
        return 1
    print(f"VERIFY OK — {n_checked} arm sequences regenerate from anchors/seeds; "
          f"summary.json byte-identical on recomputation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
