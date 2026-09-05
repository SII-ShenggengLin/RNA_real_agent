#!/usr/bin/env python3
"""EXP 29 — 适配体战役弧重跑（§2.5 / Fig 5e–5g + Fig 6f 数据；fourth programme
reset, 2026-09-03, user-directed）.

Re-runs the aptamer-side GenNav campaign arc on the CURRENT production
platform, replacing the legacy E8→E15 registrations (drivers deleted with the
2026-08-18 simplification; evidence registers kept in DECISIONS Part 2) with
newly written code.  Four pre-registered segments, each a dual-arm
budget-matched campaign over the 20-target ``RNA-BioBench-Aptamer`` pool
(manifest order), cell = (target, profile):

  seg1_migration (初始迁移, E8 analog) — the mechanical-transfer regime:
    delivery-easy constraint matrix v0 (the v3 bands with relaxed windows,
    registered below), navigator = sparse 9-length lattice (25/30/34/40/47/
    55/61/70/80), probe 1 sample per length (seed 42), mechanized band-gap-
    first reinforcement only (seeds 7/99, n<=6), NO priors, NO guarantee
    rounds, cap 48.  20 targets x 3 profiles = 60 cells/arm.
    Pre-registered expectation: the static grid already suffices — both-pass
    saturation, no demonstrable advantage (the honest scope finding).

  seg2_reanchor (重锚定, E12 analog) — the production scarce matrix v3
    (``AptamerNavConfig`` verbatim: compact 25-34 GC[.42,.62] homo<5 stem<=7 /
    standard 40-55 GC[.40,.65] homo<5 stem<=9 / extended 61-80 GC[.35,.60]
    homo<6 stem<=12), navigator = densified 17-length production lattice +
    S1-measured priors (the target's seg1 pool re-scored under v3 — measured
    at zero extra generation budget), mechanized reinforcement only (the
    guarantee lever is deliberately NOT active yet).  60 cells/arm.
    Pre-registered expectation: static-arm failures rise materially
    (>= 2x seg1's fail fraction on the pilot) and discordance grows; the
    endpoint may stay one-cell short (legacy 9:2, P = 0.065) — reported as
    measured.

  seg3_decisive (决定性, E14 analog, PRIMARY ENDPOINT) — panel D = the 12
    targets with the FEWEST static-arm delivered cells in seg2 (most
    delivery-scarce first; ties broken by manifest order) — the pre-
    registered panel rule fixing the navigator's hypothesized advantage
    regime.  Navigation arm = the shipped production mode VERBATIM
    (``RnaAptamerDesignWorkflow._generate_aptamer_navigation``: matrix v3,
    17-length lattice, probe seed 42, cycling guaranteed-repair allocation +
    mechanized fill, cap 48).  12 x 3 = 36 cells/arm.
    GO rule (pre-registered): exact McNemar p < 0.05 AND b > c (navigation-
    only : rule-only discordant cells).

  seg4_confirmation (确认, E15 analog) — panel C = the 8 complement targets
    (least scarce under the same rule); same production dual-arm protocol.
    24 cells/arm.  Pre-registered expectation: the advantage attenuates on
    the delivery-abundant regime — the aptamer scarcity boundary (Fig 6f
    data).  Pooled seg3+seg4 McNemar reported alongside.

STATIC GRID ARM (all segments, target-independent, non-adaptive): gears
(length, seed, n) = (30,42,8) (30,123,8) (47,42,8) (47,123,8) (70,42,8)
(70,123,8) — band-centre lengths (compact centre 30 = the workflow's default
``aptamer_length``; standard 47; extended 70), the workflow's default static
seeds and sample count, EXACTLY 48 raw per target.  Both arms are evaluated
by the SHARED delivery rule (platform ``deliver_profile``: matrix-pass filter
-> fixed utility order -> D1 greedy top-5, diversity floor 0.15).

CELL PASS = non-degraded delivery (5/5 post-D1) under the segment matrix;
target e2e = all 3 profiles delivered.  Budget ledger: static exactly 48,
navigation <= 48 (production cap), violations asserted 0.  Zero LLM calls
(deterministic both arms; recorded for the Fig 4h companion).

INSTRUMENT: production tool path only — one fresh ``RnaAptamerDesignWorkflow``
per cell with ``auto_start_services`` (hotspots resolved once per target via
``_prepare_target_module``, the deterministic local SASA/DBSCAN tool, then
passed explicitly), generation through the workflow's audited wrappers
(``_build_odesign_json`` / ``_run_odesign_inference`` /
``_extract_sequences_from_predictions`` — every call lands in the CapGate
audit trail), folds via ToolExecutor ``predict_rna_secondary_structure_-
with_linearfold``, allocation/delivery via the platform pure core in
``agent_core/generation/gennav_aptamer.py``.  The downstream oracle evaluate
chain (RhoFold/EGARPS/ProteinX) is NOT part of any aptamer-campaign endpoint
and is not invoked.

DATASET: ``RNA-BioBench-Aptamer`` (schema 1.1.0, unmodified since creation —
verified against git; the same on-disk files behind the re-run Figs 3a-e/h
and 4a-c).  GPU: odesign_service pinned to GPU 0 by
``experiments/exp1_bring_up_services.sh`` (2026-09-03 machine note) — run the
bring-up before the campaign.

CACHES (deterministic-services, md5-keyed, merged across workers):
odesign_<md5(protein|chain|len|hotspot|L|seed|n)> -> sequences,
fold_<md5(seq)> -> (structure, mfe), hotspots.json.  ``--verify``
recomputes every stored evaluation primitive (matrix_pass from stored
seq/gc/stem, ``deliver_profile`` over stored pools, cell outcomes, exact +
permutation McNemar, verdicts) byte-identically — no regeneration.

PILOT (2 targets: Thrombin, GFP; all four segments) calibration gates:
(a) seg1 v0 both-pass saturation >= 75% of cells with at least one delivered
    candidate (else adjust v0 BEFORE the full run — disclosed as pilot
    calibration);
(b) seg2 static-arm fail fraction >= 2x seg1's (re-anchoring effective);
(c) budget violations 0 everywhere; (d) production nav trace well-formed.

OUTPUTS: ``results/exp29_aptamer_campaign_arc/{pilot,seg1_migration,
seg2_reanchor,seg3_decisive,seg4_confirmation}/`` (runs.jsonl + verdict.json
each), ``panels.json`` (the registered selection rule applied), ``arc.json``
(the four-segment ladder summary), ``caches/``.

Budget sweep (pre-registered 2026-09-04, user-approved narrative): both
arms re-run on the FROZEN panel D at caps 24 and 32 (48 already measured)
under identical rules — static grid = equal split floor(cap/3) samples per
band at the same three band-centre lengths (seed 42, one seed — 48-cap
equivalent: 16/16/16), navigation = the shipped v3b mode with
navigation_raw_budget=cap.  Endpoint: delivered cells per arm at each cap
(the cost-delivery curve; the 48-cap point is the frozen arc).

Usage:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp29_aptamer_campaign_arc.py sweep [--workers 8]
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp29_aptamer_campaign_arc.py pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp29_aptamer_campaign_arc.py phaseA [--resume] [--workers 4]
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp29_aptamer_campaign_arc.py phaseB [--resume] [--workers 4]
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp29_aptamer_campaign_arc.py panels
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp29_aptamer_campaign_arc.py verify [seg1_migration|seg2_reanchor|seg3_decisive|seg4_confirmation|all]
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp29_aptamer_campaign_arc"
TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "targets"
STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
CACHES_DIR = RESULTS_DIR / "caches"

SEG1_DIR = "seg1_migration"
SEG2_DIR = "seg2_reanchor"
SEG3_DIR = "seg3_decisive"
SEG4_DIR = "seg4_confirmation"

RAW_CAP = 48                      # the E14 iron rule, both arms
STATIC_GEARS: tuple[tuple[int, int, int], ...] = (
    (30, 42, 8), (30, 123, 8),
    (47, 42, 8), (47, 123, 8),
    (70, 42, 8), (70, 123, 8),
)
SPARSE_LATTICE: tuple[int, ...] = (25, 30, 34, 40, 47, 55, 61, 70, 80)

PILOT_TARGETS = ["Thrombin", "GFP"]

# matrix v0 (seg1 initial, pre-re-anchoring) — v3 bands, relaxed windows
MATRIX_V0 = {
    "compact": {"lo": 25, "hi": 34, "gc_lo": 0.35, "gc_hi": 0.70,
                "homo": 6, "stem": 12},
    "standard": {"lo": 40, "hi": 55, "gc_lo": 0.35, "gc_hi": 0.70,
                 "homo": 6, "stem": 15},
    "extended": {"lo": 61, "hi": 80, "gc_lo": 0.30, "gc_hi": 0.70,
                 "homo": 7, "stem": 20},
}
PROFILE_ORDER = ("compact", "standard", "extended")

SEGMENT_LEVERS = {
    SEG1_DIR: "initial matrix v0; sparse lattice; mechanized reinforcement",
    SEG2_DIR: "re-anchored matrix v3; densified lattice; S1 priors",
    SEG3_DIR: "+ guaranteed-repair allocation (production mode verbatim)",
    SEG4_DIR: "confirmation on the scarcity complement (production mode)",
    "sweep_cap16": "budget sweep, cap 16 (static equal split 5/5/5)",
    "sweep_cap20": "budget sweep, cap 20 (static equal split 6/6/6)",
    "sweep_cap24": "budget sweep, cap 24 (static equal split 8/8/8)",
    "sweep_cap32": "budget sweep, cap 32 (static equal split 10/10/10)",
    "sweep_cap48": "budget sweep, cap 48 (the registered cap, 16/16/16)",
    "expanded_cap16": "expanded-pool cap 16",
    "expanded_cap20": "expanded-pool cap 20",
    "expanded_cap24": "expanded-pool cap 24",
    "expanded_cap32": "expanded-pool cap 32",
    "expanded_cap48": "expanded-pool cap 48",
}


def log_line(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ─────────────────────────── dataset helpers ───────────────────────────

EXPANDED_TARGETS_DIR = (PROJECT_ROOT / "data" / "benchmarks"
                        / "RNA-BioBench-Aptamer-Expanded" / "targets")


def load_targets(pool: str = "base") -> list[dict[str, Any]]:
    tdir = TARGETS_DIR if pool == "base" else EXPANDED_TARGETS_DIR
    if pool == "expanded":
        targets = load_targets("base")
    else:
        targets = []
    manifest = json.loads(
        (tdir.parent / "dataset_manifest.json").read_text(encoding="utf-8"))
    for tid in manifest["targets"]:
        meta = json.loads((tdir / f"{tid}.json").read_text(encoding="utf-8"))
        meta["_target_id"] = tid
        targets.append(meta)
    return targets


def resolve_structure(meta: dict[str, Any]) -> Optional[Path]:
    """Base pool: benchmark structures by pdb_id; expanded pool: the
    registered per-target structure_path (complex-derived, protein chains
    retained)."""
    sp = meta.get("structure_path")
    if sp:
        path = Path(sp)
        return path if path.is_file() else None
    return find_structure(meta["pdb_id"]) if meta.get("pdb_id") else None


def find_structure(pdb_id: str) -> Optional[Path]:
    for pattern in (f"{pdb_id.lower()}*.pdb", f"{pdb_id.upper()}*.pdb",
                    f"*{pdb_id.lower()}*", f"*{pdb_id}*"):
        for cand in STRUCT_DIR.glob(pattern):
            return cand
    return None


# ─────────────────────────── caches ───────────────────────────

class Caches:
    """Deterministic-service caches (odesign requests, folds, hotspots).

    md5-keyed; the fold cache stores LinearFold (structure, mfe); the odesign
    cache stores extracted sequences per (protein, gear) request.
    """

    def __init__(self, cache_dir: Path):
        self.dir = cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._odesign = self._load("odesign_cache.json")
        self._folds = self._load("fold_cache.json")
        self._hotspots = self._load("hotspots.json")
        self._dirty = False

    def _load(self, name: str) -> dict[str, Any]:
        path = self.dir / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def flush(self) -> None:
        if not self._dirty:
            return
        with self._lock:
            for name, data in (("odesign_cache.json", self._odesign),
                               ("fold_cache.json", self._folds),
                               ("hotspots.json", self._hotspots)):
                (self.dir / name).write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self._dirty = False

    # keys
    @staticmethod
    def odesign_key(protein_md5: str, chain: str, seq_len: int, hotspot: str,
                    length: int, seed: int, n: int) -> str:
        raw = f"{protein_md5}|{chain}|{seq_len}|{hotspot}|L{length}|s{seed}|n{n}"
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def fold_key(seq: str) -> str:
        return hashlib.md5(seq.upper().encode()).hexdigest()

    def odesign_get(self, key: str) -> Optional[list[str]]:
        return self._odesign.get(key)

    def odesign_put(self, key: str, sequences: list[str]) -> None:
        with self._lock:
            self._odesign[key] = sequences
            self._dirty = True
        self.flush()

    def fold_get(self, key: str) -> Optional[list[Any]]:
        return self._folds.get(key)

    def fold_put(self, key: str, struct_mfe: list) -> None:
        with self._lock:
            self._folds[key] = struct_mfe
            self._dirty = True
        self.flush()

    def seed_from(self, root: "Caches") -> None:
        """Adopt the shared root cache's entries (worker start-up)."""
        for mine, shared in ((self._odesign, root._odesign),
                             (self._folds, root._folds),
                             (self._hotspots, root._hotspots)):
            for k, v in shared.items():
                mine.setdefault(k, v)
        self._dirty = True

    def merge_into(self, root: "Caches") -> None:
        """Fold this cache back into the shared root (coordinator, single-
        threaded after workers exit)."""
        for mine, shared in ((self._odesign, root._odesign),
                             (self._folds, root._folds),
                             (self._hotspots, root._hotspots)):
            shared.update(mine)
        root._dirty = True

    def hotspot(self, target_id: str) -> Optional[str]:
        return self._hotspots.get(target_id)

    def set_hotspot(self, target_id: str, hotspot: str) -> None:
        self._hotspots[target_id] = hotspot
        self._dirty = True


