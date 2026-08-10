#!/usr/bin/env python3
"""Pilot P1 (2026-08-03): junction-aware codon optimizer — design-time objective
integration as an alternative to post-hoc BMC coordination (Type-I).

MOTIVATION (root cause R2/R4 from the 2026-08-03 failure analysis)
------------------------------------------------------------------
Fig-3 showed BMC has NO main effect for full-length mRNA design (all 11 metrics
NS at bmc1_vs_serial). Code inspection of
``full_length_mrna_design.py::_regenerate_modules`` explains why: Type-I
coordination can only (a) nudge lambda along LinearDesign's deterministic 1-D
path, (b) reuse diagnosis-set CDS seeds, (c) shuffle 6 terminal codons x 4
variants, (d) switch UTR presets. The junction objectives (junction MFE,
AUG/Kozak burial) live OUTSIDE the design tool's objective, and the reachable
neighbourhood under coordination is tiny — so on targets where the serial run
is already locally optimal, BMC has nowhere to go.

This script tests the alternative: integrate the junction objectives INTO the
codon-optimization step itself. Starting from a serial run's best CDS, a
simulated-annealing search over synonymous codons in the two junction windows
directly optimizes a scalarized objective that includes junction MFE,
AUG/Kozak accessibility, GC continuity, and CAI. Everything is local (CAI via
agent_core.sequence_utils; folding via the LinearFold microservice on 8015,
exactly the metric path used by the workflow's JunctionEvaluator).

GO/NO-GO (pre-registered, pilot-scale)
--------------------------------------
6 targets (hard: HER2, Beta_galactosidase, Influenza_HA_H1N1; easy: Insulin,
EPO, Growth_hormone) x 3 reps, each rep seeded from that rep's serial best
(fig3t1_t1_<T>_r0_rep<k> session artifact).
  GO: on hard targets the optimizer eliminates AUG/Kozak burial in >= 2/3 of
      runs AND improves junction_5utr_cds_mfe_per_nt (less negative) vs the
      serial baseline without degrading CAI by more than 0.02; easy targets
      not degraded.
  NO-GO: no consistent junction gain -> the conflict is not sequence-reachable
      in the codon neighbourhood either; pivot to UTR-side design integration.

Objective (prototype constants, documented for reproducibility):
    f = 1.0*CAI
        - 0.5*(|j1_mfe_per_nt| + |j2_mfe_per_nt|)   # both junctions: less paired = better
        - 0.15*aug_buried - 0.15*kozak_buried        # translation-start accessibility
        - 0.1*(j1_gc_diff + j2_gc_diff)              # GC continuity
        + w_stab*full_mfe_per_nt                     # v2: global stability reward (see below)
Modeling choice: for BOTH junctions "less negative mfe_per_nt" is treated as
better (accessibility), matching how the workflow's diagnosis reads junction
over-stability as a conflict.

P1 v2 (2026-08-04): tunable global-stability weight
---------------------------------------------------
v1 cost: junction repair degrades GLOBAL stability (full-construct mfe/nt vs
serial baseline: +0.009/nt large proteins, +0.044/nt small proteins). v2 adds
a user-controllable knob w_stab: the SA objective gains a stability reward
(mfe is negative, so maximizing f rewards more stable folds). w_stab=0
reproduces v1 EXACTLY (no extra folds, identical cost and trajectory).

Design note (2026-08-04, measured): folding the full construct per candidate
is infeasible in-loop (LinearFold service: 3.1 s for HER2 3965 nt -> ~2.5 h
per cell). The in-loop stability signal is therefore a PROXY: two extended
terminal windows (STAB_UTR_NT=40 UTR + STAB_CDS_NT=120 CDS per side, ~160 nt,
~0.2 s per fold, memoized so each SA step folds only the mutated side). The
proxy is VALIDATED post-hoc: every run still measures the exact
full_construct_mfe_per_nt once at the end, and the pre-registered primary
metric below uses the EXACT value, not the proxy. If the proxy does not track
global stability, the sweep curve will be flat and the NO-GO is documented
as-is.

PRE-REGISTERED SWEEP (approved in REDESIGN_2026-08-03_CALIBRATED_AGENT.md §4.1):
  Matrix: same 18 cells (6 targets x 3 reps, same serial seeds, iters=3000,
  same sa_seed=1000+rep per rep) x w_stab in {0.1, 0.25, 0.5, 1.0}; w_stab=0
  results already exist (v1, 18/18). Compute per cell is matched by
  construction (same iters/seed) — no best-of-pool comparison is made.
  Execution: 6 parallel shards (one per target) against the CPU LinearFold
  service (subprocess-per-request, no global lock; 128-core host, load ~5);
  GPU services untouched (single-worker rule unaffected).
  Hypothesis: increasing w_stab monotonically reduces the stability cost
  while retaining burial repair; a knee exists where hard-target repair rate
  is still >= 2/3 but stability cost is substantially lower than v1.
  Primary metrics per weight: (a) hard-target AUG/Kozak burial repair rate;
  (b) median stability cost = optimized full_construct_mfe_per_nt - serial
  baseline full_mfe_per_nt; (c) median delta CAI; (d) median delta
  junction_5utr_cds_mfe_per_nt.
  GO: some weight keeps hard-target repair >= 2/3 AND stability cost <= 50%
  of the v1 (w_stab=0) cost AND CAI drop <= 0.02 -> that weight becomes the
  recommended default for FullLengthMrnaDesignWorkflow integration (lock
  process per INTERFACE_LOCKS.md §14). NO-GO: the trade-off is not
  sequence-reachable — document the Pareto curve as-is.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/junction_aware_codon_optimizer.py \
        [--targets HER2,...] [--reps 0,1,2] [--iters 3000] [--w-stabs 0.1,0.25,0.5,1.0] [--resume]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT  # noqa: E402

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
DEFAULT_OUTPUT = RESULTS_DIR / "p1_v2_stability_sweep.jsonl"
V1_OUTPUT = RESULTS_DIR / "p1_junction_optimizer.jsonl"  # v1 results (w_stab=0), read-only reference

HARD_TARGETS = ["HER2", "Beta_galactosidase", "Influenza_HA_H1N1"]
EASY_TARGETS = ["Insulin", "EPO", "Growth_hormone"]
PILOT_TARGETS = HARD_TARGETS + EASY_TARGETS

# Objective weights (see module docstring)
W_CAI = 1.0
W_JUNCTION = 0.5
W_BURIAL = 0.15
W_GC = 0.1

JUNCTION_OVERLAP_NT = 20  # must match JunctionEvaluator's 20-nt overlap windows
WINDOW_CODONS = 10        # mutable codons at each terminus (30 nt >= 20-nt slice)

# v2 stability proxy windows: 40 nt UTR context + 120 nt CDS per terminus
STAB_UTR_NT = 40
STAB_CDS_NT = 120


# ── Serial baseline extraction ──────────────────────────────────────────────

def load_serial_seed(target: str, rep: int) -> dict | None:
    """Load the serial (r0) run's best candidate from its session artifact."""
    sess = PROJECT_ROOT / "workspace" / "sessions" / f"fig3t1_t1_{target}_r0_rep{rep}"
    files = sorted(glob.glob(str(sess / "workflow_results_*.json")))
    if not files:
        return None
    d = json.loads(Path(files[-1]).read_text())
    bc = d.get("best_candidate") or {}
    md = bc.get("metadata") or {}
    utr5 = md.get("utr5_sequence") or ""
    utr3 = md.get("utr3_sequence") or ""
    full = bc.get("sequence") or ""
    # NOTE (2026-08-03): metadata.cds_sequence / protein_sequence in session
    # artifacts are TRUNCATED with a literal "...(truncated)" suffix beyond a
    # few hundred chars — never use them. The intact CDS is sliced out of the
    # full-length candidate sequence by UTR lengths instead.
    if not (full and utr5 and utr3):
        return None
    if not (full.startswith(utr5) and full.endswith(utr3)):
        return None
    cds = full[len(utr5) : len(full) - len(utr3)]
    if len(cds) % 3 != 0 or len(cds) < 60:
        return None
    return {
        "target_id": target,
        "rep": rep,
        "session_id": d.get("session_id"),
        "cds_sequence": cds,
        "utr5_sequence": utr5,
        "utr3_sequence": utr3,
        "cai_species": md.get("cai_species") or "Homo sapiens",
        "baseline_scores": bc.get("scores") or {},
    }


