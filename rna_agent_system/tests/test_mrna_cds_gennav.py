"""GenNav-λ production wiring tests for ``MrnaCdsDesignWorkflow`` (v1.2.0).

Pins the navigation path added 2026-08-22 (input field ``navigation``,
``_generate_cds_navigation``, ``_gennav_trace`` state writeback, Pareto
frontier annotation) against a fully stubbed capability layer — no services:

- the λ-curve probe issues exactly one LinearDesign call per lattice λ and
  stops early once every profile band is deliverable;
- per-profile delivery honours the matrix filter and D1 diversity floor and
  candidates carry nav_* metadata + audited tool records;
- a run where nothing passes any profile fails with the dedicated
  ``navigation_delivery_empty`` error and still writes the audit trace;
- the default (navigation=False) path is unchanged (static λ grid + RNARL +
  GEMORNA, no trace);
- successful runs carry the ``pareto_frontier`` annotation (CAI × MFE/nt)
  without changing total_score ordering.

The λ-dependence is encoded in the candidate GC fraction (0.40 + 0.004·λ);
the CAI / LinearFold stubs decode it from the saved sequence file, so the
stub layer exercises the real capability plumbing (file hand-off, audit
records) end-to-end.
"""

from __future__ import annotations

import random
from typing import Any, Optional

from agent_core.capabilities.base import CapabilityResult
from agent_core.file_manager import read_sequence
from agent_core.generation.gennav_mrna_lambda import MrnaNavConfig
from agent_core.workflows.mrna_cds_design import (
    MrnaCdsDesignInput,
    MrnaCdsDesignWorkflow,
)

CONFIG = MrnaNavConfig()
N_AA = 20  # stub protein length → 60-nt CDS


def _seq_for_lambda(lam: float) -> str:
    """Deterministic shuffled RNA with GC fraction ≈ 0.40 + 0.004·λ."""
    length = 3 * N_AA
    n_gc = round(length * (0.40 + 0.004 * lam) / 2)
    n_au = (length - 2 * n_gc) // 2
    letters = ["G"] * n_gc + ["C"] * n_gc + ["A"] * n_au + ["U"] * n_au
    rng = random.Random(int(lam * 1000))
    rng.shuffle(letters)
    return "".join(letters)[:length]


def _decode_lambda(filepath: str) -> float:
    seq = read_sequence(filepath).upper().replace("T", "U")
    gc = sum(1 for c in seq if c in "GC") / len(seq)
    return (gc - 0.40) / 0.004


class _StubCap:
    def __init__(self, name: str, fn) -> None:
        self._name = name
        self._fn = fn
        self.calls: list[dict] = []

    def invoke(self, args: dict, state: Optional[dict] = None) -> CapabilityResult:
        self.calls.append(dict(args))
        return CapabilityResult(success=True, tool_name=self._name, output=self._fn(args))


def _fixed(output: dict):
    return lambda args: dict(output)


class _StubLD(_StubCap):
    def __init__(self, name: str) -> None:
        super().__init__(name, self._make)
        self.mode = "normal"

    def _make(self, args: dict) -> dict:
        lam = float(args.get("lambda_value", 0.0))
        return {"generated_sequence": _seq_for_lambda(lam), "mfe": -10.0}


def _build_registry(cai_mode: str = "normal", mfe_mode: str = "normal") -> dict[str, _StubCap]:
    ld = _StubLD("design_mrna_cds_with_lineardesign")

    def _cai(args: dict) -> dict:
        lam = _decode_lambda(args["filepath"])
        if cai_mode == "low":
            return {"cai_score": round(0.50 + 0.001 * lam, 4)}
        return {"cai_score": round(0.832 + 0.003 * lam, 4)}

    def _fold(args: dict) -> dict:
        lam = _decode_lambda(args["filepath"])
        seq = read_sequence(args["filepath"])
        if mfe_mode == "flat":
            return {"mfe": round((-0.05 + 0.001 * lam) * len(seq), 4), "structure": "." * len(seq)}
        return {"mfe": round((-0.45 + 0.02 * lam) * len(seq), 4), "structure": "." * len(seq)}

    caps: dict[str, _StubCap] = {
        "design_mrna_cds_with_lineardesign": ld,
        "design_mrna_cds_with_rnarl": _StubCap(
            "design_mrna_cds_with_rnarl", _fixed({"generated_sequence": "AUG" * 35})),
        "design_mrna_cds_with_gemorna": _StubCap(
            "design_mrna_cds_with_gemorna", _fixed({"generated_sequence": "AUG" * 40})),
        "predict_rna_secondary_structure": _StubCap(
            "predict_rna_secondary_structure", _fixed({"structure": "." * 200, "mfe_kcal_per_mol": -50.0})),
        "predict_rna_secondary_structure_with_linearfold": _StubCap(
            "predict_rna_secondary_structure_with_linearfold", _fold),
        "compute_rna_sequence_gc_content": _StubCap(
            "compute_rna_sequence_gc_content", _fixed({"gc_content": 0.5, "sequence_length": 200})),
        "compute_rna_sequence_u_content": _StubCap(
            "compute_rna_sequence_u_content", _fixed({"u_fraction": 0.25})),
        "compute_dot_bracket_unpaired_fraction": _StubCap(
            "compute_dot_bracket_unpaired_fraction", _fixed({"unpaired_fraction": 0.5})),
        "predict_mrna_stability_with_rnastop": _StubCap(
            "predict_mrna_stability_with_rnastop", _fixed({"overall_stability": 0.5})),
        "compute_cai_for_cds_sequence": _StubCap("compute_cai_for_cds_sequence", _cai),
    }
    return caps