# ─────────────────────── audited instrument ───────────────────────

_STEER_URLS: list[str] = []
_STEER_COUNTER: Optional["itertools.count"] = None


def steer_odesign_endpoints() -> list[str]:
    """Round-robin ``run_odesign_inference`` service_url across the replica
    fleet when EXP29_ODESIGN_URLS is set (the exp16 endpoint-steering
    convention; explicit non-default service_url always passes through).
    Replicas are identical deterministic services — a request's output
    depends only on its inputs, not the replica that served it.  Each
    process starts at a pid-offset position so the fleet spreads across
    GPUs from the first request instead of piling onto the first URLs."""
    global _STEER_URLS, _STEER_COUNTER
    urls = [u.strip() for u in
            os.environ.get("EXP29_ODESIGN_URLS", "").split(",") if u.strip()]
    if not urls or _STEER_COUNTER is not None:
        return urls
    _STEER_URLS = urls
    _STEER_COUNTER = itertools.count(start=os.getpid())

    from agent_core import tools as T
    tool = T.run_odesign_inference
    orig_default = tool.args_schema.model_fields["service_url"].default
    orig_func = tool.func

    def wrapper(*a, **kw):
        if kw.get("service_url", orig_default) != orig_default:
            return orig_func(*a, **kw)
        url = _STEER_URLS[next(_STEER_COUNTER) % len(_STEER_URLS)]
        return orig_func(*a, **dict(kw, service_url=url))

    tool.func = wrapper
    return urls


