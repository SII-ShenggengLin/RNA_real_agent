#!/usr/bin/env python3
"""Experiment 12 (paper §2.3 E1, Fig. 3d): EGARPS+ docking-power profile —
native-pose rank within seeded rigid-body decoy sets, 19 complexes / 14
independent protein targets.

PRE-REGISTRATION (reset campaign, 2026-08-27; protocol re-registered from the
retained E1 v2 Part-B evidence after the experiment-programme reset; anchor
panel extended to the v3 set per user approval the same day)
---------------------------------------------------------------------
* Question: does the deployed complex-scoring oracle (EGARPS+
  ``native_probability``) recognize the experimental native pose of an
  aptamer-protein complex among seeded rigid-body decoys?  This is the
  docking capability the platform's aptamer workflow implicitly relies on.
* Hypothesis (H1, direction pre-registered): the oracle shows no reliable
  docking power — native poses do not rank top-1 in ≥ 2/3 of the complexes
  (the pre-registered gate; analysis-side read-out only, nothing injected
  into the platform).  Wording discipline: conclusions are phrased as "no
  reliable docking power across the panel", never as an absolute claim.
* Anchor set: ``e1_anchor_set_v3.json`` ``docking_anchors`` verbatim —
  19 complexes over 14 independent protein targets (5 retained from v2 +
  14 admitted by the 2026-08-27 curation; Part-A entries untouched).
  Chemistry conventions (registered in the anchor set): DNA aptamers scored
  as RNA via residue renaming T->U (deoxyribose kept — no atoms added);
  sugar modifications (2'-OMe / 2'-F / FANA) mapped to parent bases via
  NUC_MAP with modification-specific atoms dropped (the 8EPK precedent);
  non-nucleotide ligands and waters stripped.
* Pose construction (per anchor): extract the registered protein chains +
  aptamer chain(s) from the deposited structure (single model, first
  altloc, no hydrogens), apply the chemistry mapping, write the NATIVE pose;
  decoys are rigid-body perturbations of the aptamer chain(s) about their
  joint centroid (protein fixed): rotation axis uniform on the sphere,
  angle θ ~ U(6°, 18°), translation direction uniform, magnitude
  d ~ U(1.5, 5) Å — seed 1000+i per decoy index (the retained convention's
  seed base).  Perturbation parameters CALIBRATED (2026-08-27, offline, no
  service calls) so the 1HVU decoy RMSD distribution matches the retained
  Part-B evidence (achieved mean 4.27, range 1.8–6.0 vs retained mean 3.67,
  range 2.44–5.81; the original driver was deleted in the reset, so the
  exact retained transform is unrecoverable — distribution-level match is
  the registered anchor; achieved RMSD is recorded per pose).  Achieved
  aptamer heavy-atom RMSD-to-native and the 4.5 Å
  heavy-atom contact count are recorded per pose.  Protocol anchor: the
  contact computation reproduces the retained evidence's 1HVU native
  n_contacts = 152 exactly (verified on the raw extraction;
  ``--verify-protocol`` asserts it before any service call).
* Instrument (zero-intervention rule): the platform's production tool path
  — ``ToolExecutor.run_tool`` through the ``ToolRegistry`` — against the
  deployed EGARPS+ microservice (port 8023) as shipped, ``academic=False``
  (platform default), no other arguments.  No threshold presets, no
  parameter sweeps, no retries (failures are recorded honestly).  Each pose
  scores in its own isolated scratch directory (EGARPS reuses a stale
  ``<basename>_fix.pdb`` — the pitfall register); pose basenames avoid the
  substrings 'protein'/'rna' (EGARPS feature-path typing hazard).
* CapGate policy: ``RNADA_CAPGATE=advisory`` — the documented regression
  convention (run_pa_test.py, exp1–exp11).  Under default enforce EGARPS is
  SelfModel-governed (graded failed from the retained evidence this
  experiment re-derives) and the calls would be blocked; advisory lets the
  profiling instrument reach the oracle while every call still lands in the
  platform audit trail (the driver activates the audit runtime via
  ``runtime_from_env()``).
* Metrics: per complex — n_poses_scored, native rank (ties broken against
  the native, tie count disclosed), native_np, median decoy np, native
  n_contacts, decoy RMSD range; primary read-out — fraction of complexes
  with native rank == 1 against the ≥ 2/3 gate; per-protein-target
  breakdown (4 thrombin families, 2 vWF families, 3 LDH complexes over 2
  species).  Secondary (recorded, informational, not gated): per-complex
  Spearman(np, −RMSD) across decoys (does the score track pose quality at
  all within a decoy set).
* Retained-evidence cross-check (informational, no tolerance gate): the two
  complexes with retained per-pose records (1HVU, 8EPK) are compared
  native-NP-vs-retained and rank-vs-retained; decoys are regenerated under
  the re-registered perturbation protocol so per-decoy scores are not
  expected to match; native-NP differences disclose service-side variance.
* Pilot: anchor ``tba_thrombin`` (4DII — DNA aptamer, exercises the full
  chemistry mapping) native + 2 decoys; pilot pass = 3/3 records with
  non-null native_probability.
* Budget: one pass over 19 anchors × 21 poses = 399 EGARPS calls
  (~50 s each, ≈ 5.5 h wall); ``--resume`` skips poses with a successful
  record on disk.  No arm comparison — per-pose compute is fixed.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp12_docking_capability.py --verify-protocol
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp12_docking_capability.py --pilot
    RNADA_CAPGATE=advisory PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp12_docking_capability.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp12_docking_capability.py --summary
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import shutil
import statistics
import time
from pathlib import Path

# regression convention BEFORE runtime_from_env() (see docstring)
os.environ.setdefault("RNADA_CAPGATE", "advisory")

HERE = Path(os.path.dirname(os.path.abspath(__file__))).resolve()
PROJECT_ROOT = HERE.parent
ANCHOR_JSON = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers"
    / "e1_anchor_set_v3.json"
)
STRUCT_DIR = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers"
    / "structures"
)
RESULTS_DIR = HERE / "results" / "exp12_docking_capability"
RECORDS_PATH = RESULTS_DIR / "poses.jsonl"
SUMMARY_PATH = RESULTS_DIR / "summary.json"
RETAINED_PART_B = HERE / "results" / "e1_docking_power_v2.jsonl"
RETAINED_SUMMARY = HERE / "results" / "e1_capability_summary_v2.json"

N_DECOYS = 20
DECOY_SEED_BASE = 1000
CONTACT_CUTOFF = 4.5
TOP1_GATE = 2.0 / 3.0
RMSD_SANITY = (0.8, 15.0)

# chemistry mapping (mirrors the v3 generator's NUC_MAP; applied at pose
# construction — parent scaffold kept, modification-specific atoms dropped)
NUC_MAP = {
    "A2M": "A", "OMC": "C", "OMG": "G", "OMU": "U",
    "CFZ": "C", "UFT": "U", "CFL": "C",
    "ATD": "U", "DT": "U", "DA": "A", "DC": "C", "DG": "G",
    "A": "A", "U": "U", "G": "G", "C": "C",
}
# standard heavy atoms per canonical RNA residue (phosphate set shared)
_SUGAR_PHOS = {"P", "OP1", "OP2", "O5'", "C5'", "C4'", "O4'", "C3'", "O2'",
               "C1'", "O3'"}
STD_ATOMS = {
    "A": _SUGAR_PHOS | {"N9", "C8", "N7", "C5", "C6", "N6", "N1", "C2", "N3", "C4"},
    "U": _SUGAR_PHOS | {"N1", "C2", "O2", "N3", "C4", "O4", "C5", "C6"},
    "G": _SUGAR_PHOS | {"N9", "C8", "N7", "C5", "C6", "O6", "N1", "C2", "N2",
                        "N3", "C4"},
    "C": _SUGAR_PHOS | {"N1", "C2", "O2", "N3", "C4", "N4", "C5", "C6"},
}
NON_NUCLEOTIDE_DROP = {
    "MG", "CA", "NA", "K", "GOL", "EPE", "SO4", "ZN", "MN", "HOH", "MPD",
    "EDO", "ACT", "PEG", "DMS", "IPA", "NO3", "PO4", "CL", "BR", "FMT",
    "MES", "TRS", "BME", "CO3", "OXY", "NAG", "BMA", "FLC", "ATP", "ACY",
}


# ── anchor handling ──────────────────────────────────────────────────────────

def load_anchors() -> list[dict]:
    data = json.loads(ANCHOR_JSON.read_text())
    anchors = data["docking_anchors"]
    assert len(anchors) == 19, f"expected 19 v3 docking anchors, got {len(anchors)}"
    return anchors


def anchor_chains(anchor: dict) -> tuple[list[str], list[str]]:
    prot = list(anchor["protein_chains"])
    apt = list(anchor.get("aptamer_chains") or [anchor["aptamer_chain"]])
    return prot, apt


def anchor_pose_id(anchor: dict, kind: str, idx: int | None) -> str:
    stem = anchor["aptamer_entry"]
    assert "protein" not in stem and "rna" not in stem, (
        f"pose basename {stem!r} trips the EGARPS typing hazard")
    return (f"{anchor['pdb_id'].lower()}_{stem}_native" if kind == "native"
            else f"{anchor['pdb_id'].lower()}_{stem}_decoy{idx:02d}")


# ── pose construction ────────────────────────────────────────────────────────

def build_native_pose(anchor: dict):
    """Return (gemmi structure of the mapped native pose, per-chain coords)."""
    import gemmi

    path = STRUCT_DIR / f"{anchor['pdb_id'].lower()}.pdb"
    src = gemmi.read_structure(str(path))
    assert len(src) == 1, f"{anchor['pdb_id']}: multi-model deposition"
    src.remove_alternative_conformations()
    src.remove_hydrogens()
    prot_chains, apt_chains = anchor_chains(anchor)

    pose = gemmi.Structure()
    pose.name = anchor_pose_id(anchor, "native", None)
    model = gemmi.Model("1")
    from gemmi import find_tabulated_residue

    for ch in src[0]:
        if ch.name not in prot_chains + apt_chains:
            continue
        out = gemmi.Chain(ch.name)
        for res in ch:
            rn = res.name
            if ch.name in apt_chains:
                if rn in NON_NUCLEOTIDE_DROP:
                    continue
                assert rn in NUC_MAP, (
                    f"{anchor['pdb_id']} chain {ch.name}: unregistered residue {rn}")
                new = gemmi.Residue()
                new.name = NUC_MAP[rn]
                new.seqid = res.seqid
                allowed = STD_ATOMS[new.name]
                for atom in res:
                    if atom.element == gemmi.Element("H"):
                        continue
                    if atom.name in allowed:
                        new.add_atom(atom)
                if len(new) > 0:
                    out.add_residue(new)
            else:
                if rn not in NON_NUCLEOTIDE_DROP and (
                    find_tabulated_residue(rn) is not None
                    and find_tabulated_residue(rn).is_amino_acid()
                ):
                    out.add_residue(res)
                # drop non-amino-acid ligands from protein chains
        if len(out) > 0:
            model.add_chain(out)
    pose.add_model(model)
    pose.setup_entities()
    return pose


def raw_native_contacts(anchor: dict) -> int:
    """4.5 A heavy-atom contact count on the RAW extraction (protocol anchor
    computation — identical to the computation that reproduces the retained
    1HVU native n_contacts = 152)."""
    import gemmi

    path = STRUCT_DIR / f"{anchor['pdb_id'].lower()}.pdb"
    st = gemmi.read_structure(str(path))
    st.remove_alternative_conformations()
    st.remove_hydrogens()
    prot_chains, apt_chains = anchor_chains(anchor)
    model = st[0]
    apt_atoms = [a for cn in apt_chains for r in model[cn] for a in r
                 if a.element != gemmi.Element("H")]
    ns = gemmi.NeighborSearch(st, 6.0).populate()
    pairs = set()
    for a in apt_atoms:
        for m in ns.find_atoms(a.pos, "\0", radius=CONTACT_CUTOFF):
            cra = m.to_cra(model)
            if cra.chain.name in prot_chains:
                pairs.add((a.serial, cra.atom.serial))
    return len(pairs)


def pose_contacts_and_rmsd(pose, prot_chains: list[str], apt_chains: list[str],
                           ref_apt_coords=None):
    """Contacts within the BUILT pose + optional aptamer RMSD vs reference."""
    import gemmi

    model = pose[0]
    ns = gemmi.NeighborSearch(pose, 6.0).populate()
    pairs = set()
    apt_atoms = [a for cn in apt_chains for r in model[cn] for a in r]
    for a in apt_atoms:
        for m in ns.find_atoms(a.pos, "\0", radius=CONTACT_CUTOFF):
            cra = m.to_cra(model)
            if cra.chain.name in prot_chains:
                pairs.add((a.serial, cra.atom.serial))
    rmsd = None
    if ref_apt_coords is not None:
        cur = []
        for cn in apt_chains:
            for r in model[cn]:
                for a in r:
                    cur.append((a.pos.x, a.pos.y, a.pos.z))
        assert len(cur) == len(ref_apt_coords), (
            "atom count changed under perturbation")
        rmsd = math.sqrt(sum(
            (c[0] - r[0]) ** 2 + (c[1] - r[1]) ** 2 + (c[2] - r[2]) ** 2
            for c, r in zip(cur, ref_apt_coords)) / len(cur))
    return len(pairs), rmsd


def aptamer_coords(pose, apt_chains: list[str]) -> list[tuple[float, float, float]]:
    return [(a.pos.x, a.pos.y, a.pos.z)
            for cn in apt_chains for r in pose[0][cn] for a in r]


def make_decoy(native_pose, anchor: dict, idx: int):
    """Seeded rigid-body perturbation of the aptamer chains (protein fixed)."""
    import gemmi

    rng = _SeededRNG(DECOY_SEED_BASE + idx)
    prot_chains, apt_chains = anchor_chains(anchor)
    pose = native_pose.clone()
    model = pose[0]

    coords = aptamer_coords(pose, apt_chains)
    n = len(coords)
    cx = sum(c[0] for c in coords) / n
    cy = sum(c[1] for c in coords) / n
    cz = sum(c[2] for c in coords) / n

    # uniform axis on sphere
    z = rng.uniform(-1.0, 1.0)
    phi = rng.uniform(0.0, 2.0 * math.pi)
    s = math.sqrt(max(0.0, 1.0 - z * z))
    theta = math.radians(rng.uniform(6.0, 18.0))
    # explicit axis-angle rotation matrix (row-major)
    x, y, zw = s * math.cos(phi), s * math.sin(phi), z
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    R = [
        [cos_t + x * x * (1 - cos_t), x * y * (1 - cos_t) - zw * sin_t,
         x * zw * (1 - cos_t) + y * sin_t],
        [y * x * (1 - cos_t) + zw * sin_t, cos_t + y * y * (1 - cos_t),
         y * zw * (1 - cos_t) - x * sin_t],
        [zw * x * (1 - cos_t) - y * sin_t, zw * y * (1 - cos_t) + x * sin_t,
         cos_t + zw * zw * (1 - cos_t)],
    ]
    # uniform translation direction, magnitude U(3, 10) A
    tz = rng.uniform(-1.0, 1.0)
    tphi = rng.uniform(0.0, 2.0 * math.pi)
    ts = math.sqrt(max(0.0, 1.0 - tz * tz))
    mag = rng.uniform(1.5, 5.0)
    tx, ty, tzw = ts * math.cos(tphi) * mag, ts * math.sin(tphi) * mag, tz * mag

    for cn in apt_chains:
        for res in model[cn]:
            for atom in res:
                px, py, pz = atom.pos.x - cx, atom.pos.y - cy, atom.pos.z - cz
                atom.pos = gemmi.Position(
                    R[0][0] * px + R[0][1] * py + R[0][2] * pz + cx + tx,
                    R[1][0] * px + R[1][1] * py + R[1][2] * pz + cy + ty,
                    R[2][0] * px + R[2][1] * py + R[2][2] * pz + cz + tzw,
                )
    pose.name = anchor_pose_id(anchor, "decoy", idx)
    return pose


class _SeededRNG:
    """Deterministic per-seed RNG (stdlib Mersenne Twister)."""

    def __init__(self, seed: int):
        import random
        self._r = random.Random(seed)

    def uniform(self, a: float, b: float) -> float:
        return self._r.uniform(a, b)


def write_pose(pose, out_path: Path) -> None:
    pose.setup_entities()
    pose.write_pdb(str(out_path))


# ── scoring chain (platform production path) ─────────────────────────────────

def build_executor():
    from agent_core.calibrated.runtime import runtime_from_env
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    runtime_from_env()
    return ToolExecutor(build_default_tool_registry())


def run_tool(executor, name: str, **kwargs) -> dict:
    res = executor.run_tool(name, **kwargs)
    if not res.success:
        raise RuntimeError(f"{name} failed: {res.error}")
    raw = res.artifacts.get("result")
    if not isinstance(raw, dict):
        raise RuntimeError(f"{name} returned no result dict")
    return raw


def score_pose(pose_path: Path, executor) -> float:
    rel = str(pose_path.relative_to(PROJECT_ROOT))
    eg = run_tool(executor, "score_rna_protein_complex_with_egarps",
                  filepath=rel, academic=False)
    np_val = eg.get("native_probability")
    if np_val is None:
        raise RuntimeError("EGARPS returned no native_probability")
    return float(np_val)


# ── driver ───────────────────────────────────────────────────────────────────

def iter_pose_specs(anchors: list[dict]):
    for anchor in anchors:
        yield anchor, "native", None
        for i in range(N_DECOYS):
            yield anchor, "decoy", i


def pose_dir(anchor: dict, kind: str, idx: int | None) -> Path:
    return RESULTS_DIR / "scratch" / anchor_pose_id(anchor, kind, idx)


def load_records() -> dict[str, dict]:
    done: dict[str, dict] = {}
    if RECORDS_PATH.exists():
        for line in RECORDS_PATH.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec.get("success"):
                    done[rec["pose_id"]] = rec
    return done


def cmd_verify_protocol() -> None:
    anchors = load_anchors()
    raw_counts = {}
    for anchor in anchors:
        pose = build_native_pose(anchor)
        prot, apt = anchor_chains(anchor)
        contacts, _ = pose_contacts_and_rmsd(pose, prot, apt)
        raw_counts[anchor["pdb_id"]] = raw_native_contacts(anchor)
        print(f"{anchor['pdb_id']:5s} {anchor['aptamer_entry']:<20s} "
              f"pose_contacts={contacts:<4d} raw_contacts={raw_counts[anchor['pdb_id']]:<4d} "
              f"apt_res={sum(len(pose[0][c]) for c in apt)} "
              f"prot_res={sum(len(pose[0][c]) for c in prot)}")
    anchor_152 = raw_counts.get("1HVU")
    assert anchor_152 == 152, (
        f"protocol anchor failed: 1HVU raw native contacts {anchor_152} != 152 "
        "(the retained evidence's value)")
    print("1HVU raw native contacts == 152 — protocol anchored to the "
          "retained Part-B computation.")


def cmd_pilot() -> None:
    anchors = [a for a in load_anchors() if a["aptamer_entry"] == "tba_thrombin"]
    assert len(anchors) == 1
    specs = [(anchors[0], "native", None),
             (anchors[0], "decoy", 0), (anchors[0], "decoy", 1)]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    executor = build_executor()
    ok = 0
    for anchor, kind, idx in specs:
        rec = run_one(anchor, kind, idx, executor)
        ok += int(rec["success"])
        print(json.dumps(rec, ensure_ascii=True))
    print(f"pilot: {ok}/3 successful")
    assert ok == 3, "pilot failed"


def cmd_run(resume: bool) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    executor = build_executor()
    done = load_records() if resume else {}
    if not resume and RECORDS_PATH.exists():
        RECORDS_PATH.unlink()
    total = failed = 0
    t0 = time.monotonic()
    with RECORDS_PATH.open("a", encoding="utf-8") as fh:
        for anchor, kind, idx in iter_pose_specs(load_anchors()):
            pid = anchor_pose_id(anchor, kind, idx)
            if pid in done:
                continue
            rec = run_one(anchor, kind, idx, executor)
            fh.write(json.dumps(rec, ensure_ascii=True) + "\n")
            fh.flush()
            total += 1
            failed += int(not rec["success"])
            if rec["success"]:
                print(f"[{total:3d}] {pid}: np={rec['egarps_native_probability']:.6g} "
                      f"({rec['elapsed_seconds']}s)", flush=True)
            else:
                print(f"[{total:3d}] {pid}: FAILED {rec['error']}", flush=True)
    wall = time.monotonic() - t0
    print(f"run: {total} scored, {failed} failures, wall {wall / 60:.1f} min")


def run_one(anchor: dict, kind: str, idx: int | None, executor) -> dict:
    started = time.monotonic()
    prot, apt = anchor_chains(anchor)
    native_pose = build_native_pose(anchor)
    ref = aptamer_coords(native_pose, apt)
    native_contacts_raw = raw_native_contacts(anchor)

    if kind == "native":
        pose = native_pose
        rmsd = 0.0
    else:
        pose = make_decoy(native_pose, anchor, idx)
    contacts, rmsd = pose_contacts_and_rmsd(
        pose, prot, apt, ref if kind == "decoy" else None)
    if kind == "decoy":
        assert RMSD_SANITY[0] <= rmsd <= RMSD_SANITY[1], (
            f"decoy RMSD {rmsd:.2f} outside sanity band {RMSD_SANITY}")

    pdir = pose_dir(anchor, kind, idx)
    if pdir.exists():
        shutil.rmtree(pdir)  # EGARPS stale <basename>_fix.pdb pitfall
    pdir.mkdir(parents=True)
    ppath = pdir / f"{anchor_pose_id(anchor, kind, idx)}.pdb"
    write_pose(pose, ppath)

    rec = {
        "pose_id": anchor_pose_id(anchor, kind, idx),
        "anchor": anchor["aptamer_entry"],
        "target": anchor["target"],
        "pdb_id": anchor["pdb_id"],
        "kind": kind,
        "decoy_seed": DECOY_SEED_BASE + idx if kind == "decoy" else None,
        "rmsd_to_native": round(rmsd, 3) if rmsd else None,
        "n_contacts": contacts,
        "n_contacts_native": native_contacts_raw,
        "success": False,
        "egarps_native_probability": None,
        "error": None,
        "elapsed_seconds": None,
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
    }
    try:
        np_val = score_pose(ppath, executor)
        rec["egarps_native_probability"] = np_val
        rec["success"] = True
    except Exception as exc:  # noqa: BLE001
        rec["error"] = str(exc)[:300]
    rec["elapsed_seconds"] = round(time.monotonic() - started, 1)
    return rec


def cmd_summary() -> None:
    records = [json.loads(l) for l in RECORDS_PATH.read_text().splitlines() if l.strip()]
    by_anchor: dict[str, list[dict]] = {}
    for rec in records:
        by_anchor.setdefault(rec["anchor"], []).append(rec)

    per_anchor = {}
    for anchor in load_anchors():
        key = anchor["aptamer_entry"]
        recs = by_anchor.get(key, [])
        if not recs:
            continue
        nat = next((r for r in recs if r["kind"] == "native" and r["success"]), None)
        decoys = sorted((r for r in recs if r["kind"] == "decoy" and r["success"]),
                        key=lambda r: r["pose_id"])
        if nat is None or not decoys:
            per_anchor[key] = {
                "target": anchor["target"], "pdb_id": anchor["pdb_id"],
                "n_poses_scored": len([r for r in recs if r["success"]]),
                "native_rank": None, "note": "native or decoys missing",
            }
            continue
        s_nat = nat["egarps_native_probability"]
        decoy_scores = [d["egarps_native_probability"] for d in decoys]
        greater = sum(1 for s in decoy_scores if s > s_nat)
        ties = sum(1 for s in decoy_scores if s == s_nat)
        rank = 1 + greater + ties  # ties broken against the native
        rmsds = [d["rmsd_to_native"] for d in decoys if d["rmsd_to_native"]]
        rho = None
        if len(set(decoy_scores)) > 2 and len(set(rmsds)) > 2:
            try:
                rho = _spearman([-r for r in rmsds], decoy_scores)
            except Exception:  # noqa: BLE001
                rho = None
        per_anchor[key] = {
            "target": anchor["target"],
            "pdb_id": anchor["pdb_id"],
            "n_poses_scored": 1 + len(decoys),
            "native_rank": rank,
            "native_np": s_nat,
            "median_decoy_np": statistics.median(decoy_scores),
            "native_n_contacts": nat["n_contacts_native"],
            "decoy_rmsd_range": [round(min(rmsds), 2), round(max(rmsds), 2)] if rmsds else None,
            "ties_against_native": ties,
            "top1": rank == 1,
            "spearman_np_vs_negrmsd_decoys": rho,
        }

    scored = {k: v for k, v in per_anchor.items() if v.get("native_rank")}
    n_complexes = len(scored)
    n_top1 = sum(1 for v in scored.values() if v["top1"])
    frac = n_top1 / n_complexes if n_complexes else 0.0

    per_target: dict[str, dict] = {}
    for key, v in scored.items():
        t = per_target.setdefault(v["target"], {"complexes": 0, "top1": 0})
        t["complexes"] += 1
        t["top1"] += int(v["top1"])

    retained = {}
    if RETAINED_SUMMARY.exists():
        rs = json.loads(RETAINED_SUMMARY.read_text()).get("part_b_docking", {})
        for key, v in scored.items():
            if key in rs:
                retained[key] = {
                    "retained_native_rank": rs[key]["native_rank"],
                    "retained_n_poses": rs[key]["n_poses_scored"],
                    "retained_native_np": rs[key]["native_np"],
                    "native_np_delta": v["native_np"] - rs[key]["native_np"],
                }

    summary = {
        "analysis": ("E12 docking-power profile (reset campaign, Fig. 3d) — "
                     "EGARPS+ native-pose rank within seeded rigid-body decoys, "
                     "19 complexes / 14 independent protein targets"),
        "date": dt.date.today().isoformat(),
        "anchor_set": str(ANCHOR_JSON.relative_to(PROJECT_ROOT)),
        "n_decoys_per_complex": N_DECOYS,
        "decoy_seed_base": DECOY_SEED_BASE,
        "contact_cutoff_A": CONTACT_CUTOFF,
        "gate_top1_fraction": TOP1_GATE,
        "n_records": len(records),
        "n_failures": sum(1 for r in records if not r["success"]),
        "n_complexes_scored": n_complexes,
        "n_top1": n_top1,
        "top1_fraction": round(frac, 4),
        "gate_pass": frac >= TOP1_GATE,
        "per_anchor": per_anchor,
        "per_target": per_target,
        "vs_retained": retained,
        "hypothesis_H1_supported": frac < TOP1_GATE,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("per_anchor", "per_target", "vs_retained")},
                     indent=1))
    print(f"wrote {SUMMARY_PATH}")


def _spearman(xs, ys) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verify-protocol", action="store_true")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.verify_protocol:
        cmd_verify_protocol()
    elif args.pilot:
        cmd_pilot()
    elif args.run:
        cmd_run(args.resume)
    elif args.summary:
        cmd_summary()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
