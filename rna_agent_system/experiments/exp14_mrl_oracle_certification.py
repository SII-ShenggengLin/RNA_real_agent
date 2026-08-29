#!/usr/bin/env python3
"""Experiment 14 (paper registry E7 — §2.3 experiment 6, Fig. 3g): MRL
expression-oracle certification, the positive side of the capability profile.

The full-length mRNA workflow's expression oracle — the GEMORNA 5'UTR
mean-ribosome-load (MRL) predictor — is re-profiled on the three
experimentally measured anchor families (Sample et al. 2019 MPRA), expecting
re-verification under the E1-identical gates (screening AUROC > 0.8 with a
10,000-fold bootstrap CI; ranking Spearman ρ ≥ 0.6).  This is the experiment
that certifies power where it exists, completing the two-sided capability
map alongside the revoked structure-oracle panels (Figs. 3b–3f).

PRE-REGISTRATION (reset campaign, 2026-08-29; protocol re-registered from
the retained E7 evidence of 2026-08-11 — user-confirmed three-family scope
the same day, the in-distribution family retained as the registered
positive control after user review)
---------------------------------------------------------------------
* Question: does the deployed expression oracle (``gemorna_5utr_mrl``)
  reproduce its certified screening and ranking power on the three measured
  MRL anchor families?  H1 (direction pre-registered): all three families
  pass both gates — screening AUROC > 0.8 with the bootstrap CI clearing
  chance, ranking ρ ≥ 0.6 — matching the retained evidence in direction and
  approximately in magnitude.  The ``sample2019_egfp_random50`` family is
  IN-TRAINING-DISTRIBUTION (GEMORNA's MRL head was trained on this assay
  library): a pass there is the registered positive control certifying the
  deployed chain end-to-end, never evidence of generalization; the
  generalization claim rests on the two never-trained families (varying-
  length random, varying-length human endogenous).
* Anchor set (user-confirmed 2026-08-29, byte-verbatim, unmodified):
  ``data/benchmarks/external_anchors/utr_mrl/e7_mrl_anchor_set.json`` —
  706 entries / 3 families from the Sample et al. 2019 MPRA (GEO GSE114002;
  EGFP reporter, unmodified RNA, HEK293T; GSM3130435 random 50-nt library +
  GSM4084997 varying-length library, filtered total_reads ≥ 1000, ACGT-only,
  deduped; selection seed 0).  Per family: 60 high-MRL (role ``binder``) +
  60 low-MRL (role ``negative``) screening tiers and a 120-anchor
  rank-stratified ``ranking_eligible`` subset.  Roles denote high/low-MRL
  screening poles, not molecular binding (anchor-set convention).
* Instrument (zero-intervention rule, identical to the exp10–exp13 runs):
  the platform's production tool path — ``ToolExecutor.run_tool`` through
  the ``ToolRegistry`` (schema-validated LangChain ``.invoke``) — against
  the deployed GEMORNA microservice already healthy at run start (port
  8004, GPU-pinned 0/1/2 placement by the experiment bring-up script,
  inherited and left untouched).  One call per anchor through the registered
  tool ``predict_5utr_mrl_with_gemorna`` with default arguments only: each
  anchor's stored sequence (DNA alphabet) is written verbatim to a scratch
  file and the tool layer's production normalization (uppercase, T→U)
  applies before the service — the anchor-set "DNA scored as RNA" convention;
  the service-echoed ``input_sequence`` is recorded for verification.  No
  threshold presets, no parameter sweeps, no retries beyond the driver-level
  ``--resume``.
* Disclosed call-path note: the retained 2026-08-11 E7 driver (deleted in
  the 2026-08-18 reset) posted the DNA sequence to the service directly and
  the service performed T→U; this reset run goes through the ToolExecutor
  tool wrapper, whose normalization applies the identical T→U before the
  identical service call — the model input is byte-identical and the
  per-entry 1:1 cross-check below verifies score equivalence.
* Metrics (all analysis-side — nothing is injected into the platform):
  (1) Screening, per family: AUROC of predicted MRL, role binder (high
      tier, n = 60) vs role negative (low tier, n = 60); tie-corrected
      midrank AUROC; stratified bootstrap 95% CI (10⁴ resamples, seed 0 —
      the E7 registration); gate AUROC > 0.8 (strict), CI must clear
      chance for the certification reading.
  (2) Ranking, per family: Spearman ρ(predicted MRL, measured MRL) over
      the ``ranking_eligible`` subset (n = 120); gate ρ ≥ 0.6.  A
      descriptive percentile bootstrap 95% CI (10⁴, seed 0) is computed for
      Fig. 3g — the retained registration carried no ρ CI (point estimate
      only); recorded as descriptive, not gate-bearing.
  (3) Tier sanity: per-family and pooled mean predicted MRL of the high vs
      low tier (retained S0 sanity context: pooled 6.34 vs 2.48).
  (4) 1:1 reproduction vs the retained ``e7_mrl_scoring.jsonl`` (706 ids,
      all live in the anchor set): per-entry predicted-MRL comparison —
      exact-match fraction (service reports 2-decimal values) and
      max/median |Δ|; family AUROC/ρ deltas new vs retained.
* CapGate policy: ``RNADA_CAPGATE=advisory`` — the documented regression
  convention (run_pa_test.py, exp1–exp13).  The oracle is SelfModel-
  governed (graded verified from the retained evidence) so enforce would
  not block it either; advisory is the uniform profiling convention and
  every call still lands in the platform audit trail (the driver activates
  the audit runtime via ``runtime_from_env()``).
* Pilot: 6 entries — ``hi01`` + ``lo01`` of each family (both screening
  poles; includes the 59-nt and 39-nt length edges).  Pilot pass = 6/6
  records with non-null ``predicted_mrl``; the retained JSONL's values for
  these six ids are printed informationally (no tolerance gate — the full
  1:1 cross-check is the registered comparison).
* Budget: one pass over the anchor set (706 calls, ~2.5–3 s each,
  ≈ 35–45 min wall); ``--resume`` skips entries with a successful record on
  disk.  No arm comparison — per-entry compute is fixed by the anchor set.
* Expected outcome (retained evidence, the reproduction reference):
  AUROC 0.990 / 1.000 / 1.000 (random50 CI 0.975–1.0), ρ 0.926 / 0.920 /
  0.835 for random50 / varying-length-random / varying-length-human.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp14_mrl_oracle_certification.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp14_mrl_oracle_certification.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp14_mrl_oracle_certification.py --summary

Outputs under ``experiments/results/exp14_mrl_oracle_certification/``:
    pilot.jsonl, records.jsonl, summary.json, scratch/<mode>/<id>.txt
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Registered regression convention — set before any agent_core import so the
# lazily-configured CalibratedRuntime picks it up (see docstring).
os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANCHOR_JSON = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "utr_mrl" / "e7_mrl_anchor_set.json"
)
RETAINED_SCORING = PROJECT_ROOT / "experiments" / "results" / "e7_mrl_scoring.jsonl"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp14_mrl_oracle_certification"

ORACLE = "gemorna_5utr_mrl"
TOOL = "predict_5utr_mrl_with_gemorna"
FAMILIES = [
    "sample2019_egfp_random50",
    "sample2019_varying_length_random",
    "sample2019_varying_length_human",
]
FAMILY_LABELS = {
    "sample2019_egfp_random50": "Random 50-nt (in-distribution)",
    "sample2019_varying_length_random": "Varying-length random",
    "sample2019_varying_length_human": "Varying-length human",
}
AUROC_GATE = 0.8   # strict > — the E1/E7 registered screening gate
RHO_GATE = 0.6     # the E1/E7 registered ranking gate
N_BOOT = 10_000
BOOT_SEED = 0      # the E7 registration's seed
EXPECTED = {  # anchor-set composition + retained-evidence reference numbers
    "n_entries": 706,
    "per_family": {
        "sample2019_egfp_random50": {"n": 238, "ranking_only": 118},
        "sample2019_varying_length_random": {"n": 238, "ranking_only": 118},
        "sample2019_varying_length_human": {"n": 230, "ranking_only": 110},
    },
    "retained": {
        "sample2019_egfp_random50": {"auroc": 0.9903, "rho": 0.9256},
        "sample2019_varying_length_random": {"auroc": 1.0000, "rho": 0.9201},
        "sample2019_varying_length_human": {"auroc": 1.0000, "rho": 0.8353},
    },
}
PILOT_IDS = [
    "hi01_egfp_random50", "lo01_egfp_random50",
    "hi01_vl_random", "lo01_vl_random",
    "hi01_vl_human", "lo01_vl_human",
]


# ── anchor-set loading with pre-registered composition assertions ────────────

def load_anchor() -> dict:
    anchor = json.loads(ANCHOR_JSON.read_text())
    entries = anchor["entries"]
    assert anchor["n_entries"] == len(entries) == EXPECTED["n_entries"], \
        f"anchor n_entries assertion: {len(entries)}"
    assert len({e["id"] for e in entries}) == len(entries), "anchor id uniqueness"
    fams = {e["target"] for e in entries}
    assert fams == set(FAMILIES), f"family set drift: {sorted(fams)}"
    for fam, exp in EXPECTED["per_family"].items():
        sub = [e for e in entries if e["target"] == fam]
        assert len(sub) == exp["n"], f"{fam}: n {len(sub)} != {exp['n']}"
        roles = {"binder": 0, "negative": 0, "ranking_only": 0}
        for e in sub:
            roles[e["role"]] += 1
            assert set(e["sequence"]) <= set("ACGT"), f"non-ACGT anchor {e['id']}"
            assert e["total_reads"] >= 1000, f"reads filter violated on {e['id']}"
            assert isinstance(e["measured_mrl"], float), f"no measured MRL on {e['id']}"
        assert roles == {"binder": 60, "negative": 60, "ranking_only": exp["ranking_only"]}, \
            f"{fam}: role composition {roles}"
        assert sum(1 for e in sub if e["ranking_eligible"]) == 120, \
            f"{fam}: ranking_eligible != 120"
    return anchor


# ── scoring (platform production path) ───────────────────────────────────────

def build_executor():
    from agent_core.calibrated.runtime import runtime_from_env
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    # AgentRunner's own startup step: configures the CalibratedRuntime from
    # RNADA_CAPGATE so every tool call lands in the platform audit trail
    # (advisory reviews, never blocks — see docstring).
    runtime_from_env()
    return ToolExecutor(build_default_tool_registry())


def score_entry(entry: dict, executor, scratch: Path) -> dict:
    started = time.monotonic()
    seq_file = scratch / f"{entry['id']}.txt"
    seq_file.write_text(entry["sequence"], encoding="utf-8")  # verbatim, DNA alphabet
    response = None
    error = None
    try:
        res = executor.run_tool(TOOL, filepath=str(seq_file.relative_to(PROJECT_ROOT)))
        if not res.success:
            raise RuntimeError(f"{TOOL} failed: {res.error}")
        raw = res.artifacts.get("result")
        if not isinstance(raw, dict) or raw.get("predicted_mrl") is None:
            raise RuntimeError(f"{TOOL} returned no predicted_mrl")
        response = raw
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    ok = response is not None
    return {
        "id": entry["id"],
        "target": entry["target"],
        "role": entry["role"],
        "ranking_eligible": bool(entry["ranking_eligible"]),
        "measured_mrl": entry["measured_mrl"],
        "total_reads": entry["total_reads"],
        "length_nt": entry["length_nt"],
        "alphabet": entry["alphabet"],
        "oracle": ORACLE,
        "tool": TOOL,
        "request_sequence": entry["sequence"],          # verbatim anchor bytes
        "response": response,                            # incl. service-echoed input_sequence (T→U)
        "predicted_mrl": response["predicted_mrl"] if ok else None,
        "success": ok,
        "error": error,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── statistics (E7-registered conventions) ───────────────────────────────────

def auroc(pos, neg) -> float:
    """AUROC via midrank Mann–Whitney U (tie-corrected)."""
    pos = np.asarray(pos, dtype=float)
    neg = np.asarray(neg, dtype=float)
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="mergesort")
    sv = allv[order]
    ranks = np.arange(1.0, len(sv) + 1.0)
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2.0 + 1.0
        i = j + 1
    r = np.empty(len(sv))
    r[order] = ranks
    u = r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))


def auroc_ci(pos, neg, seed: int = BOOT_SEED, n_boot: int = N_BOOT) -> tuple[float, float]:
    """Stratified bootstrap percentile 95% CI (tiers resampled separately)."""
    rng = np.random.default_rng(seed)
    pos = np.asarray(pos, dtype=float)
    neg = np.asarray(neg, dtype=float)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        vals[b] = auroc(rng.choice(pos, size=len(pos), replace=True),
                        rng.choice(neg, size=len(neg), replace=True))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def rho_ci(xs, ys, seed: int = BOOT_SEED, n_boot: int = N_BOOT) -> tuple[float, float]:
    """Descriptive percentile bootstrap 95% CI for Spearman ρ."""
    from scipy.stats import spearmanr

    rng = np.random.default_rng(seed)
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(xs), len(xs))
        vals.append(spearmanr(xs[idx], ys[idx])[0])
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


# ── analysis ─────────────────────────────────────────────────────────────────

def analyze(records: list[dict], mode_label: str) -> dict:
    from scipy.stats import spearmanr

    ok = [r for r in records if r["success"]]
    per_family: dict[str, dict] = {}
    for fam in FAMILIES:
        sub = [r for r in ok if r["target"] == fam]
        hi = [r["predicted_mrl"] for r in sub if r["role"] == "binder"]
        lo = [r["predicted_mrl"] for r in sub if r["role"] == "negative"]
        a = auroc(hi, lo)
        clo, chi = auroc_ci(hi, lo)
        rank = [r for r in sub if r["ranking_eligible"]]
        rho = float(spearmanr([r["predicted_mrl"] for r in rank],
                              [r["measured_mrl"] for r in rank])[0])
        rlo, rhi = rho_ci([r["predicted_mrl"] for r in rank],
                          [r["measured_mrl"] for r in rank])
        ret = EXPECTED["retained"][fam]
        per_family[fam] = {
            "label": FAMILY_LABELS[fam],
            "n_scored": len(sub),
            "screening": {
                "n_pos": len(hi), "n_neg": len(lo),
                "auroc": round(a, 4),
                "auroc_ci95": [round(clo, 4), round(chi, 4)],
                "ci_clears_chance": bool(clo > 0.5),
                "gate": "> 0.8",
                "pass": bool(a > AUROC_GATE),
                "retained_auroc": ret["auroc"],
                "delta_vs_retained": round(a - ret["auroc"], 4),
            },
            "ranking": {
                "n": len(rank),
                "spearman_rho": round(rho, 4),
                "rho_ci95_descriptive": [round(rlo, 4), round(rhi, 4)],
                "gate": ">= 0.6",
                "pass": bool(rho >= RHO_GATE),
                "retained_rho": ret["rho"],
                "delta_vs_retained": round(rho - ret["rho"], 4),
            },
            "tier_sanity": {
                "high_tier_mean_predicted": round(float(np.mean(hi)), 3),
                "low_tier_mean_predicted": round(float(np.mean(lo)), 3),
            },
        }

    # pooled tier sanity (retained S0 context: 6.34 vs 2.48)
    hi_all = [r["predicted_mrl"] for r in ok if r["role"] == "binder"]
    lo_all = [r["predicted_mrl"] for r in ok if r["role"] == "negative"]
    pooled_sanity = {
        "high_tier_mean_predicted": round(float(np.mean(hi_all)), 3),
        "low_tier_mean_predicted": round(float(np.mean(lo_all)), 3),
        "retained_context": "6.34 vs 2.48 (retained S0 sanity)",
    }

    # 1:1 reproduction vs the retained scoring JSONL
    repro: dict = {"source": str(RETAINED_SCORING.relative_to(PROJECT_ROOT))}
    if RETAINED_SCORING.exists():
        old = {}
        for line in RETAINED_SCORING.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                old[r["id"]] = r
        pairs = [(r["id"], old[r["id"]]["predicted_mrl"], r["predicted_mrl"])
                 for r in ok if r["id"] in old]
        exact = sum(1 for _, a, b in pairs if a == b)
        dts = [abs(a - b) for _, a, b in pairs]
        repro.update({
            "n_compared": len(pairs),
            "n_retained_total": len(old),
            "exact_matches": exact,
            "exact_fraction": round(exact / len(pairs), 4) if pairs else None,
            "median_abs_delta_mrl": round(float(np.median(dts)), 4) if dts else None,
            "max_abs_delta_mrl": round(float(max(dts)), 4) if dts else None,
        })

    all_pass = all(
        per_family[f]["screening"]["pass"] and per_family[f]["ranking"]["pass"]
        for f in FAMILIES)
    summary = {
        "analysis": "Exp14 / paper-E7 MRL expression-oracle certification "
                    "(reset run; retained E7 2026-08-11 re-registered)",
        "mode": mode_label,
        "anchor_set": {
            "path": str(ANCHOR_JSON.relative_to(PROJECT_ROOT)),
            "n_entries": EXPECTED["n_entries"],
            "families": FAMILY_LABELS,
            "source": "Sample et al. 2019 MPRA (Nat Biotechnol 37:803), GEO GSE114002",
            "convention": "DNA anchor sequences verbatim; tool-layer production "
                          "normalization (uppercase, T→U) before the service — "
                          "'DNA scored as RNA', service echo recorded per call",
        },
        "conventions": {
            "instrument": "ToolExecutor.run_tool (ToolRegistry, schema-validated .invoke) "
                          "-> deployed GEMORNA microservice as shipped",
            "service": {"gemorna": 8004, "endpoint": "/predict/5utr_mrl"},
            "gpu_map": "deployed instance GPU-pinned 0/1/2 by the bring-up script; "
                       "placement inherited, untouched — zero intervention",
            "capgate_policy": os.environ.get("RNADA_CAPGATE", "enforce"),
            "zero_intervention": "anchor entries verbatim; default tool arguments only; "
                                 "no threshold presets; no in-run retries (resume only)",
            "gates": {"screening": "AUROC > 0.8 (strict), stratified bootstrap 95% CI "
                                   "must clear chance for the certification reading",
                      "ranking": "Spearman rho >= 0.6",
                      "source": "E1/E7 pre-registration (identical gates)"},
            "bootstrap": f"percentile 95% CI, {N_BOOT} resamples, seed {BOOT_SEED} "
                         "(rho CI descriptive — not gate-bearing)",
            "positive_control": "sample2019_egfp_random50 is in-training-distribution; "
                                "its pass certifies the deployed chain, not generalization",
        },
        "n_records": len(records),
        "n_success": len(ok),
        "n_failed": len(records) - len(ok),
        "failed_ids": [r["id"] for r in records if not r["success"]],
        "per_family": per_family,
        "pooled_tier_sanity": pooled_sanity,
        "reproduction_vs_retained": repro,
        "decision_bits": [
            f"{FAMILY_LABELS[f]}: AUROC {per_family[f]['screening']['auroc']:.4f} "
            f"(CI {per_family[f]['screening']['auroc_ci95']}) gate > {AUROC_GATE}: "
            f"{'PASS' if per_family[f]['screening']['pass'] else 'FAIL'}; "
            f"rho {per_family[f]['ranking']['spearman_rho']:+.4f} "
            f"(CI {per_family[f]['ranking']['rho_ci95_descriptive']}) gate >= {RHO_GATE}: "
            f"{'PASS' if per_family[f]['ranking']['pass'] else 'FAIL'} "
            f"[retained {EXPECTED['retained'][f]['auroc']:.3f} / {EXPECTED['retained'][f]['rho']:.3f}]"
            for f in FAMILIES
        ] + [
            f"E7 verdict (all three families × both gates): "
            + ("GO — MRL oracle certified (verified/verified) on all families; "
               "random50 read as the in-distribution positive control"
               if all_pass else
               "NO-GO — at least one family/gate cell fails; certification "
               "downgraded accordingly (descriptive wording, never absolute)"),
        ],
    }
    return summary


def load_done(out: Path) -> set[str]:
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                done.add(r["id"])
    return done


def run_mode(mode: str, entries: list[dict], resume: bool) -> int:
    out = RESULTS_DIR / f"{mode}.jsonl"
    scratch = RESULTS_DIR / "scratch" / mode
    done = load_done(out) if resume else set()
    if not resume and out.exists():
        out.unlink()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    executor = build_executor()
    todo = [e for e in entries if e["id"] not in done]
    print(f"[{mode}] {len(todo)} to score ({len(done)} already done)", flush=True)
    with out.open("a", encoding="utf-8") as fh:
        for i, entry in enumerate(todo, 1):
            rec = score_entry(entry, executor, scratch)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{mode}] {i}/{len(todo)} {entry['id']} ok={rec['success']} "
                  f"mrl={rec['predicted_mrl']} {rec['elapsed_seconds']}s", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true", help="score the 6-entry pilot subset")
    mode.add_argument("--run", action="store_true", help="score the full 706-entry anchor set")
    mode.add_argument("--summary", action="store_true", help="write summary.json")
    parser.add_argument("--resume", action="store_true",
                        help="skip entries with a successful record on disk")
    args = parser.parse_args()

    anchor = load_anchor()
    entries = anchor["entries"]

    if args.pilot:
        subset = [e for e in entries if e["id"] in PILOT_IDS]
        assert len(subset) == len(PILOT_IDS), "pilot ids missing from anchor set"
        status = run_mode("pilot", subset, args.resume)
        # informational cross-check against the retained JSONL (no gate)
        if RETAINED_SCORING.exists():
            old = {}
            for line in RETAINED_SCORING.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    old[r["id"]] = r["predicted_mrl"]
            pilot_out = RESULTS_DIR / "pilot.jsonl"
            if pilot_out.exists():
                for line in pilot_out.read_text().splitlines():
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    if r["id"] in old:
                        print(f"[pilot-check] {r['id']}: new {r['predicted_mrl']} "
                              f"vs retained {old[r['id']]} "
                              f"(d {round(abs(r['predicted_mrl'] - old[r['id']]), 4)})")
        return status
    if args.run:
        return run_mode("records", entries, args.resume)
    if args.summary:
        recs = []
        for name in ("records.jsonl",):
            p = RESULTS_DIR / name
            if p.exists():
                recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        if not recs:
            print("no records.jsonl — run --run first", file=sys.stderr)
            return 1
        summary = analyze(recs, "full-run")
        out = RESULTS_DIR / "summary.json"
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(json.dumps({k: summary[k] for k in
                          ("n_records", "n_success", "n_failed", "decision_bits")},
                         ensure_ascii=False, indent=1))
        print(f"summary -> {out}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