class Instrument:
    """Per-thread production workflow instances; generation via the
    workflow's audited ODesign wrappers, folds via ToolExecutor LinearFold,
    all allocation/delivery via the platform pure core.  One 90-s backoff
    retry per tool call (transient-service handling, deterministic services
    return the identical result — the exp28 convention)."""

    def __init__(self, caches: Caches):
        self.caches = caches
        self._protein_md5: dict[str, str] = {}
        self._local = threading.local()
        from agent_core.calibrated.runtime import runtime_from_env
        runtime_from_env()
        steer_odesign_endpoints()

    def _workflow(self):
        wf = getattr(self._local, "wf", None)
        if wf is None:
            from agent_core.capabilities.base import build_default_capability_registry
            from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
            from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignWorkflow
            executor = ToolExecutor(build_default_tool_registry())
            registry = build_default_capability_registry(executor)
            wf = RnaAptamerDesignWorkflow(registry)
            wf.auto_start_services = True
            self._local.wf = wf
        return wf

    def protein_md5(self, protein_path: str) -> str:
        if protein_path not in self._protein_md5:
            self._protein_md5[protein_path] = hashlib.md5(
                Path(protein_path).read_bytes()).hexdigest()
        return self._protein_md5[protein_path]

    def resolve_cell_context(self, meta: dict[str, Any],
                             struct: Optional[Path]) -> dict[str, Any]:
        """Target prep through the production module (hotspot cached per
        target — the deterministic local SASA/DBSCAN tool).  Sequence-only
        targets (expanded pool fasta entries) enter with protein_sequence
        and the workflow's production ProteinX path predicts the structure —
        ONCE per target: the predicted structure path is cached and reused
        as protein_structure_path on every later cap (the fold is ~10 min
        on large proteins and must not repeat per budget arm)."""
        wf = self._workflow()
        from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput
        tid = meta["_target_id"]
        hotspot = self.caches.hotspot(tid)
        params: dict[str, Any] = {"chain_id": meta.get("pdb_chain") or "A"}
        if struct is not None:
            params["protein_structure_path"] = str(struct)
        elif meta.get("protein_sequence"):
            cached_fold = self.caches._hotspots.get(f"proteinx::{tid}")
            if cached_fold and Path(cached_fold).is_file():
                params["protein_structure_path"] = cached_fold
            else:
                params["protein_sequence"] = meta["protein_sequence"]
        if hotspot:
            params["hotspot_residues"] = hotspot
        wf._workflow_state = {}
        wf._workflow_trace = []
        protein_path, resolved_hotspot, seq_len = wf._prepare_target_module(
            RnaAptamerDesignInput(**params))
        if (struct is None and meta.get("protein_sequence")
                and protein_path and Path(protein_path).is_file()):
            with self.caches._lock:
                self.caches._hotspots[f"proteinx::{tid}"] = protein_path
                self.caches._dirty = True
            self.caches.flush()
        if hotspot is None and resolved_hotspot:
            self.caches.set_hotspot(tid, resolved_hotspot)
            self.caches.flush()
        return {
            "protein_path": protein_path,
            "hotspot": resolved_hotspot,
            "seq_len": seq_len,
            "chain_id": meta.get("pdb_chain") or "A",
        }

    def fold(self, seq: str) -> tuple[Optional[str], Optional[float]]:
        key = Caches.fold_key(seq)
        hit = self.caches.fold_get(key)
        if hit is not None:
            return (hit[0], hit[1])
        from agent_core.file_manager import save_sequence
        wf = self._workflow()
        filepath = save_sequence(seq, prefix="exp29_fold")
        res = wf._invoke_and_record(
            "predict_rna_secondary_structure_with_linearfold",
            {"filepath": filepath},
            step_name="predict_rna_secondary_structure_with_linearfold",
        )
        from agent_core.sequence_utils import _pick_float
        if res.success:
            value = (res.output.get("structure"), _pick_float(res.output, "mfe"))
        else:
            value = (None, None)
        self.caches.fold_put(key, [value[0], value[1]])
        return value

    def odesign(self, ctx: dict[str, Any], length: int, seed: int, n: int,
                log=log_line) -> list[str]:
        """One ODesign gear request through the production audited wrappers,
        cached by request key (deterministic seeds -> identical output).
        Transient service failures (GPU-OOM 500s under concurrent model
        loads) back off 90 s and retry once — deterministic services return
        the identical result, and only a twice-failed request returns empty
        (uncached, budget spent, recorded as measured)."""
        key = Caches.odesign_key(
            self.protein_md5(ctx["protein_path"]), ctx["chain_id"],
            ctx["seq_len"], ctx["hotspot"], length, seed, n)
        hit = self.caches.odesign_get(key)
        if hit is not None:
            return list(hit)
        wf = self._workflow()
        sequences: list[str] = []
        for attempt in (1, 2):
            try:
                json_result = wf._build_odesign_json(
                    protein_path=ctx["protein_path"],
                    chain_id=ctx["chain_id"],
                    seq_len=ctx["seq_len"],
                    hotspot=ctx["hotspot"],
                    aptamer_length=length,
                )
                if json_result:
                    result = wf._run_odesign_inference(
                        json_path=json_result.get("input_json_filepath", ""),
                        n_sample=n,
                        seeds=[seed],
                    )
                    if result:
                        for path in result.get("prediction_filepaths", []):
                            seqs = wf._extract_sequences_from_predictions([path])
                            if seqs:
                                sequences.extend(seqs)
                        break
                failed = "capability_result_failed"
            except Exception as exc:  # noqa: BLE001
                failed = repr(exc)
            if attempt == 1:
                log(f"[odesign] transient failure L{length} s{seed} n{n} "
                    f"({failed}); retrying in 90 s")
                time.sleep(90.0)
            else:
                log(f"[odesign] FAILED after retry L{length} s{seed} n=n{n} "
                    f"({failed}); budget spent, recorded as measured")
                return []
        sequences = [s for s in sequences if s]
        self.caches.odesign_put(key, sequences)
        return sequences

    def production_navigation(self, meta: dict[str, Any],
                              struct: Optional[Path],
                              *, raw_budget: Optional[int] = None
                              ) -> dict[str, Any]:
        """The shipped production navigation mode VERBATIM (seg3/seg4 arm C):
        ``_generate_aptamer_navigation`` — the exact method ``run(navigation=
        True)`` calls; the downstream oracle evaluate chain is not a campaign
        endpoint and is not invoked."""
        wf = self._workflow()
        from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput
        wf._workflow_state = {}
        wf._workflow_trace = []
        ctx = self.resolve_cell_context(meta, struct)
        if not ctx["protein_path"] or not ctx["hotspot"]:
            return {"success": False, "errors": ["target_preparation_failed"],
                    "trace": {}}
        input_kwargs: dict[str, Any] = {
            "chain_id": meta.get("pdb_chain") or "A",
            "hotspot_residues": ctx["hotspot"],
            "navigation": True,
        }
        if struct is not None:
            input_kwargs["protein_structure_path"] = str(struct)
        elif meta.get("protein_sequence"):
            input_kwargs["protein_sequence"] = meta["protein_sequence"]
        if raw_budget is not None:
            input_kwargs["navigation_raw_budget"] = int(raw_budget)
        inp = RnaAptamerDesignInput(**input_kwargs)
        # mirror run(): the capability layer reads param overrides from
        # state["_aptamer_input"]
        wf._workflow_state = {"_aptamer_input": inp}
        wf._workflow_trace = []
        t0 = time.perf_counter()
        try:
            wf._generate_aptamer_navigation(
                ctx["protein_path"], ctx["hotspot"], inp,
                protein_seq_len=ctx["seq_len"])
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "errors": [repr(exc)], "trace": {}}
        trace = wf._workflow_state.get("_gennav_trace") or {}
        return {
            "success": True,
            "errors": [],
            "elapsed_seconds": time.perf_counter() - t0,
            "trace": json.loads(json.dumps(trace, default=str)),
        }


# ─────────────────── platform-core era navigators (seg1/seg2) ───────────────────

def _make_config(matrix: dict[str, dict], lattice: tuple[int, ...]):
    from agent_core.generation.gennav_aptamer import AptamerNavConfig
    return AptamerNavConfig(
        profiles=json.loads(json.dumps(matrix)),
        profile_order=PROFILE_ORDER,
        lattice_lengths=lattice,
    )


def _fetch_gears_parallel(inst: Instrument, ctx: dict[str, Any],
                          gears: list[tuple[int, int, int]],
                          log=log_line) -> dict[tuple[int, int, int], list[str]]:
    """Concurrent ODesign fetch over independent gears; fixed-order
    deterministic integration happens in the caller (results keyed by gear).
    Cached gears return instantly from the request cache.  The pool width is
    EXP29_FETCH_POOL (default 2) — each ODesign subprocess pays a fixed
    ~90-s featurization load and the load phase degrades superlinearly
    beyond ~8 in-flight requests machine-wide (measured on the pilot)."""
    width = max(1, int(os.environ.get("EXP29_FETCH_POOL", "2")))
    if len(gears) <= 1:
        return {g: inst.odesign(ctx, g[0], g[1], g[2], log=log) for g in gears}
    out: dict[tuple[int, int, int], list[str]] = {}
    with ThreadPoolExecutor(max_workers=min(width, len(gears))) as pool:
        futs = {pool.submit(inst.odesign, ctx, g[0], g[1], g[2], log): g
                for g in gears}
        for fut, g in futs.items():
            out[g] = fut.result()
    return out


def era_navigation(inst: Instrument, ctx: dict[str, Any], config, *,
                   prior: Optional[list[dict]] = None,
                   log=log_line) -> dict[str, Any]:
    """The seg1/seg2 navigator: production pure core (concurrent probe ->
    mechanized-only reinforcement) under an era config.  Identical to the
    production loop minus the guarantee lever (the E12-era form); the probe
    fetches run concurrently and integrate in fixed lattice order."""
    from agent_core.generation.gennav_aptamer import (
        evaluate_matrix, gc_fraction, longest_stem_bp, mechanized_proposals,
        profile_gaps,
    )
    pool: list[dict] = []
    gears: list[dict] = []
    seen: set[str] = set()
    raw_spent = 0
    rounds: list[dict] = []

    def _add(sequences: list[str], length: int, seed: int, n_req: int) -> None:
        nonlocal raw_spent
        raw_spent += n_req
        gears.append({"aptamer_length": length, "seed": seed, "n_samples": n_req})
        for idx, seq in enumerate(sequences):
            if not seq or seq in seen:
                continue
            seen.add(seq)
            structure, mfe = inst.fold(seq)
            gc = gc_fraction(seq)
            stem = longest_stem_bp(structure) if structure else 0
            pool.append({
                "id": f"nav:L{length}:s{seed}:i{idx}",
                "sequence": seq,
                "gear": {"aptamer_length": length, "seed": seed,
                         "n_samples": n_req},
                "gc": round(gc, 4),
                "longest_stem_bp": stem,
                "mfe": mfe,
                "matrix_pass": evaluate_matrix(seq, gc, stem, config),
            })

    probe_budget = min(len(config.lattice_lengths),
                       config.raw_budget_per_target)
    probe_lengths = list(config.lattice_lengths)[:probe_budget]
    fetched = _fetch_gears_parallel(
        inst, ctx,
        [(L, config.probe_seed, 1) for L in probe_lengths], log=log)
    for length in probe_lengths:                 # phase 1: probe (fixed order)
        _add(fetched[(length, config.probe_seed, 1)], length,
             config.probe_seed, 1)
    while raw_spent < config.raw_budget_per_target:  # phase 2: mechanized fill
        gaps = profile_gaps(pool, config)
        if all(g == 0 for g in gaps.values()):
            break
        proposals, _ = mechanized_proposals(
            pool, gears, raw_spent, config, prior=prior)
        if not proposals:
            break
        gear = proposals[0]
        n = min(int(gear["n_samples"]), config.raw_budget_per_target - raw_spent)
        if n <= 0:
            break
        rounds.append({"kind": "mechanized", "length": gear["length"],
                       "seed": gear["seed"], "n_samples": n,
                       "gaps_before": gaps})
        seqs = inst.odesign(ctx, gear["length"], gear["seed"], n, log=log)
        _add(seqs, gear["length"], gear["seed"], n)
    return {"pool": pool, "gears": gears, "raw_spent": raw_spent,
            "rounds": rounds, "final_gaps": profile_gaps(pool, config)}