def load_shard_baselines() -> dict:
    """Latest successful per (target, rounds, rep) best-metrics from fig3 shards."""
    latest: dict = {}
    for shard in ["a", "b"]:
        fp = RESULTS_DIR / f"fig3_type1_shard_{shard}.jsonl"
        if not fp.exists():
            continue
        for line in fp.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("success"):
                continue
            key = (r["target_id"], r["bmc_max_rounds"], r["rep"])
            latest[key] = r  # file order: latest wins
    return latest


# ── Codon / CAI machinery (reuses agent_core.sequence_utils) ────────────────

def _genetic_code():
    from Bio.Data import CodonTable

    table = CodonTable.unambiguous_dna_by_id[1]
    aa_to_codons: dict[str, list[str]] = {}
    for codon, aa in table.forward_table.items():
        aa_to_codons.setdefault(aa, []).append(codon)
    return table.forward_table, set(table.stop_codons), aa_to_codons


def _cai_weights(species: str) -> dict[str, float]:
    from agent_core.sequence_utils import build_cai_weights, resolve_species_name
    from agent_core.tools import _load_builtin_codon_tables

    builtin = _load_builtin_codon_tables()
    resolved = resolve_species_name(species)
    key = resolved if resolved in builtin else species
    if key not in builtin:
        raise ValueError(f"no built-in codon table for {species!r} -> {resolved!r}")
    # NOTE: build_cai_weights keys are RNA codons (AUG); callers working in DNA
    # must translate T->U before lookup (see _cai_of_codons).
    return build_cai_weights(builtin[key])


