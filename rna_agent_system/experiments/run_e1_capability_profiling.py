#!/usr/bin/env python3
"""E1 (2026-08-04): oracle capability profiling pilot — CASF four capabilities
x 3 oracles x 3 targets, per REDESIGN_2026-08-03_CALIBRATED_AGENT.md §3 E1
(approved 2026-08-04). Zero LLM calls.

QUESTION
--------
What capabilities do the deployed structural oracles actually have for
RNA-protein aptamer design campaigns?
  Oracles: EGARPS native_probability, Protenix ipTM, RhoFold mean pLDDT.
  Targets: Thrombin / VEGF / PDGF-BB (anchor set:
  data/benchmarks/external_anchors/aptamers/e1_anchor_set.json, 29 entries).

PRE-REGISTERED HYPOTHESIS
-------------------------
All three oracles lack screening power (AUROC <= 0.8) and ranking power
(Spearman rho < 0.6) for RNA-protein aptamers; docking power of EGARPS is
tested here for the first time (no prior evidence either way).

DESIGN
------
  Part A (sequence level): score all 29 anchor entries through the
    RhoFold -> ProteinX -> EGARPS direct chain (identical semantics to
    run_aptamer_calibration.py; DNA scored as RNA via T->U).
      - ranking:   per oracle x target Spearman(oracle, -log10 Kd),
        binders with kd_nm (Thrombin n=6, VEGF n=8, PDGF-BB n=5).
      - screening: per oracle x target AUROC(binder vs negative)
        + bootstrap 95% CI (stats_utils).
      - scoring:   raw value distributions reported, no threshold.
  Part B (pose level, docking power, Thrombin ONLY — VEGF/PDGF-BB have no
  experimental aptamer complex, RCSB-verified 2026-08-04):
    anchors TBA->4DII, HD22-27mer->4I7Y, Toggle-25t->3DD2.
    Native pose = cleaned PDB (protein chains H/L + nucleic chain; 2'-F and
    DNA residues converted to standard RNA by residue renaming + modified-
    atom stripping; pdbfixer inside the EGARPS pipeline re-adds missing O2').
    20 decoys per anchor: rigid-body perturbation (rotation 2-15 deg,
    translation 1-6 A about the aptamer centroid), acceptance constraints
    (0 clashes < 2.2 A vs protein, interface contacts >= 50% of native,
    P-atom RMSD to native in [2, 12] A), fixed seeds (anchor_seed = 1000 +
    31*anchor_idx, decoy seed = anchor_seed + decoy_idx).
    Scoring = EGARPS only (ipTM/pLDDT are prediction-side confidences, not
    pose scorers — documented scope limit).
      - docking metric: per anchor, rank of the native pose's
        native_probability among the 21 poses; pass = native is top-1.

GO/NO-GO (pre-registered)
-------------------------
  Screening pass: any oracle-target AUROC > 0.8 (lower 95% CI bound reported
  alongside) -> that oracle-target combination UNLOCKS optimization claims
  (narrative: profiling unlocks). If none pass: "deployed oracles have no
  screening power for RNA-protein aptamers" stands as an empirical finding
  (expected direction, P2 already suggested it).
  Ranking pass: rho >= 0.6 (report rho only, n too small for p values).
  Docking pass: native top-1 in >= 2/3 anchors.
  Budget note: no arm comparison; per-entry compute is fixed by the anchor
  set (29 entries + 3 x 21 poses), budget-matching N/A.

E1 EXTENSION PRE-REGISTRATION (2026-08-04, W3-4 milestone; scope per
HANDOFF_2026-08-04_W12.md §4.1; rigor patches from the 2026-08-04 threshold-
robustness review)
------------------------------------------------------------------------------
SCOPE: extend the pilot (3 targets / 29 entries) to 6 confirmed targets,
  up to 9 if conditional curation passes. Confirmed new targets: HIV-1 RT,
  SARS-CoV-2 spike RBD, Angiopoietin-2. Conditional (included only if the
  curation script's assertions pass): Tenascin-C, Factor IXa, IL-17A.
  New docking anchors: 1HVU (HIV-1 RT, 4.75 A -- low resolution, registered
  caveat) and, conditionally, 8EPK (Factor IXa, 2.65 A).
HYPOTHESES (directions pre-registered, same as pilot):
  H1: no oracle shows RELIABLE screening power ACROSS TARGETS -- per-cell
      AUROC > 0.8 passes remain absent, or isolated with 95% CI covering
      chance (0.5). A single borderline cell with wide CI is NOT an unlock.
  H2: no oracle-target cell reaches Spearman rho >= 0.6 on ranking-eligible
      (within-assay comparable) binder subsets.
  H3: EGARPS docking power remains absent on the extended anchor set
      (native top-1 in < 2/3 of all anchors; per-target breakdown reported).
METRICS (new in extension, pre-registered):
  - Threshold sensitivity grid: pass/fail at AUROC in {0.6, 0.7, 0.8, 0.9}
    and rho in {0.4, 0.5, 0.6, 0.7} reported for EVERY cell. Headline
    criterion stays AUROC > 0.8 / rho >= 0.6; the grid preempts the
    "threshold set too high" critique by showing (in)sensitivity.
  - Enrichment factor: EF@top-3 (primary small-n enrichment metric) and
    EF@25% (secondary) = (binder fraction among the top-k oracle-ranked
    entries of a target) / (binder base rate of that target).
  - Ranking now restricted to curation-flagged ranking-eligible entries
    (within-assay Kd comparability, e.g. the Li-2008 subset for HIV-1 RT);
    screening unchanged (all binders vs negatives).
WORDING DISCIPLINE (registered): conclusions are phrased as "no oracle shows
  reliable screening/ranking power across targets", never as an absolute
  impossibility claim.
BUDGET: no arm comparison (per-entry compute fixed by anchor set); budget
  matching N/A, as in the pilot.
PILOT DATA: pilot Part A/B rows (29 entries / 3 anchors) are reused as-is
  (deterministic pipeline); the extension analysis merges pilot + extension
  jsonl by entry id. Pilot target entries are re-curated verbatim into the
  v2 anchor set (no sequence changes).

ENGINEERING DISCIPLINE (project pitfalls, RESUME_CHECKPOINT/HANDOFF §5)
-----------------------------------------------------------------------
  - EGARPS pitfalls 1-3: real .pdb only; pickle caches derived by
    `.pdb`-replace; basename must not contain 'protein'.
  - NEW pitfall (2026-08-04, discovered during E1 bring-up): the EGARPS
    pipeline SKIPS pdbfixer when `<basename>_fix.pdb` already exists, so
    re-scoring a MODIFIED pdb under the same basename silently reuses the
    stale fixed structure. EVERY pose is therefore scored in its OWN
    isolated directory with a unique basename.
  - GPU single worker: this driver is the only GPU job while it runs.
  - --resume is idempotent (per-entry / per-pose success keys).

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e1_capability_profiling.py \
        [--resume] [--skip-sequence] [--skip-docking] [--timeout 1800]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

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
E1_JSON = ANCHOR_DIR / "e1_anchor_set.json"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
POSES_DIR = RESULTS_DIR / "e1_poses"
DEFAULT_OUT_A = RESULTS_DIR / "e1_oracle_scoring.jsonl"
DEFAULT_OUT_B = RESULTS_DIR / "e1_docking_power.jsonl"

N_DECOYS = 20
ROT_DEG = (2.0, 15.0)
TRANS_A = (1.0, 6.0)
CLASH_CUT = 2.2
MIN_CONTACT_FRAC = 0.5
RMSD_RANGE = (2.0, 12.0)

# PDB residue handling for native pose cleanup (2'-F / DNA -> standard RNA)
PROT_RES = {"ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
            "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"}
NUC_MAP = {"A": "A", "G": "G", "C": "C", "U": "U", "CFL": "C", "UFT": "U",
           "DA": "A", "DG": "G", "DC": "C", "DT": "U", "DU": "U",
           # 8EPK (FIXa-DTRI-177): 2'-F / 2'-O-Me modified nucleotides -> standard RNA
           "A2M": "A", "ATD": "U", "CFZ": "C", "OMC": "C", "OMG": "G", "OMU": "U"}
DROP_ATOMS = {"F2'", "F2A", "C7", "C5M", "O2T", "H2'", "H2''", "H2A", "H2B",
              "CM'", "CM2"}  # CM'/CM2: 2'-O-Me methyl carbons (8EPK)


# ── Part A: sequence-level scoring (same semantics as P2) ───────────────────

def score_entry(entry: dict, timeout: int) -> dict:
    from agent_core.tools import (
        predict_rna_protein_complex_with_proteinx,
        predict_rna_tertiary_structure_with_rhofold,
        score_rna_protein_complex_with_egarps,
    )

    name = entry["id"]
    rna_seq = dna_to_rna(entry["sequence"])
    raw = {"rhofold_mean_plddt": None, "proteinx_ipTM": None, "egarps_native_probability": None}
    steps: dict = {}

    prot = entry["protein"]
    if prot["type"] == "benchmark_pdb":
        struct = find_structure(prot["pdb_id"])
        if struct is None:
            return {"success": False, "error": f"no structure for {prot['pdb_id']}"}
        protein_seq, protein_src = extract_protein_sequence(struct, prot.get("chain"))
    else:
        fa = ANCHOR_DIR / prot["fasta"]
        protein_seq = "".join(l for l in fa.read_text().splitlines() if not l.startswith(">"))
        protein_src = f"uniprot:{prot['uniprot']}:{prot['range']}"
    if not protein_seq:
        return {"success": False, "error": "no protein sequence"}

    rna_fa = _write_fasta(f"e1_{name}", f"e1_{name}", rna_seq)
    protein_fa = _write_fasta(f"e1_{name}_target", f"e1_{name}_target", protein_seq)

    try:
        rh = predict_rna_tertiary_structure_with_rhofold.func(filepath=rna_fa)
        raw["rhofold_mean_plddt"] = rh.get("mean_plddt")
        steps["rhofold"] = "ok"
    except Exception as exc:  # noqa: BLE001
        steps["rhofold"] = f"failed: {exc}"
        return {"success": False, "error": steps["rhofold"], "steps": steps, "raw": raw, "protein_src": protein_src}

    try:
        px = predict_rna_protein_complex_with_proteinx.func(
            protein_filepath=protein_fa, rna_filepath=rna_fa,
            num_models=1, timeout_seconds=float(max(timeout, 600)),
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
            egarps_input = str(PROJECT_ROOT / _proteinx_cif_to_pdb(str(Path(proteinx_pdb).resolve()), f"e1_{name}"))
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
    return {"success": ok, "error": None if ok else "egarps chain incomplete",
            "steps": steps, "raw": raw, "protein_src": protein_src}


# ── Part B: pose-level docking power ─────────────────────────────────────────

def clean_complex(pdb_path: Path, out_path: Path, protein_chains: set, nuc_chain: str) -> None:
    """Keep standard protein residues of protein_chains + nucleic chain renamed
    to 'R' with 2'-F/DNA residues converted to standard RNA."""
    import gemmi

    st = gemmi.read_structure(str(pdb_path))
    newst = gemmi.Structure()
    nm = gemmi.Model("0")
    for chain in st[0]:
        if chain.name in protein_chains:
            newc = gemmi.Chain(chain.name)
            for r in chain:
                if r.name in PROT_RES:
                    newc.add_residue(r)
            nm.add_chain(newc)
        elif chain.name == nuc_chain:
            newc = gemmi.Chain("R")
            for r in chain:
                if r.name not in NUC_MAP:
                    continue
                newr = gemmi.Residue()
                newr.name = NUC_MAP[r.name]
                newr.seqid = r.seqid
                newr.het_flag = "A"
                for a in r:
                    if a.name in DROP_ATOMS:
                        continue
                    newr.add_atom(a)
                newc.add_residue(newr)
            nm.add_chain(newc)
    newst.add_model(nm)
    newst.write_pdb(str(out_path))