def static_grid(inst: Instrument, ctx: dict[str, Any], config,
                log=log_line) -> dict[str, Any]:
    """The static-grid arm: the six pre-registered fixed gears (exactly 48
    raw, fetched concurrently — they are mutually independent), evaluated
    under the segment's matrix by the shared rule."""
    from agent_core.generation.gennav_aptamer import (
        evaluate_matrix, gc_fraction, longest_stem_bp,
    )
    gear_list = list(STATIC_GEARS)
    fetched = _fetch_gears_parallel(inst, ctx, gear_list, log=log)
    pool: list[dict] = []
    gears: list[dict] = []
    seen: set[str] = set()
    raw_spent = 0
    for length, seed, n in gear_list:            # fixed-order integration
        raw_spent += n
        gears.append({"aptamer_length": length, "seed": seed, "n_samples": n})
        for idx, seq in enumerate(fetched[(length, seed, n)]):
            if not seq or seq in seen:
                continue
            seen.add(seq)
            structure, mfe = inst.fold(seq)
            gc = gc_fraction(seq)
            stem = longest_stem_bp(structure) if structure else 0
            pool.append({
                "id": f"grid:L{length}:s{seed}:i{idx}",
                "sequence": seq,
                "gear": {"aptamer_length": length, "seed": seed, "n_samples": n},
                "gc": round(gc, 4),
                "longest_stem_bp": stem,
                "mfe": mfe,
                "matrix_pass": evaluate_matrix(seq, gc, stem, config),
            })
    return {"pool": pool, "gears": gears, "raw_spent": raw_spent}


# ─────────────────────────── cell assembly ───────────────────────────

def _deliveries(pool: list[dict], config) -> dict[str, dict]:
    from agent_core.generation.gennav_aptamer import deliver_profile
    return {p: deliver_profile(pool, p, config) for p in config.profile_order}


def _pool_snapshot(pool: list[dict]) -> list[dict]:
    return [{
        "id": c["id"], "sequence": c["sequence"],
        "gear": c["gear"], "gc": c["gc"],
        "longest_stem_bp": c["longest_stem_bp"], "mfe": c["mfe"],
        "matrix_pass": c["matrix_pass"],
    } for c in pool]


def _cells_pass(deliveries: dict[str, dict]) -> dict[str, bool]:
    return {p: (not d.get("degraded", True)) for p, d in deliveries.items()}


def _e2e(cells: dict[str, bool]) -> bool:
    return all(cells.get(p, False) for p in PROFILE_ORDER)


