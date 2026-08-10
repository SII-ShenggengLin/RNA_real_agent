"""Tests for BindingResolver."""

from __future__ import annotations

import pytest

from agent_core.pipeline.binding_resolver import BindingResolutionError, BindingResolver
from agent_core.workflow_models import Candidate, WorkflowResult


def _make_result(sequence: str) -> WorkflowResult:
    candidate = Candidate(sequence=sequence, source="test")
    return WorkflowResult(
        success=True,
        task_id="t1",
        best_candidate=candidate,
        all_candidates=[candidate],
        summary="ok",
    )


def test_resolve_best_candidate_sequence() -> None:
    results = {"cds": _make_result("AUGCGC")}
    resolver = BindingResolver(results)
    assert resolver.resolve("$cds.best_candidate.sequence") == "AUGCGC"


def test_resolve_with_alias() -> None:
    results = {"cds": _make_result("AUGCGC")}
    resolver = BindingResolver(results, alias_to_node_id={"my_cds": "cds"})
    assert resolver.resolve("$my_cds.best_candidate.sequence") == "AUGCGC"


def test_resolve_indexed_candidate() -> None:
    results = {"cds": _make_result("AUGCGC")}
    resolver = BindingResolver(results)
    assert resolver.resolve("$cds.all_candidates[0].sequence") == "AUGCGC"


def test_resolve_dict_key() -> None:
    results = {"cds": _make_result("AUGCGC")}
    results["cds"].best_candidate.metadata["foo"] = {"bar": 42}
    resolver = BindingResolver(results)
    assert resolver.resolve("$cds.best_candidate.metadata.foo.bar") == 42


def test_resolve_params_mapping() -> None:
    results = {"cds": _make_result("AUGCGC")}
    resolver = BindingResolver(results)
    params = resolver.resolve_params({
        "rna_sequence": "$cds.best_candidate.sequence",
        "extra": "literal_value",
    })
    assert params == {"rna_sequence": "AUGCGC", "extra": "literal_value"}


def test_unknown_node() -> None:
    resolver = BindingResolver({})
    with pytest.raises(BindingResolutionError, match="unknown node/alias"):
        resolver.resolve("$cds.best_candidate.sequence")


def test_missing_attribute() -> None:
    results = {"cds": _make_result("AUGCGC")}
    resolver = BindingResolver(results)
    with pytest.raises(BindingResolutionError, match="Cannot resolve"):
        resolver.resolve("$cds.best_candidate.missing_field")


def test_index_out_of_range() -> None:
    results = {"cds": _make_result("AUGCGC")}
    resolver = BindingResolver(results)
    with pytest.raises(BindingResolutionError):
        resolver.resolve("$cds.all_candidates[5].sequence")
