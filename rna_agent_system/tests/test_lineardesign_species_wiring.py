"""Species-correct LinearDesign design (2026-08-25 platform fix).

Regression tests for the codon-table wiring: ``cai_species`` must resolve to
the platform-shipped LinearDesign CSV (same Kazusa source the CAI evaluator
uses) on both the golden path and the GenNav navigation path; the explicit
``lineardesign_codon_usage_path`` override wins; unresolvable species fail
fast instead of silently designing against the service's default human table.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.sequence_utils import (
    LINEARDESIGN_CODON_TABLES_DIR,
    lineardesign_codon_table_for_species,
)
from agent_core.workflows.mrna_cds_design import (
    MrnaCdsDesignInput,
    MrnaCdsDesignWorkflow,
    _lineardesign_codon_table,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── table resolution ─────────────────────────────────────────────────────────

def test_builtin_species_resolve_to_existing_csvs():
    for species, fname in [
        ("Homo sapiens", "Homo_sapiens.csv"),
        ("human", "Homo_sapiens.csv"),
        ("E. coli", "Escherichia_coli_K-12.csv"),
        ("ecoli", "Escherichia_coli_K-12.csv"),
        ("Escherichia coli K-12", "Escherichia_coli_K-12.csv"),
        ("Saccharomyces cerevisiae", "Saccharomyces_cerevisiae.csv"),
        ("yeast", "Saccharomyces_cerevisiae.csv"),
    ]:
        path = lineardesign_codon_table_for_species(species)
        assert path is not None, species
        assert Path(path).name == fname
        assert Path(path).is_file()


def test_unknown_species_returns_none():
    assert lineardesign_codon_table_for_species("Martian pseudomonas") is None


def test_every_builtin_table_has_64_codons():
    csvs = sorted(LINEARDESIGN_CODON_TABLES_DIR.glob("*.csv"))
    assert len(csvs) == 11
    for csv_path in csvs:
        rows = [l for l in csv_path.read_text(encoding="utf-8").splitlines()
                if l and not l.startswith("#")]
        assert len(rows) == 64, csv_path.name


def test_generator_check_passes():
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "gen_lineardesign_codon_tables.py"), "--check"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── workflow wiring ──────────────────────────────────────────────────────────

class _CapturingLinearDesign:
    name = "design_mrna_cds_with_lineardesign"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def invoke(self, tool_args: dict[str, Any], state: Optional[dict] = None) -> CapabilityResult:
        self.calls.append(dict(tool_args))
        return CapabilityResult(
            success=True, tool_name=self.name,
            output={"generated_sequence": "AUG" * 10},
        )


class _StubRegistry:
    def __init__(self, caps: dict[str, Any]) -> None:
        self._caps = caps

    def has(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> Any:
        return self._caps[name]

    def list_names(self) -> list[str]:
        return sorted(self._caps)


def _run_generate(inp: MrnaCdsDesignInput) -> _CapturingLinearDesign:
    cap = _CapturingLinearDesign()
    wf = MrnaCdsDesignWorkflow(_StubRegistry({"design_mrna_cds_with_lineardesign": cap}))
    wf.generate_candidates(inp)
    return cap


def test_generate_passes_species_codon_table():
    cap = _run_generate(MrnaCdsDesignInput(
        protein_sequence="MKVAGIS", design_tool="lineardesign",
        lambda_value=0.0, cai_species="E. coli",
    ))
    assert len(cap.calls) == 1
    path = cap.calls[0]["codon_usage_path"]
    assert path.endswith("Escherichia_coli_K-12.csv")


def test_generate_human_uses_platform_table_not_service_default():
    cap = _run_generate(MrnaCdsDesignInput(
        protein_sequence="MKVAGIS", design_tool="lineardesign",
        lambda_value=0.0, cai_species="Homo sapiens",
    ))
    assert cap.calls[0]["codon_usage_path"].endswith("Homo_sapiens.csv")


def test_explicit_override_wins():
    cap = _run_generate(MrnaCdsDesignInput(
        protein_sequence="MKVAGIS", design_tool="lineardesign",
        lambda_value=0.0, cai_species="ecoli",
        lineardesign_codon_usage_path="/tmp/my_table.csv",
    ))
    assert cap.calls[0]["codon_usage_path"] == "/tmp/my_table.csv"


def test_unknown_species_fails_fast_when_lineardesign_used():
    with pytest.raises(ValueError, match="No codon-usage table"):
        MrnaCdsDesignInput(
            protein_sequence="MKVAGIS", design_tool="lineardesign",
            lambda_value=0.0, cai_species="Martian pseudomonas",
        )


def test_unknown_species_tolerated_without_lineardesign():
    # No LinearDesign call → no table resolution → no early failure (the CAI
    # evaluator surfaces the unknown species per candidate, as before).
    cap = _CapturingLinearDesign()
    wf = MrnaCdsDesignWorkflow(_StubRegistry({"design_mrna_cds_with_lineardesign": cap}))
    candidates = wf.generate_candidates(MrnaCdsDesignInput(
        protein_sequence="MKVAGIS", design_tool="gemorna",
        cai_species="Martian pseudomonas",
    ))
    assert cap.calls == []          # lineardesign never invoked
    assert candidates == []         # gemorna capability absent in the stub registry


def test_lambda_grid_all_carries_table_on_every_call():
    cap = _run_generate(MrnaCdsDesignInput(
        protein_sequence="MKVAGIS", design_tool="all", cai_species="ecoli",
    ))
    # only the lineardesign stub is registered; rnarl/gemorna are skipped
    assert [c["lambda_value"] for c in cap.calls] == [0.0, 1.0, 4.0, 10.0]
    assert all(c["codon_usage_path"].endswith("Escherichia_coli_K-12.csv")
               for c in cap.calls)