def _arm_record(kind: str, run: dict[str, Any], deliveries: dict[str, dict],
                *, pool: Optional[list[dict]] = None,
                extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    spent = run.get("raw_spent") or 0
    rec: dict[str, Any] = {
        "kind": kind,
        "raw_budget": RAW_CAP,
        "raw_spent": run.get("raw_spent"),
        "budget_violation": int(spent > RAW_CAP),
        "rounds": run.get("rounds", []),
        "pool_size": len(run.get("pool", [])) if "pool" in run else None,
        "final_gaps": run.get("final_gaps"),
        "deliveries": deliveries,
        "cells_pass": _cells_pass(deliveries),
        "e2e": _e2e(_cells_pass(deliveries)),
    }
    if pool is not None:
        rec["pool"] = _pool_snapshot(pool)
    if extra:
        rec.update(extra)
    return rec


def run_cell(segment: str, meta: dict[str, Any], inst: Instrument,
             prior_pool: Optional[list[dict]] = None,
             log=log_line) -> dict[str, Any]:
    """One (segment, target) cell: both arms, budget ledger, shared rule."""
    tid = meta["_target_id"]
    struct = resolve_structure(meta)
    t0 = time.perf_counter()
    if struct is None and not meta.get("protein_sequence"):
        return {"segment": segment, "target_id": tid, "success": False,
                "error": f"no structure for {meta.get('pdb_id')}",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ctx = inst.resolve_cell_context(meta, struct)
    if not ctx["protein_path"] or not ctx["hotspot"]:
        return {"segment": segment, "target_id": tid, "success": False,
                "error": "target_preparation_failed",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}

    if segment == SEG1_DIR:
        config = _make_config(MATRIX_V0, SPARSE_LATTICE)
        prior = None
        nav_kind = "nav_migration"
    elif segment == SEG2_DIR:
        config = _make_config(_MATRIX_V3(), _DENSE_LATTICE())
        prior = prior_pool
        nav_kind = "nav_reanchor"
    elif segment in (SEG3_DIR, SEG4_DIR):
        config = _make_config(_MATRIX_V3(), _DENSE_LATTICE())
        prior = None
        nav_kind = "nav_production"
    else:
        raise ValueError(segment)

    # ── arm A: static grid ──
    log(f"[{segment}:{tid}] arm A static grid (48 raw) ...")
    grid = static_grid(inst, ctx, config, log=log)
    assert grid["raw_spent"] == RAW_CAP, grid["raw_spent"]
    deliveries_a = _deliveries(grid["pool"], config)
    arm_a = _arm_record("static_grid", grid, deliveries_a, pool=grid["pool"])

    # ── arm C: navigation ──
    if nav_kind == "nav_production":
        log(f"[{segment}:{tid}] arm C production navigation ...")
        nav = inst.production_navigation(meta, struct)
        trace = nav["trace"]
        deliveries_c = dict(trace.get("deliveries") or {})
        if not deliveries_c:
            run_c = {"raw_spent": 0, "rounds": [], "final_gaps": None,
                     "pool": []}
        else:
            run_c = {"raw_spent": trace.get("raw_spent"),
                     "rounds": trace.get("rounds"),
                     "final_gaps": trace.get("final_gaps")}
        arm_c = _arm_record(
            "nav_production", run_c, deliveries_c,
            extra={"navigation_success": nav["success"],
                   "navigation_errors": nav["errors"],
                   "nav_elapsed_seconds": nav.get("elapsed_seconds"),
                   "trace_protocol": trace.get("protocol"),
                   "probe": trace.get("probe")})
    else:
        log(f"[{segment}:{tid}] arm C {nav_kind} ...")
        nav = era_navigation(inst, ctx, config, prior=prior, log=log)
        deliveries_c = _deliveries(nav["pool"], config)
        arm_c = _arm_record(nav_kind, nav, deliveries_c, pool=nav["pool"])
        if prior is not None:
            arm_c["prior_pool_size"] = len(prior)

    rec = {
        "segment": segment,
        "target_id": tid,
        "pdb_id": meta.get("pdb_id"),
        "protein_length_aa": meta.get("protein_length_aa"),
        "matrix": "v0" if segment == SEG1_DIR else "v3",
        "success": True,
        "arms": {"A": arm_a, "C": arm_c},
        "llm_calls": 0,
        "elapsed_seconds": round(time.perf_counter() - t0, 1),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    ca, cc = arm_a["cells_pass"], arm_c["cells_pass"]
    log(f"[{segment}:{tid}] done in {rec['elapsed_seconds']:.0f}s — "
        f"cells A={sum(ca.values())}/3 C={sum(cc.values())}/3 "
        f"(nav raw {arm_c['raw_spent']}/48)")
    return rec


def _MATRIX_V3() -> dict[str, dict]:
    from agent_core.generation.gennav_aptamer import AptamerNavConfig
    return json.loads(json.dumps(AptamerNavConfig().profiles))


def _DENSE_LATTICE() -> tuple[int, ...]:
    from agent_core.generation.gennav_aptamer import AptamerNavConfig
    return AptamerNavConfig().lattice_lengths


def _prior_from_seg1(seg1_rec: dict[str, Any]) -> list[dict]:
    """S1 prior: the target's seg1 pool (nav + static) re-scored under v3."""
    from agent_core.generation.gennav_aptamer import (
        evaluate_matrix, gc_fraction,
    )
    config = _make_config(_MATRIX_V3(), _DENSE_LATTICE())
    prior: list[dict] = []
    for arm in ("C", "A"):
        for cand in (seg1_rec["arms"][arm].get("pool") or []):
            seq = cand["sequence"]
            gc = gc_fraction(seq)
            stem = cand.get("longest_stem_bp") or 0
            prior.append({
                "gear": {"aptamer_length": cand["gear"]["aptamer_length"]},
                "matrix_pass": evaluate_matrix(seq, gc, stem, config),
            })
    return prior


# ─────────────────────────── statistics ───────────────────────────

def exact_mcnemar(b: int, c: int) -> float:
    """Two-sided exact binomial McNemar p over discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    return min(1.0, 2.0 * tail)


def permutation_null(b: int, c: int, draws: int = 10_000,
                     seed: int = 0) -> float:
    """Sign-flip permutation null on |b - c| (exp28 convention, 1e4/seed 0)."""
    n = b + c
    if n == 0:
        return 1.0
    rng = random.Random(seed)
    obs = abs(b - c)
    hits = 0
    for _ in range(draws):
        s = sum(1 for _ in range(n) if rng.random() < 0.5)
        if abs(2 * s - n) >= obs:
            hits += 1
    return hits / draws


def segment_verdict(records: list[dict[str, Any]], segment: str,
                    missing: Optional[list[str]] = None) -> dict[str, Any]:
    """Paired cell outcomes -> exact + permutation McNemar, arm counts."""
    b = c = 0
    cells = {"both": 0, "nav": 0, "rule": 0, "none": 0}
    delivered = {"A": 0, "C": 0}
    e2e = {"A": 0, "C": 0}
    n_cells = 0
    per_target: dict[str, dict[str, Any]] = {}
    for rec in records:
        if not rec.get("success"):
            continue
        ca = rec["arms"]["A"]["cells_pass"]
        cc = rec["arms"]["C"]["cells_pass"]
        for prof in PROFILE_ORDER:
            a_pass, c_pass = ca.get(prof, False), cc.get(prof, False)
            n_cells += 1
            delivered["A"] += int(a_pass)
            delivered["C"] += int(c_pass)
            if c_pass and a_pass:
                cells["both"] += 1
            elif c_pass:
                cells["nav"] += 1
                b += 1
            elif a_pass:
                cells["rule"] += 1
                c += 1
            else:
                cells["none"] += 1
        e2e["A"] += int(rec["arms"]["A"]["e2e"])
        e2e["C"] += int(rec["arms"]["C"]["e2e"])
        per_target[rec["target_id"]] = {
            "A": sum(ca.values()), "C": sum(cc.values()),
            "e2e_A": rec["arms"]["A"]["e2e"], "e2e_C": rec["arms"]["C"]["e2e"],
        }
    verdict = {
        "segment": segment,
        "lever": SEGMENT_LEVERS[segment],
        "n_targets": len(per_target),
        "n_cells": n_cells,
        "mcnemar": {
            "b_nav_only": b, "c_rule_only": c, "n_discordant": b + c,
            "p_exact": exact_mcnemar(b, c),
            "p_permutation_1e4": permutation_null(b, c),
        },
        "delivered_cells": delivered,
        "delivered_fraction": {k: (round(v / n_cells, 4) if n_cells else None)
                               for k, v in delivered.items()},
        "pair_outcomes": cells,
        "e2e_targets": e2e,
        "budget": {
            "static_raw_spend": RAW_CAP,
            "nav_raw_spent_max": max(
                (r["arms"]["C"]["raw_spent"] or 0)
                for r in records if r.get("success")),
            "nav_raw_spent_mean": round(sum(
                (r["arms"]["C"]["raw_spent"] or 0)
                for r in records if r.get("success")) / max(1, len(
                    [r for r in records if r.get("success")])), 2),
            "violations": sum(
                (r["arms"]["C"].get("budget_violation") or 0) +
                (r["arms"]["A"].get("budget_violation") or 0)
                for r in records if r.get("success")),
        },
        "llm_calls": 0,
        "per_target": per_target,
        "targets_missing_boundary": missing or [],
    }
    if segment == SEG3_DIR:
        verdict["go_rule"] = {
            "rule": "exact McNemar p < 0.05 AND b > c (navigation-only > rule-only)",
            "p_exact": verdict["mcnemar"]["p_exact"],
            "b": b, "c": c,
            "verdict": "GO" if (verdict["mcnemar"]["p_exact"] < 0.05 and b > c)
                       else "NO-GO",
        }
    return verdict


# ─────────────────────────── panel selection ───────────────────────────

def select_panels() -> dict[str, Any]:
    """The pre-registered decisive-panel rule over seg2's static-arm
    delivered cells (fewest first; ties by manifest order)."""
    seg2_dir = RESULTS_DIR / SEG2_DIR
    records = [json.loads(ln) for ln in
               (seg2_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()
               if ln.strip()]
    records = [r for r in records if r.get("success")]
    manifest = [t["_target_id"] for t in load_targets()]
    scored = []
    for rec in records:
        cells_a = sum(rec["arms"]["A"]["cells_pass"].values())
        cells_c = sum(rec["arms"]["C"]["cells_pass"].values())
        scored.append({"target_id": rec["target_id"],
                       "static_cells_seg2": cells_a,
                       "nav_cells_seg2": cells_c})
    by_id = {s["target_id"]: s for s in scored}
    ranked = sorted(scored, key=lambda s: (s["static_cells_seg2"],
                                           manifest.index(s["target_id"])))
    panel_d = [s["target_id"] for s in ranked[:12]]
    panel_c = [s["target_id"] for s in ranked[12:]]
    doc = {
        "rule": ("rank by static-arm delivered cells under v3 in seg2 "
                 "(ascending, most delivery-scarce first; ties by dataset "
                 "manifest order); panel D = first 12 (decisive), "
                 "panel C = complement 8 (confirmation)"),
        "seg2_static_cells": by_id,
        "panel_D_decisive": panel_d,
        "panel_C_confirmation": panel_c,
        "selected_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (RESULTS_DIR / "panels.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log_line(f"[panels] D={panel_d}")
    log_line(f"[panels] C={panel_c}")
    return doc


# ─────────────────────────── stage running ───────────────────────────

def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in
            path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _seg1_record(seg1_records: dict[str, dict], tid: str) -> Optional[dict]:
    rec = seg1_records.get(tid)
    return rec if rec and rec.get("success") else None


def run_stage(segment: str, targets_meta: list[dict[str, Any]], *,
              resume: bool, workers: int = 1, worker_id: Optional[int] = None,
              stage_root: Optional[Path] = None) -> int:
    stage_dir = (stage_root or RESULTS_DIR) / segment
    stage_dir.mkdir(parents=True, exist_ok=True)
    manifest_ids = [m["_target_id"] for m in targets_meta]

    if worker_id is not None:
        out = stage_dir / f"runs_worker{worker_id}.jsonl"
        caches = Caches(CACHES_DIR / f"worker{worker_id}")
        root_caches = Caches(CACHES_DIR)
        caches.seed_from(root_caches)
        inst = Instrument(caches)
        seg1_records: dict[str, dict] = {}
        if segment == SEG2_DIR:
            seg1_path = (stage_root or RESULTS_DIR) / SEG1_DIR / "runs.jsonl"
            for r in load_records(seg1_path):
                if r.get("success"):
                    seg1_records[r["target_id"]] = r
        done = {(r.get("segment"), r.get("target_id"))
                for r in load_records(out)}
        for meta in targets_meta:
            tid = meta["_target_id"]
            if (segment, tid) in done:
                continue
            prior = None
            if segment == SEG2_DIR:
                base = _seg1_record(seg1_records, tid)
                if base is not None:
                    prior = _prior_from_seg1(base)
            try:
                rec = run_cell(segment, meta, inst, prior_pool=prior)
            except Exception as exc:  # noqa: BLE001
                log_line(f"[{segment}:w{worker_id}:{tid}] FAILURE: {exc!r}")
                rec = {"segment": segment, "target_id": tid, "success": False,
                       "error": repr(exc),
                       "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        caches.flush()
        return 0

    if workers > 1:
        done: set[str] = set()
        for path in [stage_dir / "runs.jsonl"] + \
                sorted(stage_dir.glob("runs_worker*.jsonl")):
            done |= {r["target_id"] for r in load_records(path)
                     if r.get("success")}
        remaining = [m for m in targets_meta if m["_target_id"] not in done]
        # LPT-ish partition by protein length (odesign cost proxy)
        chunks: list[list[dict]] = [[] for _ in range(workers)]
        loads = [0.0] * workers
        for m in sorted(remaining,
                        key=lambda x: -(x.get("protein_length_aa") or 100)):
            k = min(range(workers), key=lambda i: loads[i])
            chunks[k].append(m)
            loads[k] += (m.get("protein_length_aa") or 100) ** 2
        log_line(f"[{segment}] parallel launch: {len(done)} done, "
                 f"{len(remaining)} remaining across {workers} workers "
                 f"{[len(c) for c in chunks]}")
        procs = []
        for k, chunk in enumerate(chunks):
            if not chunk:
                continue
            lf = (stage_dir / f"worker{k}.log").open("w", encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).resolve()),
                   "--stage", segment, "--targets",
                   ",".join(m["_target_id"] for m in chunk),
                   "--worker-id", str(k), "--resume",
                   "--stage-root", str(stage_root or RESULTS_DIR)]
            procs.append((k, subprocess.Popen(
                cmd,
                env={**os.environ,
                     "PYTHONPATH": f"{PROJECT_ROOT}:{os.environ.get('PYTHONPATH', '')}"},
                stdout=lf, stderr=subprocess.STDOUT), lf))
        for k, proc, lf in procs:
            rc = proc.wait()
            lf.close()
            log_line(f"[{segment}] worker{k} exit={rc}")
        # fold worker caches back into the shared root (single-threaded here)
        root_caches = Caches(CACHES_DIR)
        for wc in sorted(CACHES_DIR.glob("worker*")):
            if wc.is_dir():
                Caches(wc).merge_into(root_caches)
        root_caches.flush()
        return finalize_stage(segment, manifest_ids, stage_dir=stage_dir)

    out = stage_dir / "runs.jsonl"
    done = {r["target_id"] for r in load_records(out)
            if r.get("success")} if resume else set()
    if done and not resume:
        out.write_text("")
        done = set()
    caches = Caches(CACHES_DIR)
    inst = Instrument(caches)
    seg1_records = {}
    if segment == SEG2_DIR:
        for r in load_records((stage_root or RESULTS_DIR) / SEG1_DIR / "runs.jsonl"):
            if r.get("success"):
                seg1_records[r["target_id"]] = r
    failures = 0
    for meta in targets_meta:
        tid = meta["_target_id"]
        if tid in done:
            continue
        prior = None
        if segment == SEG2_DIR:
            base = _seg1_record(seg1_records, tid)
            if base is not None:
                prior = _prior_from_seg1(base)
        try:
            rec = run_cell(segment, meta, inst, prior_pool=prior)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            log_line(f"[{segment}:{tid}] FAILURE: {exc!r}")
            rec = {"segment": segment, "target_id": tid, "success": False,
                   "error": repr(exc),
                   "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    caches.flush()
    return finalize_stage(segment, manifest_ids, stage_dir=stage_dir)


def finalize_stage(segment: str, manifest_ids: list[str], *,
                   stage_dir: Optional[Path] = None) -> int:
    stage_dir = stage_dir or RESULTS_DIR / segment
    merged: dict[str, dict] = {}
    for path in [stage_dir / "runs.jsonl"] + \
            sorted(stage_dir.glob("runs_worker*.jsonl")):
        for r in load_records(path):
            if r.get("success") and r["target_id"] not in merged:
                merged[r["target_id"]] = r
    ordered = [merged[t] for t in manifest_ids if t in merged]
    with (stage_dir / "runs.jsonl").open("w", encoding="utf-8") as fh:
        for r in ordered:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    for wk in sorted(stage_dir.glob("runs_worker*.jsonl")):
        wk.unlink()
    log_line(f"[{segment}] merged {len(ordered)}/{len(manifest_ids)} records")
    if not ordered:
        return 1
    missing = [t for t in manifest_ids if t not in merged]
    if missing:
        # measured boundary (e.g. the registered ODesign ferritin-class
        # zero-candidate failures) — disclosed, the campaign continues on
        # the delivered targets
        log_line(f"[{segment} WARNING] boundary failures recorded: {missing}")
    verdict = segment_verdict(ordered, segment, missing=missing)
    (stage_dir / "verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mc = verdict["mcnemar"]
    extra = ""
    if "go_rule" in verdict:
        extra = f" GO={verdict['go_rule']['verdict']}"
    log_line(f"[{segment}] verdict: b:c={mc['b_nav_only']}:{mc['c_rule_only']} "
             f"p={mc['p_exact']:.4g} n={verdict['n_cells']}{extra}")
    return 0


def write_arc() -> dict[str, Any]:
    """The four-segment ladder summary (fig5e data)."""
    arc: dict[str, Any] = {"campaign": "exp29_aptamer_campaign_arc",
                           "segments": {}, "llm_calls": 0}
    for segment in (SEG1_DIR, SEG2_DIR, SEG3_DIR, SEG4_DIR):
        path = RESULTS_DIR / segment / "verdict.json"
        if path.is_file():
            arc["segments"][segment] = json.loads(path.read_text(encoding="utf-8"))
    panels_path = RESULTS_DIR / "panels.json"
    if panels_path.is_file():
        arc["panels"] = json.loads(panels_path.read_text(encoding="utf-8"))
    segs = [arc["segments"].get(s) for s in (SEG3_DIR, SEG4_DIR)]
    if all(segs):
        b = sum(s["mcnemar"]["b_nav_only"] for s in segs)
        c = sum(s["mcnemar"]["c_rule_only"] for s in segs)
        arc["pooled_seg3_seg4"] = {
            "b": b, "c": c, "p_exact": exact_mcnemar(b, c),
            "p_permutation_1e4": permutation_null(b, c),
        }
    (RESULTS_DIR / "arc.json").write_text(
        json.dumps(arc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log_line(f"[arc] wrote arc.json with {len(arc['segments'])} segment verdicts")
    return arc


# ─────────────────────────── budget sweep ───────────────────────────

SWEEP_CAPS = (24, 32)


def _sweep_static_gears(cap: int) -> tuple[tuple[int, int, int], ...]:
    """Pre-registered static scaling rule: equal split floor(cap/3) samples
    per band at the same three band-centre lengths, one seed (42).  At 48
    this reproduces the frozen static arm's 16/16/16 total."""
    n_each = cap // 3
    return tuple((L, 42, n_each) for L in (30, 47, 70))


def run_sweep_cell(cap: int, meta: dict[str, Any], inst: Instrument,
                   log=log_line) -> dict[str, Any]:
    """One sweep cell: static grid at floor(cap/3)-per-band vs the shipped
    navigator at the same cap, identical matrix v3 and delivery rule."""
    tid = meta["_target_id"]
    struct = resolve_structure(meta)
    t0 = time.perf_counter()
    if struct is None and not meta.get("protein_sequence"):
        return {"sweep_cap": cap, "target_id": tid, "success": False,
                "error": f"no structure for {meta.get('pdb_id')}"}
    ctx = inst.resolve_cell_context(meta, struct)
    config = _make_config(_MATRIX_V3(), _DENSE_LATTICE())
    config = _make_config(_MATRIX_V3(), _DENSE_LATTICE())
    import dataclasses
    config = dataclasses.replace(config, raw_budget_per_target=cap)

    gears = _sweep_static_gears(cap)
    from agent_core.generation.gennav_aptamer import (
        evaluate_matrix, gc_fraction, longest_stem_bp,
    )
    fetched = _fetch_gears_parallel(inst, ctx, list(gears), log=log)
    pool_a: list[dict] = []
    seen: set[str] = set()
    spent_a = 0
    for L, seed, n in gears:
        spent_a += n
        for idx, seq in enumerate(fetched[(L, seed, n)]):
            if not seq or seq in seen:
                continue
            seen.add(seq)
            structure, mfe = inst.fold(seq)
            gc = gc_fraction(seq)
            stem = longest_stem_bp(structure) if structure else 0
            pool_a.append({
                "id": f"grid:L{L}:s{seed}:i{idx}", "sequence": seq,
                "gear": {"aptamer_length": L, "seed": seed, "n_samples": n},
                "gc": round(gc, 4), "longest_stem_bp": stem, "mfe": mfe,
                "matrix_pass": evaluate_matrix(seq, gc, stem, config),
            })
    deliveries_a = _deliveries(pool_a, config)

    nav = inst.production_navigation(meta, struct, raw_budget=cap)
    trace = nav["trace"]
    deliveries_c = dict(trace.get("deliveries") or {})
    rec = {
        "sweep_cap": cap, "target_id": tid, "success": True,
        "arms": {
            "A": {"raw_spent": spent_a, "raw_budget": cap,
                  "cells_pass": _cells_pass(deliveries_a),
                  "e2e": _e2e(_cells_pass(deliveries_a)),
                  "deliveries": deliveries_a,
                  "pool": _pool_snapshot(pool_a)},
            "C": {"raw_spent": trace.get("raw_spent"),
                  "raw_budget": trace.get("raw_budget"),
                  "cells_pass": _cells_pass(deliveries_c),
                  "e2e": _e2e(_cells_pass(deliveries_c)),
                  "deliveries": deliveries_c,
                  "rounds": trace.get("rounds"),
                  "probe": trace.get("probe"),
                  "final_gaps": trace.get("final_gaps"),
                  "pool_size": trace.get("pool_size")},
        },
        "elapsed_seconds": round(time.perf_counter() - t0, 1),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    ca = sum(rec["arms"]["A"]["cells_pass"].values())
    cc = sum(rec["arms"]["C"]["cells_pass"].values())
    log(f"[sweep{cap}:{tid}] A={ca}/3 C={cc}/3 "
        f"(nav {trace.get('raw_spent')}/{cap})")
    return rec


def run_sweep_stage(cap: int, targets_meta: list[dict[str, Any]], *,
                    resume: bool, workers: int = 1,
                    worker_id: Optional[int] = None,
                    prefix: str = "sweep") -> int:
    stage_dir = RESULTS_DIR / f"{prefix}_cap{cap}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    manifest_ids = [m["_target_id"] for m in targets_meta]
    if worker_id is not None:
        out = stage_dir / f"runs_worker{worker_id}.jsonl"
        caches = Caches(CACHES_DIR / f"worker{worker_id}")
        caches.seed_from(Caches(CACHES_DIR))
        inst = Instrument(caches)
        done = {r.get("target_id") for r in load_records(out)}
        for meta in targets_meta:
            if meta["_target_id"] in done:
                continue
            try:
                rec = run_sweep_cell(cap, meta, inst)
            except Exception as exc:  # noqa: BLE001
                log_line(f"[sweep{cap}:w{worker_id}:{meta['_target_id']}] "
                         f"FAILURE: {exc!r}")
                rec = {"sweep_cap": cap, "target_id": meta["_target_id"],
                       "success": False, "error": repr(exc)}
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        caches.flush()
        return 0
    if workers > 1:
        done: set[str] = set()
        for path in [stage_dir / "runs.jsonl"] + \
                sorted(stage_dir.glob("runs_worker*.jsonl")):
            done |= {r["target_id"] for r in load_records(path)
                     if r.get("success")}
        remaining = [m for m in targets_meta if m["_target_id"] not in done]
        chunks: list[list[dict]] = [[] for _ in range(workers)]
        loads = [0.0] * workers
        for m in sorted(remaining,
                        key=lambda x: -(x.get("protein_length_aa") or 100)):
            k = min(range(workers), key=lambda i: loads[i])
            chunks[k].append(m)
            loads[k] += (m.get("protein_length_aa") or 100) ** 2
        log_line(f"[sweep{cap}] parallel launch: {len(done)} done, "
                 f"{len(remaining)} remaining across {workers} workers")
        procs = []
        for k, chunk in enumerate(chunks):
            if not chunk:
                continue
            lf = (stage_dir / f"worker{k}.log").open("w", encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).resolve()),
                   "sweep-worker", str(cap),
                   "--targets", ",".join(m["_target_id"] for m in chunk),
                   "--worker-id", str(k), "--resume",
                   "--sweep-prefix", prefix]
            procs.append((k, subprocess.Popen(
                cmd, env={**os.environ,
                          "PYTHONPATH": f"{PROJECT_ROOT}:{os.environ.get('PYTHONPATH', '')}"},
                stdout=lf, stderr=subprocess.STDOUT), lf))
        for k, proc, lf in procs:
            rc = proc.wait()
            lf.close()
            log_line(f"[sweep{cap}] worker{k} exit={rc}")
        root_caches = Caches(CACHES_DIR)
        for wc in sorted(CACHES_DIR.glob("worker*")):
            if wc.is_dir():
                Caches(wc).merge_into(root_caches)
        root_caches.flush()
    # merge + verdict
    merged: dict[str, dict] = {}
    for path in [stage_dir / "runs.jsonl"] + \
            sorted(stage_dir.glob("runs_worker*.jsonl")):
        for r in load_records(path):
            if r.get("success") and r["target_id"] not in merged:
                merged[r["target_id"]] = r
    ordered = [merged[t] for t in manifest_ids if t in merged]
    with (stage_dir / "runs.jsonl").open("w", encoding="utf-8") as fh:
        for r in ordered:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    for wk in sorted(stage_dir.glob("runs_worker*.jsonl")):
        wk.unlink()
    if not ordered:
        return 1
    verdict = segment_verdict(ordered, f"sweep_cap{cap}")
    verdict["cap"] = cap
    (stage_dir / "verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mc = verdict["mcnemar"]
    log_line(f"[sweep{cap}] verdict: b:c={mc['b_nav_only']}:{mc['c_rule_only']} "
             f"p={mc['p_exact']:.4g} delivered "
             f"C{verdict['delivered_cells']['C']} A{verdict['delivered_cells']['A']} "
             f"e2e C{verdict['e2e_targets']['C']} A{verdict['e2e_targets']['A']}")
    return 0 if ordered else 1


def summarize_sweep() -> dict[str, Any]:
    """The cost-delivery curve across caps (fig5h data)."""
    curve: dict[str, Any] = {"frozen_48": {}, "sweep": {}}
    v48 = json.loads((RESULTS_DIR / SEG3_DIR / "verdict.json").read_text())
    curve["frozen_48"] = {
        "delivered": v48["delivered_cells"], "e2e": v48["e2e_targets"],
        "nav_spend_mean": v48["budget"]["nav_raw_spent_mean"],
        "static_spend": RAW_CAP,
    }
    for cap in SWEEP_CAPS:
        path = RESULTS_DIR / f"sweep_cap{cap}" / "verdict.json"
        if path.is_file():
            v = json.loads(path.read_text())
            curve["sweep"][cap] = {
                "delivered": v["delivered_cells"], "e2e": v["e2e_targets"],
                "mcnemar": v["mcnemar"],
                "nav_spend_mean": v["budget"]["nav_raw_spent_mean"],
                "static_spend": 3 * (cap // 3),
            }
    (RESULTS_DIR / "sweep_curve.json").write_text(
        json.dumps(curve, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    log_line(f"[sweep] curve: " + json.dumps(
        {k: v.get("delivered") for k, v in curve["sweep"].items()}))
    return curve

def verify(stage: str) -> int:
    """Recompute every stored evaluation primitive byte-identically:
    matrix_pass from stored (seq, gc, stem), deliver_profile over stored
    pools (or the stored delivery sets for the production arms), cell
    outcomes, exact + permutation McNemar, verdict."""
    from agent_core.generation.gennav_aptamer import (
        evaluate_matrix, gc_fraction, longest_stem_bp, normalized_levenshtein,
    )
    segments = [SEG1_DIR, SEG2_DIR, SEG3_DIR, SEG4_DIR] \
        if stage == "all" else [stage]
    mismatches = 0
    for segment in segments:
        stage_dir = RESULTS_DIR / segment
        records = load_records(stage_dir / "runs.jsonl")
        assert records, f"{segment}: no records"
        config = _make_config(MATRIX_V0, SPARSE_LATTICE) \
            if segment == SEG1_DIR else _make_config(_MATRIX_V3(), _DENSE_LATTICE())
        for rec in records:
            if not rec.get("success"):
                continue
            for arm_key in ("A", "C"):
                arm = rec["arms"][arm_key]
                pool = arm.get("pool")
                if pool is not None:
                    for cand in pool:
                        gc = gc_fraction(cand["sequence"])
                        stem = cand["longest_stem_bp"]
                        if round(gc, 4) != cand["gc"] or \
                                stem != cand["longest_stem_bp"]:
                            mismatches += 1
                            log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                     f"{arm_key} {cand['id']} primitives")
                        if evaluate_matrix(cand["sequence"], gc, stem, config) \
                                != cand["matrix_pass"]:
                            mismatches += 1
                            log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                     f"{arm_key} {cand['id']} matrix_pass")
                    redeliveries = _deliveries([dict(c) for c in pool], config)
                else:
                    # production arm: recompute the stored delivery record's
                    # primitives from the delivered sequences themselves
                    redeliveries = arm["deliveries"]
                    for prof, stored in redeliveries.items():
                        seqs = [c["sequence"] for c in stored.get("candidates") or []]
                        if stored.get("degraded") != (len(seqs) < 5):
                            mismatches += 1
                            log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                     f"{arm_key} {prof} degraded")
                        dists = [normalized_levenshtein(seqs[i], seqs[j])
                                 for i in range(len(seqs))
                                 for j in range(i + 1, len(seqs))]
                        d1 = round(min(dists), 4) if dists else None
                        if d1 != stored.get("d1_min_dist"):
                            mismatches += 1
                            log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                     f"{arm_key} {prof} d1_min_dist")
                        for c in stored.get("candidates") or []:
                            gc = gc_fraction(c["sequence"])
                            if round(gc, 4) != c["gc"] or \
                                    len(c["sequence"]) != c["length"]:
                                mismatches += 1
                                log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                         f"{arm_key} {prof} cand primitives")
                            if not evaluate_matrix(
                                    c["sequence"], gc,
                                    c["longest_stem_bp"], config)[prof]:
                                mismatches += 1
                                log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                         f"{arm_key} {prof} cand band pass")
                for prof in PROFILE_ORDER:
                    stored = arm["deliveries"].get(prof) or {}
                    new = redeliveries.get(prof) or {}
                    for key in ("degraded", "n_passing_in_band", "d1_min_dist"):
                        if new.get(key) != stored.get(key):
                            mismatches += 1
                            log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                     f"{arm_key} {prof}.{key}")
                    if pool is not None:
                        if [x["id"] for x in new.get("candidates") or []] != \
                                [x["id"] for x in stored.get("candidates") or []]:
                            mismatches += 1
                            log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                     f"{arm_key} {prof} delivery ids")
                new_cells = _cells_pass(redeliveries)
                if arm["cells_pass"] != new_cells:
                    mismatches += 1
                    log_line(f"VERIFY MISMATCH {rec['target_id']} "
                             f"{arm_key} cells_pass")
                if arm["e2e"] != _e2e(new_cells):
                    mismatches += 1
                    log_line(f"VERIFY MISMATCH {rec['target_id']} "
                             f"{arm_key} e2e")
                if (arm["raw_spent"] or 0) > RAW_CAP:
                    mismatches += 1
                    log_line(f"VERIFY MISMATCH {rec['target_id']} "
                             f"{arm_key} budget violation")
        manifest_ids = [t["_target_id"] for t in load_targets()]
        if segment == SEG3_DIR and (RESULTS_DIR / "panels.json").is_file():
            panels = json.loads(
                (RESULTS_DIR / "panels.json").read_text(encoding="utf-8"))
            panel_ids = panels["panel_D_decisive"]
        elif segment == SEG4_DIR and (RESULTS_DIR / "panels.json").is_file():
            panels = json.loads(
                (RESULTS_DIR / "panels.json").read_text(encoding="utf-8"))
            panel_ids = panels["panel_C_confirmation"]
        else:
            panel_ids = manifest_ids
        ok_records = [r for r in records if r.get("success")]
        present = {r["target_id"] for r in ok_records}
        missing = [t for t in panel_ids if t not in present]
        verdict = segment_verdict(ok_records, segment, missing=missing)
        stored_verdict = json.loads(
            (stage_dir / "verdict.json").read_text(encoding="utf-8"))
        if json.dumps(verdict, sort_keys=True) != \
                json.dumps(stored_verdict, sort_keys=True):
            mismatches += 1
            log_line(f"VERIFY MISMATCH: {segment} verdict differs")
        log_line(f"[verify:{segment}] "
                 f"{'CLEAN' if mismatches == 0 else 'MISMATCHES'} "
                 f"so far over {len(records)} records")
    total = sum(len(load_records(RESULTS_DIR / s / "runs.jsonl"))
                for s in segments)
    log_line(f"[verify:{stage}] "
             f"{'BYTE-IDENTICAL' if mismatches == 0 else f'{mismatches} MISMATCHES'} "
             f"over {total} records + verdicts")
    return 0 if mismatches == 0 else 1