def _w_rna(weights: dict[str, float], dna_codon: str) -> float:
    return weights.get(dna_codon.replace("T", "U"), 1e-9)


def _cds_to_dna(cds: str) -> str:
    return cds.upper().replace("U", "T")


def _to_alphabet(seq_dna: str, like: str) -> str:
    return seq_dna.replace("T", "U") if "U" in like.upper() else seq_dna


def _cai_of_codons(codons: list[str], weights: dict[str, float]) -> float:
    logs = [math.log(max(_w_rna(weights, c), 1e-9)) for c in codons if c not in ("TAA", "TAG", "TGA")]
    return math.exp(sum(logs) / len(logs)) if logs else 0.0


# ── Junction metrics (identical semantics to JunctionEvaluator) ─────────────

class JunctionFolder:
    """Memoized LinearFold folder + burial/GC checks mirroring JunctionEvaluator."""

    def __init__(self, service_url: str, tmp_dir: Path):
        self.service_url = service_url
        self.tmp_dir = tmp_dir
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict] = {}
        self._fp = self.tmp_dir / f"junction_fold_{os.getpid()}.fa"
        self.n_calls = 0

    def fold(self, seq: str) -> dict:
        if seq in self._cache:
            return self._cache[seq]
        from agent_core.tools import predict_rna_secondary_structure_with_linearfold

        self._fp.write_text(f">q\n{seq}\n")
        out = predict_rna_secondary_structure_with_linearfold.func(filepath=str(self._fp))
        self.n_calls += 1
        res = {
            "mfe": out.get("mfe"),
            "structure": out.get("structure", ""),
        }
        self._cache[seq] = res
        return res

    @staticmethod
    def gc(seq: str) -> float:
        if not seq:
            return 0.0
        s = seq.upper()
        return (s.count("G") + s.count("C")) / len(s)

    def junction_metrics(self, utr5: str, cds: str, utr3: str) -> dict:
        """Same 20+20 windows, mfe/nt, GC diff, AUG/Kozak burial as the workflow."""
        from agent_core.workflows.evaluators import JunctionEvaluator

        j1_left = utr5[-JUNCTION_OVERLAP_NT:]
        j1_right = cds[:JUNCTION_OVERLAP_NT]
        j1 = j1_left + j1_right
        f1 = self.fold(j1)
        m1 = f1.get("mfe")
        out = {
            "j1_mfe": m1,
            "j1_mfe_per_nt": (m1 / len(j1)) if m1 is not None and j1 else None,
            "j1_gc_diff": abs(self.gc(j1_left) - self.gc(j1_right)),
            "j1_structure": f1.get("structure", ""),
        }
        if out["j1_structure"]:
            chk = JunctionEvaluator._check_translation_start(
                j1, out["j1_structure"], cds_start_offset=len(j1_left)
            )
            out["aug_buried"] = bool(chk.get("aug_buried"))
            out["kozak_buried"] = bool(chk.get("kozak_buried"))
        else:
            out["aug_buried"] = out["kozak_buried"] = None

        j2_left = cds[-JUNCTION_OVERLAP_NT:]
        j2_right = utr3[:JUNCTION_OVERLAP_NT]
        j2 = j2_left + j2_right
        f2 = self.fold(j2)
        m2 = f2.get("mfe")
        out.update(
            {
                "j2_mfe": m2,
                "j2_mfe_per_nt": (m2 / len(j2)) if m2 is not None and j2 else None,
                "j2_gc_diff": abs(self.gc(j2_left) - self.gc(j2_right)),
            }
        )
        return out