def _coords(chain, only_p: bool) -> np.ndarray:
    return np.array([[a.pos.x, a.pos.y, a.pos.z] for r in chain for a in r
                     if (a.name == "P") == only_p or not only_p])


def _prot_coords(chains: dict) -> np.ndarray:
    return np.array([[a.pos.x, a.pos.y, a.pos.z]
                     for name, ch in chains.items() if name != "R" for r in ch for a in r])


def _rodrigues(axis: np.ndarray, deg: float) -> np.ndarray:
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    th = math.radians(deg)
    return np.eye(3) + math.sin(th) * k + (1 - math.cos(th)) * (k @ k)


def _n_contacts(x: np.ndarray, prot: np.ndarray, cut: float = 4.5) -> int:
    d = np.sqrt(((x[:, None, :] - prot[None, :, :]) ** 2).sum(-1))
    return int((d < cut).sum())


def make_decoy(native_pdb: Path, out_pdb: Path, seed: int, max_tries: int = 3000):
    """Rigid-body decoy under pre-registered acceptance constraints."""
    import gemmi

    rng = np.random.default_rng(seed)
    rpy = random.Random(seed)
    st = gemmi.read_structure(str(native_pdb))
    chains = {ch.name: ch for ch in st[0]}
    nuc = chains["R"]
    atoms = [a for r in nuc for a in r]
    orig = np.array([[a.pos.x, a.pos.y, a.pos.z] for a in atoms])
    p_mask = np.array([a.name == "P" for a in atoms])
    p0 = orig[p_mask]
    centroid = p0.mean(axis=0)
    prot = _prot_coords(chains)
    n_native = _n_contacts(orig, prot)
    for _ in range(max_tries):
        axis = rng.normal(size=3)
        axis /= np.linalg.norm(axis)
        rm = _rodrigues(axis, rpy.uniform(*ROT_DEG))
        t = rng.normal(size=3)
        t /= np.linalg.norm(t)
        t = t * rpy.uniform(*TRANS_A)
        moved = (orig - centroid) @ rm.T + centroid + t
        rmsd = float(np.sqrt(((moved[p_mask] - p0) ** 2).sum(1).mean()))
        d = np.sqrt(((moved[:, None, :] - prot[None, :, :]) ** 2).sum(-1))
        n_clash = int((d < CLASH_CUT).sum())
        n_cont = _n_contacts(moved, prot)
        if n_clash == 0 and n_cont >= MIN_CONTACT_FRAC * n_native and RMSD_RANGE[0] <= rmsd <= RMSD_RANGE[1]:
            for a, v in zip(atoms, moved):
                a.pos = gemmi.Position(*v)
            st.write_pdb(str(out_pdb))
            return {"rmsd_to_native": round(rmsd, 2), "n_contacts": n_cont, "n_contacts_native": n_native}
    return None


