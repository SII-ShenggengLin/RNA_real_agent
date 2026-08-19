"""GenNav production wiring tests for ``RnaAptamerDesignWorkflow`` (v2.1.0).

Pins the navigation path added 2026-08-19 (input field ``navigation``,
``_generate_aptamer_navigation``, ``_gennav_trace`` state writeback) against
a fully stubbed capability layer — no services, no LLM:

- lattice probe issues exactly one ODesign request per lattice length;
- the cycling guarantee-round allocation respects the 48-raw budget and
  stops early once every profile is deliverable;
- a starved band keeps consuming guarantee rounds up to the budget and its
  delivery degrades explicitly;
- per-profile delivery honours the matrix-v3 filter and the D1 diversity
  floor;
- a run where nothing passes any profile fails with the dedicated
  ``navigation_delivery_empty`` error and still writes the audit trace;
- the default (navigation=False) path is unchanged.

The pure-function invariants themselves live in
``tests/test_gennav_aptamer_core.py``.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Callable

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.file_manager import save_text_file
from agent_core.generation.gennav_aptamer import AptamerNavConfig
from agent_core.workflows.rna_aptamer_design import (
    RnaAptamerDesignInput,
    RnaAptamerDesignWorkflow,
)

CONFIG = AptamerNavConfig()

# ═════════════════════════════════════════════════════════════════════════════
# Stub capability layer
# ═════════════════════════════════════════════════════════════════════════════


class _StubCapability:
    def __init__(self, name: str, fn: Callable[[dict], dict]) -> None:
        self._name = name
        self._fn = fn

    def invoke(self, args: dict, state: dict | None = None) -> CapabilityResult:
        return CapabilityResult(success=True, tool_name=self._name, output=self._fn(args))


class _StubRegistry:
    """Duck-typed CapabilityRegistry: only the names in ``caps`` exist."""

    def __init__(self, caps: dict[str, Callable[[dict], dict]]) -> None:
        self._caps = {name: _StubCapability(name, fn) for name, fn in caps.items()}

    def has(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> _StubCapability:
        return self._caps[name]


def _synth_seq(length: int, idx: int, gc_target: float) -> str:
    """Deterministic RNA sequence with GC ≈ *gc_target* and shuffled bases."""
    rng = random.Random((length << 12) ^ (idx * 7919))
    n_gc = round(length * gc_target / 2)
    n_au = length - 2 * n_gc
    letters = ["G"] * n_gc + ["C"] * n_gc + ["A"] * (n_au // 2) + ["U"] * (n_au - n_au // 2)
    rng.shuffle(letters)
    return "".join(letters)


class _OdesignFactory:
    """Stateful ODesign stub: synthesises unique candidates per request."""

    def __init__(self, gc_of_length: Callable[[int], float]) -> None:
        self.gc_of_length = gc_of_length
        self.requests: list[dict] = []
        self.counter = 0

    def build_json(self, args: dict) -> dict:
        cfg = [{
            "name": "stub",
            "chains": [
                {"chain_type": "proteinChain",
                 "sequence": f"{args['protein_chain_id']}/1-{args['protein_sequence_length']}"},
                {"chain_type": "rnaChain",
                 "sequence": f"{args['aptamer_length']}-{args['aptamer_length']}"},
            ],
            "hotspot": args["hotspot_residues"],
        }]
        path = save_text_file(json.dumps(cfg), prefix="gennav_test_input", suffix=".json")
        return {"input_json_filepath": path}

    def infer(self, args: dict) -> dict:
        cfg = json.loads(Path(args["input_json_filepath"]).read_text(encoding="utf-8"))
        length = int(cfg[0]["chains"][1]["sequence"].split("-")[0])
        n = int(args["n_sample"])
        self.requests.append({"length": length, "n": n})
        paths = []
        for _ in range(n):
            self.counter += 1
            seq = _synth_seq(length, self.counter, self.gc_of_length(length))
            paths.append(save_text_file(f">stub\n{seq}\n", prefix="gennav_test_pred", suffix=".fasta"))
        return {"prediction_filepaths": paths}


def _make_workflow(odesign: _OdesignFactory) -> RnaAptamerDesignWorkflow:
    caps: dict[str, Callable[[dict], dict]] = {
        "build_odesign_aptamer_input_json": odesign.build_json,
        "run_odesign_inference": odesign.infer,
        "predict_rna_secondary_structure_with_linearfold": lambda args: {
            "structure": "." * len(_read_seq(args["filepath"])), "mfe": -3.0,
        },
        "compute_rna_sequence_gc_content": lambda args: {
            "gc_content": (_read_seq(args["filepath"]).count("G")
                           + _read_seq(args["filepath"]).count("C"))
            / len(_read_seq(args["filepath"])),
        },
    }
    return RnaAptamerDesignWorkflow(_StubRegistry(caps))


def _read_seq(filepath: str) -> str:
    content = Path(filepath).read_text(encoding="utf-8")
    return "".join(
        ln.strip() for ln in content.splitlines() if not ln.startswith(">")
    ).upper().replace("T", "U")


@pytest.fixture(autouse=True)
def _no_service_autostart(monkeypatch):
    monkeypatch.setattr(RnaAptamerDesignWorkflow, "_ensure_services_running", lambda self: None)


@pytest.fixture
def protein_stub_file(tmp_path: Path) -> str:
    p = tmp_path / "protein.pdb"
    p.write_text("ATOM  1  CA  ALA A   1\n", encoding="utf-8")
    return str(p)


def _nav_input(protein_stub_file: str, **overrides) -> RnaAptamerDesignInput:
    defaults = dict(
        protein_structure_path=protein_stub_file,
        protein_sequence="MKT" * 10,
        chain_id="A",
        hotspot_residues="A/5",
        navigation=True,
    )
    defaults.update(overrides)
    return RnaAptamerDesignInput(**defaults)


# ═════════════════════════════════════════════════════════════════════════════
# Navigation generation
# ═════════════════════════════════════════════════════════════════════════════


def test_probe_requests_every_lattice_length(protein_stub_file):
    odesign = _OdesignFactory(lambda length: 0.5)
    wf = _make_workflow(odesign)
    candidates = wf._generate_aptamer_navigation(
        protein_stub_file, "A/5", _nav_input(protein_stub_file), protein_seq_len=30,
    )
    probe_requests = [r for r in odesign.requests if r["n"] == 1]
    probed_lengths = {r["length"] for r in probe_requests}
    assert probed_lengths == set(CONFIG.lattice_lengths)
    assert candidates, "healthy scenario must deliver candidates"


def test_budget_cap_and_early_stop(protein_stub_file):
    odesign = _OdesignFactory(lambda length: 0.5)
    wf = _make_workflow(odesign)
    wf._generate_aptamer_navigation(
        protein_stub_file, "A/5", _nav_input(protein_stub_file), protein_seq_len=30,
    )
    trace = wf._workflow_state["_gennav_trace"]
    assert trace["raw_spent"] <= CONFIG.raw_budget_per_target
    assert sum(r["n_samples"] for r in trace["rounds"]) + len(CONFIG.lattice_lengths) == trace["raw_spent"]
    # every band full -> the navigator stops before burning the whole budget
    assert all(g == 0 for g in trace["final_gaps"].values())
    assert trace["raw_spent"] < CONFIG.raw_budget_per_target
    # guarantee rounds fire before mechanized ones
    assert all(r["kind"] == "guarantee" for r in trace["rounds"])


def test_delivery_respects_matrix_and_diversity(protein_stub_file):
    odesign = _OdesignFactory(lambda length: 0.5)
    wf = _make_workflow(odesign)
    wf._generate_aptamer_navigation(
        protein_stub_file, "A/5", _nav_input(protein_stub_file), protein_seq_len=30,
    )
    trace = wf._workflow_state["_gennav_trace"]
    for profile, delivery in trace["deliveries"].items():
        assert len(delivery["ids"]) == CONFIG.delivery_size
        assert not delivery["degraded"]
        assert delivery["d1_min_dist"] >= CONFIG.d1_min_pairwise - 1e-9
        spec = CONFIG.profiles[profile]
        for cand in delivery["candidates"]:
            assert spec["lo"] <= cand["length"] <= spec["hi"]
            assert spec["gc_lo"] <= cand["gc"] <= spec["gc_hi"]


def test_starved_band_degrades_within_budget(protein_stub_file):
    # compact-band lengths get out-of-window GC -> compact never fills
    odesign = _OdesignFactory(
        lambda length: 0.75 if length <= CONFIG.profiles["compact"]["hi"] else 0.5
    )
    wf = _make_workflow(odesign)
    candidates = wf._generate_aptamer_navigation(
        protein_stub_file, "A/5", _nav_input(protein_stub_file), protein_seq_len=30,
    )
    trace = wf._workflow_state["_gennav_trace"]
    assert trace["raw_spent"] <= CONFIG.raw_budget_per_target
    compact = trace["deliveries"]["compact"]
    assert compact["degraded"] and compact["ids"] == []
    assert trace["deliveries"]["standard"]["ids"]
    assert trace["deliveries"]["extended"]["ids"]
    # all reinforcement budget went to the starved band
    assert all(
        r["length"] <= CONFIG.profiles["compact"]["hi"] for r in trace["rounds"]
    )
    assert candidates, "other bands still deliver"


# ═════════════════════════════════════════════════════════════════════════════
# run() integration
# ═════════════════════════════════════════════════════════════════════════════


def test_run_navigation_success_summary_and_metadata(protein_stub_file):
    odesign = _OdesignFactory(lambda length: 0.5)
    wf = _make_workflow(odesign)
    result = wf.run(_nav_input(protein_stub_file))
    assert result.success, result.summary
    assert "[GenNav]" in result.summary
    assert result.all_candidates
    for cand in result.all_candidates:
        assert cand.metadata.get("nav_bands")
        assert cand.metadata.get("nav_matrix_pass")
    assert "_gennav_trace" in result._state_writeback


def test_run_navigation_all_bands_fail_is_explicit_degrade(protein_stub_file):
    odesign = _OdesignFactory(lambda length: 0.95)
    wf = _make_workflow(odesign)
    result = wf.run(_nav_input(protein_stub_file))
    assert not result.success
    assert result.errors == ["navigation_delivery_empty"]
    assert "degrade" in result.summary
    assert "_gennav_trace" in result._state_writeback


def test_navigation_defaults_off(protein_stub_file):
    inp = _nav_input(protein_stub_file, navigation=False)
    assert inp.navigation is False
    # static path: single gear through _generate_aptamer_module
    odesign = _OdesignFactory(lambda length: 0.5)
    wf = _make_workflow(odesign)
    candidates = wf._generate_aptamer_module(
        protein_stub_file, "A/5", inp, protein_seq_len=30,
    )
    assert candidates
    assert len(odesign.requests) == 1
    assert "_gennav_trace" not in wf._workflow_state