def objective(jm: dict, cai: float, stab_mfe_per_nt: float | None = None, w_stab: float = 0.0) -> float:
    f = W_CAI * cai
    if jm.get("j1_mfe_per_nt") is not None:
        f -= W_JUNCTION * abs(jm["j1_mfe_per_nt"])
    if jm.get("j2_mfe_per_nt") is not None:
        f -= W_JUNCTION * abs(jm["j2_mfe_per_nt"])
    if jm.get("aug_buried"):
        f -= W_BURIAL
    if jm.get("kozak_buried"):
        f -= W_BURIAL
    f -= W_GC * (jm.get("j1_gc_diff") or 0.0)
    f -= W_GC * (jm.get("j2_gc_diff") or 0.0)
    # v2: global stability reward (mfe/nt is negative; maximizing f favours
    # more stable full-construct folds). w_stab=0 -> exact v1 objective.
    if w_stab > 0.0 and stab_mfe_per_nt is not None:
        f += w_stab * stab_mfe_per_nt
    return f


# ── Simulated annealing over synonymous codons in junction windows ──────────

def optimize_cds(
    seed: dict,
    folder: JunctionFolder,
    iters: int,
    sa_seed: int,
    t0: float = 0.05,
    t_end: float = 0.002,
    w_stab: float = 0.0,
) -> dict:
    rng = random.Random(sa_seed)
    forward_table, stop_codons, aa_to_codons = _genetic_code()
    weights = _cai_weights(seed["cai_species"])

    cds_dna = _cds_to_dna(seed["cds_sequence"])
    codons = [cds_dna[i : i + 3] for i in range(0, len(cds_dna) - 2, 3)]
    n_codons = len(codons)
    has_stop = codons and codons[-1] in stop_codons

    # Mutable positions: first/last WINDOW_CODONS codons, excluding the start
    # codon (fixed AUG), the terminal stop, and single-codon amino acids.
    mutable: list[int] = []
    last_idx = n_codons - 2 if has_stop else n_codons - 1
    for i in list(range(1, min(WINDOW_CODONS, n_codons))) + list(
        range(max(1, n_codons - WINDOW_CODONS - (1 if has_stop else 0)), last_idx + 1)
    ):
        aa = forward_table.get(codons[i])
        if aa and len(aa_to_codons.get(aa, [])) > 1 and i not in mutable:
            mutable.append(i)

    utr5 = seed["utr5_sequence"]
    utr3 = seed["utr3_sequence"]
    use_rna = "U" in seed["cds_sequence"].upper()

    def cds_str(codon_list: list[str]) -> str:
        dna = "".join(codon_list)
        return dna.replace("T", "U") if use_rna else dna

    def evaluate(codon_list: list[str]) -> tuple[float, dict, float]:
        seq = cds_str(codon_list)
        jm = folder.junction_metrics(utr5, seq, utr3)
        cai = _cai_of_codons(codon_list, weights)
        stab = None
        if w_stab > 0.0:
            # v2: extended-terminal-window stability proxy (memoized folds; each
            # SA step mutates one terminus, so only that side is a cache miss).
            s1 = utr5[-STAB_UTR_NT:] + seq[:STAB_CDS_NT]
            s2 = seq[-STAB_CDS_NT:] + utr3[:STAB_UTR_NT]
            parts = []
            for s in (s1, s2):
                m = folder.fold(s).get("mfe")
                if m is not None:
                    parts.append(m / len(s))
            if parts:
                stab = sum(parts) / len(parts)
        return objective(jm, cai, stab, w_stab), jm, cai

    cur = list(codons)
    cur_f, _, _ = evaluate(cur)
    best = list(cur)
    best_f = cur_f
    trace = [cur_f]

    for it in range(iters):
        t = t0 * (t_end / t0) ** (it / max(iters - 1, 1))
        pos = rng.choice(mutable)
        aa = forward_table[cur[pos]]
        alts = [c for c in aa_to_codons[aa] if c != cur[pos]]
        if not alts:
            continue
        # CAI-weighted proposal (favours high-usage codons, keeps exploration)
        w = [max(_w_rna(weights, c), 1e-6) for c in alts]
        new_codon = rng.choices(alts, weights=w, k=1)[0]
        old_codon = cur[pos]
        cur[pos] = new_codon
        new_f, _, _ = evaluate(cur)
        d = new_f - cur_f
        if d >= 0 or rng.random() < math.exp(d / max(t, 1e-9)):
            cur_f = new_f
            if new_f > best_f:
                best_f = new_f
                best = list(cur)
        else:
            cur[pos] = old_codon
        if (it + 1) % 200 == 0:
            trace.append(cur_f)

    final_f, final_jm, final_cai = evaluate(best)
    # Post-hoc degradation check: fold the full construct once (the SA loop
    # only ever re-folds the two 40-nt junction windows).
    full_seq = utr5 + cds_str(best) + utr3
    full_fold = folder.fold(full_seq)
    full_mfe = full_fold.get("mfe")
    return {
        "optimized_cds": cds_str(best),
        "objective_final": final_f,
        "objective_trace": trace,
        "cai": final_cai,
        "junction": final_jm,
        "full_construct_mfe": full_mfe,
        "full_construct_mfe_per_nt": (full_mfe / len(full_seq)) if full_mfe is not None else None,
        "n_mutable_positions": len(mutable),
        "fold_calls": folder.n_calls,
    }