def score_pose(pdb_path: Path) -> dict:
    from agent_core.tools import score_rna_protein_complex_with_egarps

    try:
        res = score_rna_protein_complex_with_egarps.func(filepath=str(pdb_path), academic=False)
        return {"success": True, "egarps_native_probability": res.get("native_probability")}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)[:300]}


def run_docking(anchors: list, output: Path, resume_keys: set) -> None:
    for a_idx, anchor in enumerate(anchors):
        a_seed = 1000 + 31 * a_idx
        tag = f"{anchor['pdb_id'].lower()}_{anchor['aptamer_entry']}"
        for kind, d_idx in [("native", None)] + [("decoy", i) for i in range(N_DECOYS)]:
            pose_id = f"{tag}_{kind}" if kind == "native" else f"{tag}_decoy{d_idx:02d}"
            if pose_id in resume_keys:
                continue
            pose_dir = POSES_DIR / pose_id  # isolated dir per pose (stale-cache pitfall)
            if kind == "native" or not (pose_dir / f"{pose_id}.pdb").exists():
                if pose_dir.exists():
                    shutil.rmtree(pose_dir)
                pose_dir.mkdir(parents=True)
            pose_pdb = pose_dir / f"{pose_id}.pdb"
            meta = {}
            if kind == "native":
                clean_complex(
                    ANCHOR_DIR / "structures" / f"{anchor['pdb_id'].lower()}.pdb",
                    pose_pdb, set(anchor["protein_chains"]), anchor["aptamer_chain"],
                )
            else:
                native_pdb = POSES_DIR / f"{tag}_native" / f"{tag}_native.pdb"
                meta = make_decoy(native_pdb, pose_pdb, seed=a_seed + d_idx) or {}
                if not meta:
                    rec = {"pose_id": pose_id, "anchor": anchor["aptamer_entry"], "pdb_id": anchor["pdb_id"],
                           "kind": kind, "success": False, "error": "decoy generation exhausted max_tries",
                           "timestamp": datetime.now().isoformat(timespec="seconds")}
                    with output.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    print(f"  {pose_id}: DECOY-GEN FAIL", flush=True)
                    continue
            t0 = time.perf_counter()
            res = score_pose(pose_pdb.resolve())
            rec = {"pose_id": pose_id, "anchor": anchor["aptamer_entry"], "pdb_id": anchor["pdb_id"],
                   "kind": kind, "decoy_seed": (a_seed + d_idx) if kind == "decoy" else None,
                   **meta, **res, "elapsed_seconds": round(time.perf_counter() - t0, 1),
                   "timestamp": datetime.now().isoformat(timespec="seconds")}
            with output.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  {pose_id}: {'OK' if res['success'] else 'FAIL'} "
                  f"np={res.get('egarps_native_probability')} rmsd={meta.get('rmsd_to_native')}", flush=True)


