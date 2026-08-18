"""W1.1 oracle-ontology and tool-inventory enforcement tests.

The ToolSpec ``kind`` / ``OracleDescriptor`` ontology is the single source of
truth the CapGate managed-oracle set derives from, and the inventory manifest
is the paper's supplementary tool table.  These tests pin both: every tool
must be classified, every managed oracle must be deliberate, and every tool
without a caller must carry an explicit reservation.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from agent_core.tool_interface import OracleDescriptor, ToolKind

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_ENFORCED_ORACLES = {
    "score_rna_protein_complex_with_egarps": ("egarps_native_probability", "ranking_objective", "rna_aptamer_design"),
    "predict_rna_protein_complex_with_proteinx": ("proteinx_ipTM", "ranking_objective", "rna_aptamer_design"),
    "predict_rna_tertiary_structure_with_rhofold": ("rhofold_mean_plddt", "ranking_objective", "rna_aptamer_design"),
    "predict_5utr_mrl_with_gemorna": ("gemorna_5utr_mrl", "ranking_objective", "full_length_mrna"),
    "predict_3utr_stability_with_gemorna": ("gemorna_3utr_stability", "ranking_objective", "full_length_mrna"),
    "score_rna_ligand_binding_with_rnasmol": ("rnasmol", "screening_evaluation", "rna_small_molecule"),
    # E16/E17/E18 graded 2026-08-18 (all failed their declared-use gates;
    # records in default_self_model.json -> enforced, see verdict.json).
    "score_rna_ligand_binding_with_gernabind": ("gernabind_probability", "screening_evaluation", "rna_small_molecule"),
    "predict_mrna_stability_with_rnastop": ("rnastop_stability", "ranking_objective", "full_length_mrna"),
    "predict_putative_ires_with_iresfinder": ("iresfinder_score", "screening_evaluation", "ires_prediction"),
}

# Remaining E16+ backlog: no labeled anchor set exists on disk (DECISIONS.md
# (l)); reviewed and audited, never blocked until their campaigns deliver.
EXPECTED_PENDING_ORACLES = {
    "score_sgrna_handle_with_crgpt": ("crgpt_handle_score", "ranking_objective", "sgrna_design"),
    "score_crispr_off_target_with_crisot": ("crisot_off_target_score", "ranking_objective", "sgrna_design"),
}

EXPECTED_STATUS_COUNTS = {"production": 41, "experiment_only": 0, "reserved": 0, "demo": 1}


def _langchain_tool_names() -> set[str]:
    tree = ast.parse((PROJECT_ROOT / "agent_core" / "tools.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "tool":
                    names.add(node.name)
    return names


def test_every_langchain_tool_has_a_spec_with_kind() -> None:
    from agent_core.tool_specs import TOOL_SPECS

    tool_names = _langchain_tool_names()
    assert len(tool_names) == 42
    assert set(TOOL_SPECS) == tool_names, "tools.py @tool set and TOOL_SPECS keys drifted"
    for name, spec in TOOL_SPECS.items():
        assert isinstance(spec.kind, ToolKind), f"{name}: kind not set"


def test_oracle_descriptor_sets_are_pinned() -> None:
    from agent_core.tool_specs import TOOL_SPECS

    enforced: dict[str, tuple[str, str, str]] = {}
    pending: dict[str, tuple[str, str, str]] = {}
    for name, spec in TOOL_SPECS.items():
        if spec.oracle is None:
            continue
        assert isinstance(spec.oracle, OracleDescriptor)
        assert spec.kind == ToolKind.predictor, f"{name}: oracle descriptor on non-predictor kind"
        triple = (spec.oracle.oracle_id, spec.oracle.evidence_use.value, spec.oracle.default_task_type)
        if spec.oracle.governance.value == "enforce":
            enforced[name] = triple
        else:
            pending[name] = triple
    assert enforced == EXPECTED_ENFORCED_ORACLES
    assert pending == EXPECTED_PENDING_ORACLES


def test_runtime_managed_set_derives_from_specs() -> None:
    from agent_core.calibrated.runtime import MANAGED_ORACLE_TOOLS, ORACLE_GOVERNANCE
    from agent_core.tool_specs import TOOL_SPECS

    expected = {n: (s.oracle.oracle_id, s.oracle.default_task_type, s.oracle.evidence_use.value)
                for n, s in TOOL_SPECS.items() if s.oracle is not None}
    assert MANAGED_ORACLE_TOOLS == expected
    assert set(ORACLE_GOVERNANCE) == set(expected)
    assert sum(1 for g in ORACLE_GOVERNANCE.values() if g == "enforce") == len(EXPECTED_ENFORCED_ORACLES)
    assert sum(1 for g in ORACLE_GOVERNANCE.values() if g == "pending") == len(EXPECTED_PENDING_ORACLES)


def test_pending_oracles_reviewed_but_never_blocked(tmp_path: Path) -> None:
    from agent_core.calibrated.runtime import CalibratedRuntime

    runtime = CalibratedRuntime.configure(audit_path=tmp_path / "audit.jsonl", policy="enforce")
    try:
        # Enforced oracle with failed evidence under the default SelfModel blocks.
        decision = runtime.review_tool_call("score_rna_protein_complex_with_egarps")
        assert decision is not None and decision.verdict == "reject"
        assert runtime.should_block(decision, "score_rna_protein_complex_with_egarps")

        # Pending oracles are reviewed (verdict recorded/audited) but never blocked.
        for name in EXPECTED_PENDING_ORACLES:
            decision = runtime.review_tool_call(name)
            assert decision is not None, f"{name}: pending oracle not reviewed"
            assert not runtime.should_block(decision, name), f"{name}: pending oracle must not block"

        # Non-oracle tools are untouched by the gate.
        assert runtime.review_tool_call("compute_rna_sequence_gc_content") is None
    finally:
        CalibratedRuntime.clear()


def test_inventory_statuses_complete_and_pinned() -> None:
    from agent_core.tool_inventory import DEMO_TOOLS, RESERVED_TOOLS, build_inventory

    manifest = build_inventory()  # raises InventoryError on unclassified tools
    assert manifest["summary"]["total_tools"] == 42
    assert manifest["summary"]["status"] == EXPECTED_STATUS_COUNTS

    by_status: dict[str, set[str]] = {}
    for tool in manifest["tools"]:
        by_status.setdefault(tool["status"], set()).add(tool["name"])

    assert by_status["demo"] == set(DEMO_TOOLS)
    assert by_status.get("reserved", set()) == set(RESERVED_TOOLS)
    assert by_status.get("experiment_only", set()) == set()
    # Every reserved tool genuinely lacks a production caller.
    for tool in manifest["tools"]:
        if tool["status"] == "reserved":
            assert not tool["production_callers"], f"{tool['name']} reserved but has production callers"


def test_unclassified_tool_raises_inventory_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import agent_core.tool_inventory as inv
    from agent_core.tool_specs import TOOL_SPECS

    victim = "compute_rna_sequence_u_content"  # production tool; simulate losing all callers
    real_prod = inv.production_callers
    monkeypatch.setattr(
        inv, "production_callers",
        lambda names: {n: ([] if n == victim else real_prod(names)[n]) for n in names},
    )
    with pytest.raises(inv.InventoryError, match=victim):
        inv.build_inventory()
    # appease linters about unused import anchor
    assert TOOL_SPECS is not None
