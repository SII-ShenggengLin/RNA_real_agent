#!/usr/bin/env python
"""Junction ddG Phase 0 pilot — pre-registered metric-validity + Route-C gates.

Date: 2026-08-05. Motivation: the legacy junction metric (isolated 40-nt
fragment fold + AUG/Kozak pairing booleans, JunctionEvaluator semantics) proved
unreliable in P2 (junction_integrated_optimizer_summary.json NO-GO: the
global-fold window penalty cleared window pairs yet fragment-fold burial
persisted — penalty/metric coordinate mismatch). This pilot evaluates the
REPLACEMENT metric — full-length constrained-fold ddG — and whether synonymous
codon shuffling at the N-terminal junction can improve it at fixed lambda
(decides whether the E4 executor Route-C "generate-and-select" design holds).

NEW METRIC DEFINITION (registered here, before any run)
--------------------------------------------------------
For a full-length mRNA construct ``full = utr5 + cds + utr3``:
  ddG_open = MFE_constrained - MFE_unconstrained   (should be >= 0)
Both folds use the LinearFold service (8015, LinearFold-C default parameters,
same backend as every other full-construct fold in this project). The
constraint string is '?' over the full length with '.' (forced unpaired,
LinearFold constraint alphabet per external_repos/LinearFold/README.md:
"? . ( )" = unknown / unpaired / left / right) inside the AUG-context window.
The CDS start offset is len(utr5) from the seed slicing — we do NOT search for
AUG motifs (uAUG hazard). Two window definitions are computed for every
candidate:
  W1 (narrow): [cds_start - 6, cds_start + 9)  -> 15 nt (AUG + Kozak context)
  W2 (wide):   [max(0, cds_start - 60), cds_start + 30)  -> <=90 nt
               (5'UTR tail 60 nt + CDS head 30 nt; clipped to the actual UTR
               length — seed UTR5s are 39-54 nt, so W2 is 69-84 nt; the actual
               window is recorded per row)
PRIMARY window for the gates: W1. W2 is descriptive.

CORRECTNESS PROBE (runs before the matrix; aborts on failure)
-------------------------------------------------------------
On the Insulin rep0 SEED construct: fold unconstrained + W1/W2 constrained and
assert (a) 0 paired bases ('('/')') inside each constrained window, (b) both
ddG_open >= 0. If either fails the constraint is not in effect -> stop and
debug; the matrix is never run on an unverified constraint path. The same two
checks are then recorded per candidate row (obedience + non-negativity flags).

DESIGN MATRIX
-------------
3 easy targets (Insulin, EPO, Growth_hormone), rep0 serial seeds
(``workspace/sessions/fig3t1_t1_<target>_r0_rep0`` via ``load_serial_seed``;
UTRs fixed from the seed, only the CDS varies).
  lambda axis:  lambda in {0, 1, 4, 10}, one deterministic LinearDesign call
    (legacy POST 8014 /generate/cds via ``design_mrna_cds_with_lineardesign``)
    per (target, lambda) -> 12 parent CDSs.
  shuffle axis: each parent CDS -> ``shuffle_cds_junction_codons``
    (n_terminus, codon_count=6, num_variants=8, species="Homo sapiens"
    = the seed metadata cai_species, seed=20260805 fixed) -> <=8 variants.
  cells ~= 3 x 4 x (1 + 8) = 108 candidates.
Per candidate: full-length ddG_open (W1/W2), unconstrained full MFE + MFE/nt,
CDS CAI (compute_cai_for_cds_sequence, Homo sapiens), J1 fragment burial
booleans (JunctionFolder.junction_metrics = legacy metric, kept as the
old-vs-new consistency control). ViennaRNA (8003) unconstrained full-length
MFE on the 12 parents only (LinearFold-vs-Vienna consistency spot check;
~1 kb O(n^3) is acceptable).

PRE-REGISTERED GATES (fixed before the run; do not edit post hoc)
-----------------------------------------------------------------
Gate 1 — metric validity (GO/NO-GO):
  1a. constraint obedience rate = 100% (0 paired bases in the constrained
      window, over all candidates x both windows);
  1b. ddG_open >= 0 rate = 100% (all candidates x both windows);
  1c. Pearson r of LinearFold vs ViennaRNA unconstrained full-length MFE over
      the 12 parents — DESCRIPTIVE, no threshold.
Gate 2 — Route-C viability (GO/NO-GO):
  Per (target, lambda): improvement = parent ddG_open_W1 - min over variants
  ddG_open_W1; the variant attaining that min is the "best variant" of the
  cell, with dCAI = variant CAI - parent CAI and dMFE/nt = variant
  unconstrained MFE/nt - parent MFE/nt. Per target: median improvement over
  the 4 lambdas, median dCAI, median |dMFE/nt| (over the per-cell best
  variants). A target PASSES if median improvement >= 1.0 kcal/mol AND
  median dCAI >= -0.02 AND median |dMFE/nt| <= 0.01 kcal/mol/nt.
  GO if >= 2 of 3 targets pass -> proceed to Phase 1; otherwise NO-GO ->
  fall back to plan A.
The lambda-axis trend of ddG_open (user hypothesis: ddG falls as lambda rises,
at an MFE cost) is DESCRIPTIVE ONLY — reported, not gated.

Outputs:
  - results/junction_ddg_pilot_runs.jsonl (one row per candidate; parents have
    variant_index=-1; resume dedups per (target, lambda, variant_index),
    latest row wins)
  - results/junction_ddg_pilot_summary.json (both gates, per-target table,
    lambda-axis descriptive stats, old-vs-new consistency, GO/NO-GO)
  - results/MODEL_API_USAGE.md row (added after the run): no LLM calls.

Services: 8014 (LinearDesign), 8015 (LinearFold), 8003 (ViennaRNA) are
pre-flighted and auto-started via ``ensure_services_ready`` — no manual
launcher needed. No LLM calls anywhere in this script.

Runbook (single background worker, log on disk, pgrep before starting):
  cd rna_agent_system
  PYTHONPATH="$(pwd):$PYTHONPATH" setsid nohup python \
      experiments/junction_ddg_pilot_eval.py --workers 4 \
      > experiments/results/junction_ddg_pilot.log 2>&1 &
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from junction_aware_codon_optimizer import (  # noqa: E402
    JunctionFolder,
    _genetic_code,
    load_serial_seed,
)

FOLD_URL = "http://127.0.0.1:8015/fold"
TMP_DIR = PROJECT_ROOT / "workspace" / "tmp"

DEFAULT_TARGETS = ["Insulin", "EPO", "Growth_hormone"]
REP = 0
LAMBDAS = [0.0, 1.0, 4.0, 10.0]

# Shuffle axis (registered constants).
SHUFFLE_CODON_COUNT = 6
SHUFFLE_NUM_VARIANTS = 8
SHUFFLE_SEED = 20260805
CAI_SPECIES = "Homo sapiens"  # seed metadata cai_species for all 3 targets

# Window definitions (registered).
W1_UPSTREAM_NT = 6
W1_DOWNSTREAM_NT = 9   # from AUG start -> 15 nt total
W2_UTR_NT = 60
W2_CDS_NT = 30

# Pre-registered Gate-2 thresholds.
IMPROVEMENT_MIN = 1.0       # kcal/mol, median per target
DCAI_MIN = -0.02            # median per target (variant - parent)
DMFE_PER_NT_ABS_MAX = 0.01  # kcal/mol/nt, median |.| per target
TARGETS_PASS_MIN = 2        # of 3


def _translate_cds(cds_rna: str) -> str:
    """Same Biopython table as the P1/P2 drivers; stops -> '*'."""
    forward_table, stop_codons, _ = _genetic_code()
    cds = cds_rna.upper().replace("U", "T")
    aas = []
    for i in range(0, len(cds) - 2, 3):
        codon = cds[i : i + 3]
        aas.append("*" if codon in stop_codons else forward_table[codon])
    return "".join(aas)


def w1_window(utr5_len: int) -> tuple[int, int]:
    return utr5_len - W1_UPSTREAM_NT, utr5_len + W1_DOWNSTREAM_NT


def w2_window(utr5_len: int) -> tuple[int, int]:
    return max(0, utr5_len - W2_UTR_NT), utr5_len + W2_CDS_NT


def constraint_string(full_len: int, start: int, end: int) -> str:
    """'?' everywhere, '.' (forced unpaired) inside [start, end)."""
    c = ["?"] * full_len
    for i in range(max(0, start), min(full_len, end)):
        c[i] = "."
    return "".join(c)


def window_pair_count(structure: str, start: int, end: int) -> int:
    return sum(1 for ch in structure[start:end] if ch in "()")


class PilotFolder(JunctionFolder):
    """JunctionFolder + thread-safe memoized constrained folds.

    The base class writes one fixed temp FASTA per process (a race under
    threads) and has no constraints parameter; this subclass gives every call
    its own temp file and caches on (sequence, constraints).
    """

    def __init__(self, service_url: str, tmp_dir: Path):
        super().__init__(service_url, tmp_dir)
        self._ddg_cache: dict[tuple[str, str | None], dict] = {}
        self._counter = 0
        self._lock = threading.Lock()

    def fold(self, seq: str, constraints: str | None = None) -> dict:
        if constraints is None:
            # Route plain fragment folds through the same cache so the base
            # junction_metrics path and the ddG path share results.
            key = (seq, None)
        else:
            key = (seq, constraints)
        if key in self._ddg_cache:
            return self._ddg_cache[key]
        from agent_core.tools import predict_rna_secondary_structure_with_linearfold

        with self._lock:
            self._counter += 1
            idx = self._counter
        fp = self.tmp_dir / (
            f"ddg_fold_{os.getpid()}_{threading.get_ident()}_{idx}.fa"
        )
        fp.write_text(f">q\n{seq}\n")
        out = predict_rna_secondary_structure_with_linearfold.func(
            filepath=str(fp), constraints=constraints
        )
        self.n_calls += 1
        res = {"mfe": out.get("mfe"), "structure": out.get("structure", "")}
        self._ddg_cache[key] = res
        try:
            fp.unlink()
        except OSError:
            pass
        return res


def fold_construct(folder: PilotFolder, utr5: str, cds: str, utr3: str) -> dict:
    """Full-length unconstrained + W1/W2 constrained folds -> ddG metrics."""
    full = utr5 + cds + utr3
    n = len(full)
    u5 = len(utr5)
    w1s, w1e = w1_window(u5)
    w2s, w2e = w2_window(u5)

    f_un = folder.fold(full)
    struct_un = f_un.get("structure") or ""
    mfe_un = f_un.get("mfe")

    out: dict = {
        "full_length": n,
        "mfe_unconstrained": mfe_un,
        "mfe_per_nt_unconstrained": (mfe_un / n) if mfe_un is not None else None,
        "w1": {"start": w1s, "end": w1e, "nt": w1e - w1s},
        "w2": {"start": w2s, "end": w2e, "nt": w2e - w2s},
        "w1_pairs_unconstrained": window_pair_count(struct_un, w1s, w1e),
        "w2_pairs_unconstrained": window_pair_count(struct_un, w2s, w2e),
    }
    for tag, (s, e) in (("w1", (w1s, w1e)), ("w2", (w2s, w2e))):
        cons = constraint_string(n, s, e)
        fc = folder.fold(full, constraints=cons)
        struct_c = fc.get("structure") or ""
        mfe_c = fc.get("mfe")
        obedient = (
            len(struct_c) == n and window_pair_count(struct_c, s, e) == 0
        )
        ddg = (mfe_c - mfe_un) if (mfe_c is not None and mfe_un is not None) else None
        out[f"mfe_constrained_{tag}"] = mfe_c
        out[f"ddg_open_{tag}"] = ddg
        out[f"constraint_obedient_{tag}"] = bool(obedient)
        out[f"ddg_nonneg_{tag}"] = bool(ddg is not None and ddg >= 0)
    return out


def evaluate_candidate(
    folder: PilotFolder,
    utr5: str,
    cds: str,
    utr3: str,
    tmp_dir: Path,
    tag: str,
    do_vienna: bool,
) -> dict:
    """All per-candidate metrics: ddG (new), burial (old), CAI, Vienna spot."""
    metrics = fold_construct(folder, utr5, cds, utr3)

    # Old metric (consistency control): 40-nt fragment fold + burial booleans.
    jm = folder.junction_metrics(utr5, cds, utr3)
    metrics["junction"] = {
        "j1_mfe_per_nt": jm.get("j1_mfe_per_nt"),
        "aug_buried": jm.get("aug_buried"),
        "kozak_buried": jm.get("kozak_buried"),
        "j1_buried": bool(jm.get("aug_buried")) or bool(jm.get("kozak_buried")),
    }

    from agent_core.tools import compute_cai_for_cds_sequence

    cds_fp = tmp_dir / f"ddg_cds_{os.getpid()}_{threading.get_ident()}_{tag}.fa"
    cds_fp.write_text(f">cds\n{cds}\n")
    try:
        cai = compute_cai_for_cds_sequence.func(
            filepath=str(cds_fp), species=CAI_SPECIES
        )
        metrics["cds_cai"] = float(cai["cai_score"])
    finally:
        cds_fp.unlink(missing_ok=True)

    metrics["vienna_mfe_unconstrained"] = None
    if do_vienna:
        from agent_core.tools import predict_rna_secondary_structure

        full = utr5 + cds + utr3
        v_fp = tmp_dir / f"ddg_vienna_{os.getpid()}_{threading.get_ident()}_{tag}.fa"
        v_fp.write_text(f">full\n{full}\n")
        try:
            v = predict_rna_secondary_structure.func(filepath=str(v_fp))
            metrics["vienna_mfe_unconstrained"] = float(v["mfe_kcal_per_mol"])
        finally:
            v_fp.unlink(missing_ok=True)
    return metrics


def run_group(target: str, lam: float, folder: PilotFolder) -> list[dict]:
    """One (target, lambda) group: parent LinearDesign CDS + shuffle variants."""
    rows: list[dict] = []
    t0 = time.time()
    base = {
        "target_id": target,
        "rep": REP,
        "lambda_value": lam,
        "success": False,
        "error": None,
    }
    try:
        seed = load_serial_seed(target, REP)
        if seed is None:
            raise RuntimeError("serial seed not found")
        utr5, utr3 = seed["utr5_sequence"], seed["utr3_sequence"]
        protein = _translate_cds(seed["cds_sequence"]).rstrip("*")

        # Parent: deterministic LinearDesign at this lambda (legacy endpoint).
        from agent_core.tools import design_mrna_cds_with_lineardesign

        TMP_DIR.mkdir(parents=True, exist_ok=True)
        prot_fp = TMP_DIR / f"ddg_protein_{target}_{lam:g}.fa"
        prot_fp.write_text(f">p\n{protein}\n")
        try:
            ld = design_mrna_cds_with_lineardesign.func(
                filepath=str(prot_fp), lambda_value=lam
            )
        finally:
            prot_fp.unlink(missing_ok=True)
        parent_cds = ld["generated_sequence"]

        parent_row = {
            **base,
            "kind": "parent",
            "variant_index": -1,
            "cds_sequence": parent_cds,
            "lineardesign": {
                "cai_score": ld.get("cai_score"),
                "mfe_objective": ld.get("mfe"),
            },
        }
        parent_row["metrics"] = evaluate_candidate(
            folder, utr5, parent_cds, utr3, TMP_DIR,
            tag=f"{target}_{lam:g}_p", do_vienna=True,
        )
        parent_row["success"] = True
        parent_row["elapsed_seconds"] = round(time.time() - t0, 2)
        rows.append(parent_row)

        # Shuffle axis: N-terminal synonymous variants of the parent CDS.
        from agent_core.tools import shuffle_cds_junction_codons

        cds_fp = TMP_DIR / f"ddg_parentcds_{target}_{lam:g}.fa"
        cds_fp.write_text(f">cds\n{parent_cds}\n")
        try:
            sh = shuffle_cds_junction_codons.func(
                filepath=str(cds_fp),
                junction_end="n_terminus",
                codon_count=SHUFFLE_CODON_COUNT,
                num_variants=SHUFFLE_NUM_VARIANTS,
                species=CAI_SPECIES,
                seed=SHUFFLE_SEED,
            )
        finally:
            cds_fp.unlink(missing_ok=True)

        for vi, var in enumerate(sh.get("variants", [])):
            vcds = var["sequence"]
            vrow = {
                **base,
                "kind": "variant",
                "variant_index": vi,
                "cds_sequence": vcds,
                "changed_codons": var.get("changed_codons"),
            }
            try:
                vrow["metrics"] = evaluate_candidate(
                    folder, utr5, vcds, utr3, TMP_DIR,
                    tag=f"{target}_{lam:g}_v{vi}", do_vienna=False,
                )
                vrow["success"] = True
            except Exception as exc:  # noqa: BLE001 - record and continue
                vrow["error"] = f"{type(exc).__name__}: {exc}"
            vrow["elapsed_seconds"] = round(time.time() - t0, 2)
            rows.append(vrow)
    except Exception as exc:  # noqa: BLE001 - group-level failure row
        fail = {**base, "kind": "parent", "variant_index": -1,
                "error": f"{type(exc).__name__}: {exc}"}
        fail["elapsed_seconds"] = round(time.time() - t0, 2)
        if not rows:
            rows.append(fail)
    return rows


def constraint_probe(folder: PilotFolder) -> dict:
    """Pre-matrix correctness probe on the Insulin rep0 SEED construct."""
    seed = load_serial_seed("Insulin", REP)
    utr5, utr3, cds = seed["utr5_sequence"], seed["utr3_sequence"], seed["cds_sequence"]
    m = fold_construct(folder, utr5, cds, utr3)
    probe = {
        "cell": "Insulin rep0 seed CDS",
        "full_length": m["full_length"],
        "w1": m["w1"],
        "w2": m["w2"],
        "mfe_unconstrained": m["mfe_unconstrained"],
        "mfe_constrained_w1": m["mfe_constrained_w1"],
        "mfe_constrained_w2": m["mfe_constrained_w2"],
        "ddg_open_w1": m["ddg_open_w1"],
        "ddg_open_w2": m["ddg_open_w2"],
        "w1_pairs_unconstrained": m["w1_pairs_unconstrained"],
        "w2_pairs_unconstrained": m["w2_pairs_unconstrained"],
        "obedient_w1": m["constraint_obedient_w1"],
        "obedient_w2": m["constraint_obedient_w2"],
        "ddg_nonneg_w1": m["ddg_nonneg_w1"],
        "ddg_nonneg_w2": m["ddg_nonneg_w2"],
    }
    probe["pass"] = bool(
        probe["obedient_w1"] and probe["obedient_w2"]
        and probe["ddg_nonneg_w1"] and probe["ddg_nonneg_w2"]
    )
    return probe


def _median(values: list[float | None]) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return cov / math.sqrt(vx * vy)


def load_done_groups(output: Path) -> set[tuple]:
    """Groups with a SUCCESSFUL parent row are skipped wholesale on resume
    (LinearDesign is deterministic, so a partial group is cheaply rebuilt)."""
    done = set()
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("success") and r.get("kind") == "parent":
                done.add((r["target_id"], float(r["lambda_value"])))
    return done


def load_latest_rows(output: Path) -> list[dict]:
    latest: dict[tuple, dict] = {}
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            key = (r["target_id"], float(r["lambda_value"]), r["variant_index"])
            latest[key] = r
    return list(latest.values())


def build_summary(rows: list[dict], probe: dict, runtime_s: float) -> dict:
    ok = [r for r in rows if r.get("success")]
    parents = [r for r in ok if r["kind"] == "parent"]
    variants = [r for r in ok if r["kind"] == "variant"]

    # Gate 1: metric validity over all candidates x both windows.
    n_obed = n_ddg_checks = n_obed_ok = n_nonneg_ok = 0
    for r in ok:
        m = r["metrics"]
        for tag in ("w1", "w2"):
            n_obed += 1
            n_obed_ok += 1 if m[f"constraint_obedient_{tag}"] else 0
            if m[f"ddg_open_{tag}"] is not None:
                n_ddg_checks += 1
                n_nonneg_ok += 1 if m[f"ddg_nonneg_{tag}"] else 0
    obedience_rate = (n_obed_ok / n_obed) if n_obed else None
    nonneg_rate = (n_nonneg_ok / n_ddg_checks) if n_ddg_checks else None

    lf = [p["metrics"]["mfe_unconstrained"] for p in parents]
    vn = [p["metrics"]["vienna_mfe_unconstrained"] for p in parents]
    paired = [(a, b) for a, b in zip(lf, vn) if a is not None and b is not None]
    pearson = _pearson([a for a, _ in paired], [b for _, b in paired]) if paired else None
    gate1_go = bool(obedience_rate == 1.0 and nonneg_rate == 1.0)

    # Gate 2: Route-C viability per target (primary window W1).
    per_target: dict[str, dict] = {}
    for target in sorted({r["target_id"] for r in parents}):
        cells = []
        for p in [r for r in parents if r["target_id"] == target]:
            lam = float(p["lambda_value"])
            vs = [
                r for r in variants
                if r["target_id"] == target and float(r["lambda_value"]) == lam
                and r["metrics"].get("ddg_open_w1") is not None
            ]
            p_ddg = p["metrics"].get("ddg_open_w1")
            if p_ddg is None or not vs:
                cells.append({"lambda": lam, "n_variants": len(vs),
                              "improvement_w1": None})
                continue
            best = min(vs, key=lambda r: r["metrics"]["ddg_open_w1"])
            improvement = p_ddg - best["metrics"]["ddg_open_w1"]
            d_cai = (
                best["metrics"]["cds_cai"] - p["metrics"]["cds_cai"]
                if best["metrics"].get("cds_cai") is not None
                and p["metrics"].get("cds_cai") is not None
                else None
            )
            d_mfe_nt = (
                best["metrics"]["mfe_per_nt_unconstrained"]
                - p["metrics"]["mfe_per_nt_unconstrained"]
                if best["metrics"].get("mfe_per_nt_unconstrained") is not None
                and p["metrics"].get("mfe_per_nt_unconstrained") is not None
                else None
            )
            cells.append({
                "lambda": lam,
                "n_variants": len(vs),
                "parent_ddg_open_w1": p_ddg,
                "best_variant_index": best["variant_index"],
                "best_variant_ddg_open_w1": best["metrics"]["ddg_open_w1"],
                "improvement_w1": improvement,
                "best_variant_d_cai": d_cai,
                "best_variant_d_mfe_per_nt": d_mfe_nt,
            })
        med_imp = _median([c.get("improvement_w1") for c in cells])
        med_dcai = _median([c.get("best_variant_d_cai") for c in cells])
        med_dmfe = _median([
            abs(c["best_variant_d_mfe_per_nt"])
            if c.get("best_variant_d_mfe_per_nt") is not None else None
            for c in cells
        ])
        target_pass = bool(
            med_imp is not None and med_imp >= IMPROVEMENT_MIN
            and med_dcai is not None and med_dcai >= DCAI_MIN
            and med_dmfe is not None and med_dmfe <= DMFE_PER_NT_ABS_MAX
        )
        per_target[target] = {
            "cells": cells,
            "median_improvement_w1": med_imp,
            "median_best_variant_d_cai": med_dcai,
            "median_best_variant_abs_d_mfe_per_nt": med_dmfe,
            "pass": target_pass,
        }
    n_pass = sum(1 for t in per_target.values() if t["pass"])
    gate2_go = n_pass >= TARGETS_PASS_MIN

    # Lambda axis (descriptive): parent ddG + MFE/nt per lambda.
    lambda_axis: dict[str, dict] = {}
    for lam in sorted({float(p["lambda_value"]) for p in parents}):
        ps = [p for p in parents if float(p["lambda_value"]) == lam]
        lambda_axis[f"{lam:g}"] = {
            "parent_ddg_open_w1": [p["metrics"]["ddg_open_w1"] for p in ps],
            "parent_ddg_open_w2": [p["metrics"]["ddg_open_w2"] for p in ps],
            "parent_mfe_per_nt": [p["metrics"]["mfe_per_nt_unconstrained"] for p in ps],
            "parent_cai": [p["metrics"]["cds_cai"] for p in ps],
            "median_ddg_open_w1": _median([p["metrics"]["ddg_open_w1"] for p in ps]),
            "median_mfe_per_nt": _median(
                [p["metrics"]["mfe_per_nt_unconstrained"] for p in ps]
            ),
        }

    # Old-vs-new consistency: ddG_open by fragment-burial class.
    buried = [r["metrics"]["ddg_open_w1"] for r in ok
              if r["metrics"]["junction"]["j1_buried"]
              and r["metrics"]["ddg_open_w1"] is not None]
    unburied = [r["metrics"]["ddg_open_w1"] for r in ok
                if not r["metrics"]["junction"]["j1_buried"]
                and r["metrics"]["ddg_open_w1"] is not None]
    consistency = {
        "n_j1_buried": len(buried),
        "n_j1_unburied": len(unburied),
        "median_ddg_open_w1_buried": _median(buried),
        "median_ddg_open_w1_unburied": _median(unburied),
        "note": (
            "legacy metric = 40-nt fragment fold burial booleans; new metric = "
            "full-length constrained ddG. If the new metric is valid, buried "
            "candidates should show systematically higher ddG_open."
        ),
    }

    per_cell_s = [r.get("elapsed_seconds") for r in ok if r.get("elapsed_seconds")]
    return {
        "analysis": "junction ddG Phase 0 pilot (metric validity + Route C)",
        "date": time.strftime("%Y-%m-%d"),
        "preregistration": "junction_ddg_pilot_eval.py docstring (2026-08-05)",
        "matrix": {
            "targets": DEFAULT_TARGETS,
            "rep": REP,
            "lambdas": LAMBDAS,
            "shuffle": {
                "junction_end": "n_terminus",
                "codon_count": SHUFFLE_CODON_COUNT,
                "num_variants": SHUFFLE_NUM_VARIANTS,
                "species": CAI_SPECIES,
                "seed": SHUFFLE_SEED,
            },
        },
        "probe": probe,
        "gate1_metric_validity": {
            "constraint_obedience_rate": obedience_rate,
            "n_obedience_checks": n_obed,
            "ddg_nonneg_rate": nonneg_rate,
            "n_ddg_checks": n_ddg_checks,
            "linearfold_vs_vienna_parent_pearson_r": pearson,
            "n_parents_paired": len(paired),
            "go": gate1_go,
        },
        "gate2_route_c": {
            "thresholds": {
                "median_improvement_min_kcal_per_mol": IMPROVEMENT_MIN,
                "median_d_cai_min": DCAI_MIN,
                "median_abs_d_mfe_per_nt_max": DMFE_PER_NT_ABS_MAX,
                "targets_pass_min": TARGETS_PASS_MIN,
                "primary_window": "W1 (narrow, 15 nt AUG context)",
            },
            "per_target": per_target,
            "n_targets_pass": n_pass,
            "go": gate2_go,
        },
        "lambda_axis_descriptive": lambda_axis,
        "old_vs_new_consistency": consistency,
        "decision": "GO" if (gate1_go and gate2_go) else "NO-GO",
        "n_rows": len(rows),
        "n_success": len(ok),
        "n_parents": len(parents),
        "n_variants": len(variants),
        "runtime_seconds": round(runtime_s, 1),
        "mean_cell_seconds": round(sum(per_cell_s) / len(per_cell_s), 2) if per_cell_s else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--targets", default=",".join(DEFAULT_TARGETS))
    ap.add_argument("--lambdas", default=",".join(f"{l:g}" for l in LAMBDAS))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--output", default=str(RESULTS_DIR / "junction_ddg_pilot_runs.jsonl"))
    ap.add_argument("--summary", default=str(RESULTS_DIR / "junction_ddg_pilot_summary.json"))
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--probe-only", action="store_true",
                    help="run only the constraint correctness probe, then exit")
    args = ap.parse_args()

    targets = args.targets.split(",")
    lambdas = [float(x) for x in args.lambdas.split(",")]

    # Service pre-flight: direct service calls bypass workflow pre-flight, so
    # pull up all three microservices explicitly (P1/P2 pattern).
    from agent_core.services.service_manager import (
        CAPABILITY_SERVICE_MAP,
        ensure_services_ready,
    )

    ok, msgs = ensure_services_ready(
        [
            CAPABILITY_SERVICE_MAP["design_mrna_cds_with_lineardesign"],
            CAPABILITY_SERVICE_MAP["predict_rna_secondary_structure_with_linearfold"],
            CAPABILITY_SERVICE_MAP["predict_rna_secondary_structure"],
        ]
    )
    print(f"service preflight: ok={ok} {msgs}", flush=True)
    if not ok:
        return 1

    folder = PilotFolder(FOLD_URL, TMP_DIR)

    # Correctness probe BEFORE the matrix: if the constraint is not in effect
    # (window still pairs, or ddG < 0), stop here and debug — never hard-run.
    print("running constraint correctness probe (Insulin rep0 seed)...", flush=True)
    probe = constraint_probe(folder)
    print(f"probe: {json.dumps(probe)}", flush=True)
    if args.probe_only:
        return 0 if probe["pass"] else 1
    if not probe["pass"]:
        print("FATAL: constraint probe failed — constraint not in effect; aborting matrix", flush=True)
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    done = load_done_groups(output) if args.resume else set()
    jobs = [(t, l) for t in targets for l in lambdas]
    pending = [j for j in jobs if j not in done]
    print(f"matrix: {len(jobs)} groups, {len(done)} done, {len(pending)} pending", flush=True)

    lock = threading.Lock()
    rows_written = 0
    t_start = time.time()
    with output.open("a") as fh:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_group, t, l, folder): (t, l) for (t, l) in pending}
            for fut in as_completed(futures):
                t, l = futures[fut]
                group_rows = fut.result()
                with lock:
                    for row in group_rows:
                        fh.write(json.dumps(row) + "\n")
                        rows_written += 1
                    fh.flush()
                n_ok = sum(1 for r in group_rows if r.get("success"))
                print(
                    f"[group {t} lambda={l:g}] {n_ok}/{len(group_rows)} rows ok "
                    f"elapsed={group_rows[0].get('elapsed_seconds')}s",
                    flush=True,
                )

    all_rows = load_latest_rows(output)
    summary = build_summary(all_rows, probe, time.time() - t_start)
    Path(args.summary).write_text(json.dumps(summary, indent=1))
    print(f"decision: {summary['decision']} "
          f"gate1_go={summary['gate1_metric_validity']['go']} "
          f"gate2_go={summary['gate2_route_c']['go']} "
          f"targets_pass={summary['gate2_route_c']['n_targets_pass']}", flush=True)
    print(f"summary -> {args.summary}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