# ── Driver ───────────────────────────────────────────────────────────────────

def load_done(output: Path, key: str) -> set:
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
                done.add(r[key])
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--skip-sequence", action="store_true")
    parser.add_argument("--skip-docking", action="store_true")
    parser.add_argument("--output-a", type=Path, default=DEFAULT_OUT_A)
    parser.add_argument("--output-b", type=Path, default=DEFAULT_OUT_B)
    parser.add_argument("--anchor-set", type=Path, default=E1_JSON,
                        help="anchor set JSON (default: pilot e1_anchor_set.json)")
    parser.add_argument("--targets", type=str, default=None,
                        help="comma-separated target filter (extension runs: score only the new targets)")
    args = parser.parse_args()

    doc = json.loads(args.anchor_set.read_text())
    entries = doc["entries"]
    anchors = doc["docking_anchors"]
    if args.targets:
        wanted = {t.strip() for t in args.targets.split(",")}
        entries = [e for e in entries if e["target"] in wanted]
        anchors = [a for a in anchors if a.get("target") in wanted]

    from agent_core.services.service_manager import CAPABILITY_SERVICE_MAP, ensure_services_ready

    caps = [
        "predict_rna_tertiary_structure_with_rhofold",
        "predict_rna_protein_complex_with_proteinx",
        "score_rna_protein_complex_with_egarps",
    ]
    ok, msgs = ensure_services_ready([CAPABILITY_SERVICE_MAP[c] for c in caps], timeout=600)
    print(f"service preflight: ok={ok} {msgs}", flush=True)
    if not ok:
        return 1

    if not args.skip_sequence:
        done = load_done(args.output_a, "id") if args.resume else set()
        n_ok = n_fail = n_skip = 0
        for i, entry in enumerate(entries, 1):
            if entry["id"] in done:
                n_skip += 1
                continue
            print(f"[A {i}/{len(entries)}] {entry['id']} (target={entry['target']}) ...", flush=True)
            t0 = time.perf_counter()
            try:
                res = score_entry(entry, timeout=args.timeout)
            except Exception as exc:  # noqa: BLE001
                res = {"success": False, "error": str(exc)}
            out = {
                "id": entry["id"], "target": entry["target"], "role": entry["role"],
                "kd_nm": entry.get("kd_nm"), "length_nt": entry["length_nt"], "alphabet": entry["alphabet"],
                "success": res.get("success", False), "error": res.get("error"),
                "elapsed_seconds": round(time.perf_counter() - t0, 1),
                **{k: res.get(k) for k in ("steps", "raw", "protein_src") if k in res},
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            with args.output_a.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
            n_ok += out["success"]
            n_fail += not out["success"]
            print(f"      -> {'OK' if out['success'] else 'FAIL'} raw={out.get('raw')}", flush=True)
        print(f"\nPart A done: {n_ok} ok, {n_fail} failed, {n_skip} resumed-skip -> {args.output_a}", flush=True)

    if not args.skip_docking:
        done_b = load_done(args.output_b, "pose_id") if args.resume else set()
        print(f"Part B: {len(anchors)} anchors x (1 native + {N_DECOYS} decoys), {len(done_b)} already done", flush=True)
        run_docking(anchors, args.output_b, done_b)
        print(f"Part B done -> {args.output_b}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