# ─────────────────────────── main ───────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", nargs="?", default=None,
                        choices=["pilot", "phaseA", "phaseB", "panels",
                                 "arc", "sweep", "sweep-expanded",
                                 "sweep-worker", "verify"])
    parser.add_argument("stage", nargs="?", default=None,
                        help="verify target: seg dir name or 'all'")
    parser.add_argument("--targets", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--worker-id", type=int, default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--stage", dest="stage_opt", default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--stage-root", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--sweep-prefix", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.worker_id is not None:
        ids = args.targets.split(",")
        metas = [m for m in load_targets() if m["_target_id"] in ids]
        stage_root = Path(args.stage_root) if args.stage_root else None
        if args.mode == "sweep-worker":
            cap = int(args.stage or 0)
            prefix = args.sweep_prefix or "sweep"
            metas_all = load_targets("expanded")
            by_id = {m["_target_id"]: m for m in metas_all}
            metas = [by_id[i] for i in ids if i in by_id]
            return run_sweep_stage(cap, metas, resume=True, workers=1,
                                   worker_id=args.worker_id, prefix=prefix)
        return run_stage(args.stage_opt, metas, resume=True, workers=1,
                         worker_id=args.worker_id, stage_root=stage_root)

    if args.mode is None:
        parser.error("mode is required (pilot|phaseA|phaseB|panels|arc|verify)")

    if args.mode == "verify":
        return verify(args.stage or args.targets or "all")

    targets_meta = load_targets()
    if args.targets:
        keep = {t.strip() for t in args.targets.split(",")}
        targets_meta = [m for m in targets_meta if m["_target_id"] in keep]

    if args.mode == "pilot":
        pilots = [m for m in targets_meta
                  if m["_target_id"] in PILOT_TARGETS]
        stage_root = RESULTS_DIR / "pilot"
        rc = 0
        for segment in (SEG1_DIR, SEG2_DIR):
            rc |= run_stage(segment, pilots, resume=args.resume,
                            workers=args.workers, stage_root=stage_root)
        # seg3 production-path smoke on the pilot pair
        panels = {"panel_D_decisive": PILOT_TARGETS,
                  "panel_C_confirmation": []}
        (stage_root / "panels_smoke.json").write_text(
            json.dumps(panels, indent=2) + "\n", encoding="utf-8")
        rc |= run_stage(SEG3_DIR, pilots, resume=args.resume,
                        workers=args.workers, stage_root=stage_root)
        return rc

    if args.mode == "panels":
        select_panels()
        return 0

    if args.mode == "arc":
        write_arc()
        return 0

    if args.mode == "sweep":
        panels = json.loads(
            (RESULTS_DIR / "panels.json").read_text(encoding="utf-8"))
        by_id = {m["_target_id"]: m for m in load_targets()}
        panel_d = [by_id[t] for t in panels["panel_D_decisive"] if t in by_id]
        rc = 0
        for cap in (24, 32):
            rc |= run_sweep_stage(cap, panel_d, resume=args.resume,
                                  workers=args.workers)
        if rc == 0:
            summarize_sweep()
        return rc

    if args.mode == "sweep-expanded":
        metas = [m for m in load_targets("expanded")
                 if m["_target_id"] not in {t["_target_id"] for t in load_targets("base")}
                 or True]
        # run EVERY expanded-pool target (base targets with existing cap-24/32
        # records resume instantly; caps 16/20 and 48 are new for all)
        rc = 0
        for cap in (16, 20, 24, 32, 48):
            rc |= run_sweep_stage(cap, metas, resume=args.resume,
                                  workers=args.workers, prefix="expanded")
        if rc == 0:
            summarize_expanded()
        return rc

    if args.mode == "phaseA":
        rc = run_stage(SEG1_DIR, targets_meta, resume=args.resume,
                       workers=args.workers)
        if rc != 0:
            return rc
        # seg2 needs every seg1 record (S1 priors) — merge caches first
        rc = run_stage(SEG2_DIR, targets_meta, resume=args.resume,
                       workers=args.workers)
        if rc == 0:
            select_panels()
        return rc

    if args.mode == "phaseB":
        panels = json.loads(
            (RESULTS_DIR / "panels.json").read_text(encoding="utf-8"))
        by_id = {m["_target_id"]: m for m in load_targets()}
        panel_d = [by_id[t] for t in panels["panel_D_decisive"] if t in by_id]
        panel_c = [by_id[t] for t in panels["panel_C_confirmation"]
                   if t in by_id]
        rc = run_stage(SEG3_DIR, panel_d, resume=args.resume,
                       workers=args.workers)
        if panel_c:
            rc |= run_stage(SEG4_DIR, panel_c, resume=args.resume,
                            workers=args.workers)
        else:
            log_line("[phaseB] empty confirmation panel — seg4 skipped")
        if rc == 0:
            write_arc()
        return rc

    return 1


if __name__ == "__main__":
    raise SystemExit(main())


def summarize_expanded() -> dict[str, Any]:
    """The promotion analysis: full-pool (~39-target) per-cap verdicts
    combining the base-pool sweep records with the expanded-pool records —
    paired-cell McNemar AND the target-level e2e pairing (sign test) per
    cap.  (Re-appended 2026-09-05: the original definition was lost in a
    later patch and the cap48 run crashed calling it; the cap48 verdict
    itself was already written by finalize.)"""
    base_ids = {t["_target_id"] for t in load_targets("base")}
    out: dict[str, Any] = {"caps": {}, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for cap in (16, 20, 24, 32, 48):
        records: list[dict] = []
        for prefix in ("expanded", "sweep"):
            path = RESULTS_DIR / f"{prefix}_cap{cap}" / "runs.jsonl"
            if not path.is_file():
                continue
            for r in load_records(path):
                if not r.get("success"):
                    continue
                if prefix == "sweep" and r["target_id"] not in base_ids:
                    continue
                records.append(r)
        if not records:
            continue
        by_t = {}
        for r in records:
            by_t[r["target_id"]] = r
        records = list(by_t.values())
        verdict = segment_verdict(records, f"expanded_cap{cap}")
        verdict["cap"] = cap
        verdict["n_targets_full_pool"] = len(records)
        (RESULTS_DIR / f"expanded_cap{cap}").mkdir(exist_ok=True)
        (RESULTS_DIR / f"expanded_cap{cap}" / "full_pool_verdict.json").write_text(
            json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        e2e_b = sum(1 for r in records if r["arms"]["C"]["e2e"] and not r["arms"]["A"]["e2e"])
        e2e_c = sum(1 for r in records if r["arms"]["A"]["e2e"] and not r["arms"]["C"]["e2e"])
        out["caps"][cap] = {
            "n_targets": len(records),
            "delivered": verdict["delivered_cells"],
            "mcnemar": verdict["mcnemar"],
            "e2e_targets": verdict["e2e_targets"],
            "e2e_paired": {"nav_only": e2e_b, "static_only": e2e_c,
                           "p_sign": exact_mcnemar(e2e_b, e2e_c)},
        }
        log_line(f"[expanded cap{cap}] n={len(records)} delivered "
                 f"C{verdict['delivered_cells']['C']} A{verdict['delivered_cells']['A']} "
                 f"b:c={verdict['mcnemar']['b_nav_only']}:{verdict['mcnemar']['c_rule_only']} "
                 f"p={verdict['mcnemar']['p_exact']:.4g} | e2e "
                 f"{verdict['e2e_targets']['C']}:{verdict['e2e_targets']['A']} "
                 f"paired {e2e_b}:{e2e_c} p={out['caps'][cap]['e2e_paired']['p_sign']:.4g}")
    (RESULTS_DIR / "expanded_summary.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