# ── Driver ──────────────────────────────────────────────────────────────────

def load_done(output: Path) -> set[tuple]:
    done = set()
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                done.add((r["target_id"], r["rep"], r.get("w_stab", 0.0)))
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--targets", default=",".join(PILOT_TARGETS))
    parser.add_argument("--reps", default="0,1,2")
    parser.add_argument("--iters", type=int, default=3000)
    parser.add_argument("--w-stabs", default="0.1,0.25,0.5,1.0",
                        help="comma list of stability weights; 0.0 reproduces v1 exactly")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    targets = args.targets.split(",")
    reps = [int(x) for x in args.reps.split(",")]
    w_stabs = [float(x) for x in args.w_stabs.split(",")]

    # Service pre-flight: the LinearFold direct-call chain does NOT go through
    # the workflow pre-flight (RESUME_CHECKPOINT note 8) — pull it up ourselves.
    from agent_core.services.service_manager import (
        CAPABILITY_SERVICE_MAP,
        ensure_services_ready,
    )

    ok, msgs = ensure_services_ready(
        [CAPABILITY_SERVICE_MAP["predict_rna_secondary_structure_with_linearfold"]]
    )
    print(f"service preflight: ok={ok} {msgs}", flush=True)
    if not ok:
        return 1

    folder = JunctionFolder(
        "http://127.0.0.1:8015/fold", PROJECT_ROOT / "workspace" / "tmp"
    )
    shard = load_shard_baselines()
    done = load_done(args.output) if args.resume else set()

    n_ok = n_fail = n_skip = 0
    jobs = [(t, r, w) for t in targets for r in reps for w in w_stabs]
    for i, (target, rep, w_stab) in enumerate(jobs, 1):
        if (target, rep, w_stab) in done:
            n_skip += 1
            continue
        seed = load_serial_seed(target, rep)
        if seed is None:
            print(f"[{i}/{len(jobs)}] {target} rep{rep}: NO serial session artifact, skipped")
            n_fail += 1
            continue
        base_serial = (shard.get((target, 0, rep)) or {}).get("best") or {}
        base_bmc1 = (shard.get((target, 1, rep)) or {}).get("best") or {}

        t_start = time.perf_counter()
        try:
            res = optimize_cds(seed, folder, iters=args.iters, sa_seed=1000 + rep, w_stab=w_stab)
        except Exception as exc:  # noqa: BLE001 - record and continue
            print(f"[{i}/{len(jobs)}] {target} rep{rep}: FAIL {exc}", flush=True)
            n_fail += 1
            continue
        elapsed = time.perf_counter() - t_start

        jm = res["junction"]
        out = {
            "target_id": target,
            "target_class": "hard" if target in HARD_TARGETS else "easy",
            "rep": rep,
            "w_stab": w_stab,
            "success": True,
            "iters": args.iters,
            "elapsed_seconds": round(elapsed, 1),
            "n_mutable_positions": res["n_mutable_positions"],
            "fold_calls": res["fold_calls"],
            "cai_species": seed["cai_species"],
            "optimized": {
                "cds_cai": res["cai"],
                "junction_5utr_cds_mfe": jm["j1_mfe"],
                "junction_5utr_cds_mfe_per_nt": jm["j1_mfe_per_nt"],
                "junction_5utr_cds_aug_buried": jm["aug_buried"],
                "junction_5utr_cds_kozak_buried": jm["kozak_buried"],
                "junction_5utr_cds_gc_diff": jm["j1_gc_diff"],
                "junction_cds_3utr_mfe": jm["j2_mfe"],
                "junction_cds_3utr_mfe_per_nt": jm["j2_mfe_per_nt"],
                "junction_cds_3utr_gc_diff": jm["j2_gc_diff"],
                "full_construct_mfe_per_nt": res["full_construct_mfe_per_nt"],
            },
            "baseline_serial": {
                k: base_serial.get(k)
                for k in [
                    "cds_cai",
                    "junction_5utr_cds_mfe",
                    "junction_5utr_cds_mfe_per_nt",
                    "junction_5utr_cds_aug_buried",
                    "junction_5utr_cds_kozak_buried",
                    "junction_5utr_cds_gc_diff",
                    "junction_cds_3utr_mfe",
                    "junction_cds_3utr_mfe_per_nt",
                    "junction_cds_3utr_gc_diff",
                    "full_mfe_per_nt",
                ]
            },
            "baseline_bmc1": {
                k: base_bmc1.get(k)
                for k in [
                    "cds_cai",
                    "junction_5utr_cds_mfe_per_nt",
                    "junction_5utr_cds_aug_buried",
                    "junction_5utr_cds_kozak_buried",
                    "junction_cds_3utr_mfe_per_nt",
                ]
            },
            "optimized_cds": res["optimized_cds"],
            "seed_cds": seed["cds_sequence"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
        n_ok += 1
        b = out["baseline_serial"]
        o = out["optimized"]
        def _fmt(x: object) -> str:
            return f"{x:.4f}" if isinstance(x, (int, float)) else str(x)

        print(
            f"[{i}/{len(jobs)}] {target} rep{rep} w={w_stab}: "
            f"AUG {b.get('junction_5utr_cds_aug_buried')}->{o['junction_5utr_cds_aug_buried']} "
            f"Kozak {b.get('junction_5utr_cds_kozak_buried')}->{o['junction_5utr_cds_kozak_buried']} "
            f"j1/nt {_fmt(b.get('junction_5utr_cds_mfe_per_nt'))}->{_fmt(o['junction_5utr_cds_mfe_per_nt'])} "
            f"CAI {(b.get('cds_cai') or 0):.3f}->{o['cds_cai']:.3f} "
            f"full/nt {_fmt(b.get('full_mfe_per_nt'))}->{_fmt(o['full_construct_mfe_per_nt'])} "
            f"({elapsed:.0f}s, {res['fold_calls']} folds)",
            flush=True,
        )

    print(f"\nDone: {n_ok} ok, {n_fail} failed/no-seed, {n_skip} resumed-skip -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
