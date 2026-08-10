#!/usr/bin/env python3
"""Pilot P2 (2026-08-03): score the known-aptamer calibration set through the
RhoFold -> ProteinX -> EGARPS chain and evaluate ranking fidelity.

QUESTION
--------
Within a target, does the scoring chain rank higher-affinity aptamers higher
(Spearman rho between egarps native_probability and -log10 Kd), and does it
separate binders from non-binders (AUROC)? This calibrates the objective used
by the Fig-4 Type-II optimization claims (see curate_aptamer_calibration.py
docstring for motivation).

GO/NO-GO (pre-registered)
-------------------------
  GO: thrombin-series Spearman rho >= 0.6 AND pooled binder-vs-negative
      AUROC > 0.8 -> objective is rank-faithful; Fig-4 optimization claims
      stand as-is.
  NO-GO: rho < 0.6 or AUROC <= 0.8 -> add per-target calibration gating to
      the manuscript: optimization claims restricted to relative
      (same-target, same-campaign) comparisons, and the calibration result
      itself is reported as a method boundary finding.

NOTE: scoring uses the GPU services (RhoFold 8005 / ProteinX 8022 / EGARPS
8023); run AFTER the P0 budget-matched driver has released the GPUs. The
chain follows the EGARPS three-pitfalls discipline (RESUME_CHECKPOINT/HANDOFF
§5.1): real .pdb only for EGARPS, filename sanitised of "protein", pickle
cache never written back to inputs.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_aptamer_calibration.py [--resume]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT  # noqa: E402
from run_bmc_type2_ablation import find_structure  # noqa: E402
from run_known_aptamer_validation import (  # noqa: E402
    _proteinx_cif_to_pdb,
    _write_fasta,
    dna_to_rna,
    extract_protein_sequence,
)

ANCHOR_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers"
CALIBRATION_JSON = ANCHOR_DIR / "calibration_set.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "p2_aptamer_calibration.jsonl"


def load_done(output: Path) -> set[str]:
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
                done.add(r["id"])
    return done


def score_entry(entry: dict, timeout: int) -> dict:
    """Run one calibration entry through the scoring chain (direct calls)."""
    from agent_core.tools import (
        predict_rna_protein_complex_with_proteinx,
        predict_rna_tertiary_structure_with_rhofold,
        score_rna_protein_complex_with_egarps,
    )

    name = entry["id"]
    rna_seq = dna_to_rna(entry["sequence"])  # T->U convention (calibration_set doc)
    raw: dict = {"rhofold_mean_plddt": None, "proteinx_ipTM": None, "egarps_native_probability": None}
    steps: dict = {}

    # Protein fasta
    prot = entry["protein"]
    if prot["type"] == "benchmark_pdb":
        struct = find_structure(prot["pdb_id"])
        if struct is None:
            return {"success": False, "error": f"no structure for {prot['pdb_id']}"}
        protein_seq, protein_src = extract_protein_sequence(struct, prot.get("chain"))
    else:
        fa = ANCHOR_DIR / prot["fasta"]
        lines = fa.read_text().splitlines()
        protein_seq = "".join(l for l in lines if not l.startswith(">"))
        protein_src = f"uniprot:{prot['uniprot']}:{prot['range']}"
    if not protein_seq:
        return {"success": False, "error": "no protein sequence"}

    rna_fa = _write_fasta(f"p2cal_{name}", f"p2cal_{name}", rna_seq)
    protein_fa = _write_fasta(f"p2cal_{name}_target", f"p2cal_{name}_target", protein_seq)

    try:
        rh = predict_rna_tertiary_structure_with_rhofold.func(filepath=rna_fa)
        raw["rhofold_mean_plddt"] = rh.get("mean_plddt")
        rhofold_pdb = rh.get("pdb_filepath")
        steps["rhofold"] = "ok"
    except Exception as exc:  # noqa: BLE001
        steps["rhofold"] = f"failed: {exc}"
        return {"success": False, "error": steps["rhofold"], "steps": steps, "raw": raw, "protein_src": protein_src}

    try:
        px = predict_rna_protein_complex_with_proteinx.func(
            protein_filepath=protein_fa,
            rna_filepath=rna_fa,
            num_models=1,
            timeout_seconds=float(max(timeout, 600)),
        )
        raw["proteinx_ipTM"] = px.get("ipTM")
        proteinx_pdb = px.get("pdb_filepath") or None
        steps["proteinx_complex"] = "ok"
    except Exception as exc:  # noqa: BLE001
        steps["proteinx_complex"] = f"failed: {exc}"
        return {"success": False, "error": steps["proteinx_complex"], "steps": steps, "raw": raw, "protein_src": protein_src}

    egarps_input = None
    if proteinx_pdb:
        try:
            egarps_input = str(PROJECT_ROOT / _proteinx_cif_to_pdb(str(Path(proteinx_pdb).resolve()), f"p2cal_{name}"))
            steps["cif_to_pdb"] = "ok"
        except Exception as exc:  # noqa: BLE001
            steps["cif_to_pdb"] = f"failed: {exc}"

    if egarps_input:
        try:
            eg = score_rna_protein_complex_with_egarps.func(filepath=egarps_input, academic=False)
            raw["egarps_native_probability"] = eg.get("native_probability")
            steps["egarps"] = "ok"
        except Exception as exc:  # noqa: BLE001
            steps["egarps"] = f"failed: {exc}"

    ok = raw["egarps_native_probability"] is not None
    return {
        "success": ok,
        "error": None if ok else "egarps chain incomplete",
        "steps": steps,
        "raw": raw,
        "protein_src": protein_src,
        "artifacts": {"egarps_input_pdb": egarps_input},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    doc = json.loads(CALIBRATION_JSON.read_text())
    entries = doc["entries"]

    # Direct capability chain does NOT go through workflow pre-flight — pull
    # services up explicitly (RESUME_CHECKPOINT note 8).
    from agent_core.services.service_manager import (
        CAPABILITY_SERVICE_MAP,
        ensure_services_ready,
    )

    caps = [
        "predict_rna_tertiary_structure_with_rhofold",
        "predict_rna_protein_complex_with_proteinx",
        "score_rna_protein_complex_with_egarps",
    ]
    ok, msgs = ensure_services_ready([CAPABILITY_SERVICE_MAP[c] for c in caps], timeout=600)
    print(f"service preflight: ok={ok} {msgs}", flush=True)
    if not ok:
        return 1

    done = load_done(args.output) if args.resume else set()
    n_ok = n_fail = n_skip = 0
    for i, entry in enumerate(entries, 1):
        if entry["id"] in done:
            n_skip += 1
            continue
        print(f"[{i}/{len(entries)}] {entry['id']} (target={entry['target']}) ...", flush=True)
        t0 = time.perf_counter()
        try:
            res = score_entry(entry, timeout=args.timeout)
        except Exception as exc:  # noqa: BLE001
            res = {"success": False, "error": str(exc)}
        elapsed = time.perf_counter() - t0
        out = {
            "id": entry["id"],
            "target": entry["target"],
            "role": entry["role"],
            "kd_nm": entry.get("kd_nm"),
            "kd_assigned_nm_for_sensitivity": entry.get("kd_assigned_nm_for_sensitivity"),
            "length_nt": entry["length_nt"],
            "alphabet": entry["alphabet"],
            "confidence": entry.get("confidence", "high"),
            "success": res.get("success", False),
            "error": res.get("error"),
            "elapsed_seconds": round(elapsed, 1),
            **{k: res.get(k) for k in ("steps", "raw", "protein_src") if k in res},
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
        if out["success"]:
            n_ok += 1
        else:
            n_fail += 1
        eg = (out.get("raw") or {}).get("egarps_native_probability")
        print(f"      -> {'OK' if out['success'] else 'FAIL(' + str(out.get('error')) + ')'} "
              f"egarps={eg} in {elapsed:.0f}s", flush=True)

    print(f"\nDone: {n_ok} ok, {n_fail} failed, {n_skip} resumed-skip -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