class _Registry:
    def __init__(self, caps: dict[str, _StubCap]) -> None:
        self._caps = caps

    def has(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> _StubCap:
        return self._caps[name]


def _run(caps: dict[str, _StubCap], **inp_kwargs):
    wf = MrnaCdsDesignWorkflow(_Registry(caps))
    inp = MrnaCdsDesignInput(protein_sequence="M" * N_AA, **inp_kwargs)
    return wf.run(inp)


# ── navigation path ──────────────────────────────────────────────────────────


def test_navigation_early_stop_full_delivery():
    caps = _build_registry()
    result = _run(caps, navigation=True, design_tool="all")

    assert result.success is True
    assert result.errors == []
    trace = result._state_writeback["_gennav_trace"]
    assert trace["protocol"] == "gennav_lambda_production_v1"
    assert trace["raw_spent"] == len(CONFIG.probe_lambdas) + 1  # probe + one guarantee round
    assert len(trace["rounds"]) == 1 and trace["rounds"][0]["kind"] == "guarantee"
    assert trace["raw_spent"] <= CONFIG.raw_budget
    assert trace["pool_size"] == len(CONFIG.probe_lambdas) + 1
    for prof in CONFIG.profile_order:
        d = trace["deliveries"][prof]
        assert len(d["ids"]) == CONFIG.delivery_size
        assert d["degraded"] is False
    # every delivered candidate carries navigation metadata + bands
    assert len(result.all_candidates) >= 9
    for cand in result.all_candidates:
        assert cand.metadata["nav_bands"], cand.source
        assert cand.metadata["nav_matrix_pass"]
        assert cand.source.startswith("cds_design_gennav:lambda")
    # audited LinearDesign calls: one per probed λ, no RNARL/GEMORNA on this path
    ld = caps["design_mrna_cds_with_lineardesign"]
    assert len(ld.calls) == trace["raw_spent"]
    assert {float(c["lambda_value"]) for c in ld.calls} == set(CONFIG.probe_lambdas) | {12.0}
    assert caps["design_mrna_cds_with_rnarl"].calls == []
    assert caps["design_mrna_cds_with_gemorna"].calls == []


def test_navigation_pareto_annotation_without_changing_order():
    caps = _build_registry()
    result = _run(caps, navigation=True)
    assert result.success is True
    assert "pareto_frontier_size" in result.summary
    frontier = getattr(result, "pareto_frontier", None)
    assert frontier, "pareto_frontier extra must be attached"
    scores = [c.scores.get("total_score") for c in result.all_candidates]
    assert scores == sorted(scores, reverse=True)


def test_navigation_all_fail_dedicated_error():
    caps = _build_registry(cai_mode="low", mfe_mode="flat")
    result = _run(caps, navigation=True)

    assert result.success is False
    assert result.errors == ["navigation_delivery_empty"]
    trace = result._state_writeback["_gennav_trace"]
    assert trace is not None
    assert trace["raw_spent"] == CONFIG.raw_budget  # budget exhausted, nothing passed
    for prof in CONFIG.profile_order:
        assert trace["deliveries"][prof]["ids"] == []
        assert trace["deliveries"][prof]["degraded"] is True


# ── static path unchanged ────────────────────────────────────────────────────


def test_static_path_unchanged_when_navigation_false():
    caps = _build_registry()
    result = _run(caps, design_tool="all")

    assert result.success is True
    assert result._state_writeback.get("_gennav_trace") is None
    sources = {c.source.split(":")[0] for c in result.all_candidates}
    assert any(s.startswith("cds_design") for s in sources)
    ld_lambdas = [float(c["lambda_value"]) for c in caps["design_mrna_cds_with_lineardesign"].calls]
    assert sorted(ld_lambdas) == [0.0, 1.0, 4.0, 10.0]
    assert len(caps["design_mrna_cds_with_rnarl"].calls) == 1
    assert len(caps["design_mrna_cds_with_gemorna"].calls) == 1
    # Pareto annotation is present on the static path too
    assert "pareto_frontier_size" in result.summary
    assert getattr(result, "pareto_frontier", None)
