"""Tests for FormValidator."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field
from typing import Literal, Optional, List

from agent_core.form import FormValidator, FormSchemaBuilder


class DemoInput(BaseModel):
    name: str = Field(..., description="Name")
    age: int = Field(default=0, description="Age")
    score: float = Field(default=0.0, description="Score")
    active: bool = Field(default=False, description="Active")
    mode: Literal["a", "b"] = Field(default="a", description="Mode")
    tags: List[str] = Field(default_factory=list, description="Tags")
    seeds: List[int] = Field(default_factory=list, description="Seeds")
    meta: Optional[dict] = Field(default=None, description="Meta")


def test_validate_with_model_success():
    raw = {
        "name": "test",
        "age": "30",
        "score": "98.5",
        "active": "true",
        "mode": "b",
        "tags": "a, b, c",
        "seeds": "[1, 2, 3]",
        "meta": '{"key": "value"}',
    }
    params, errors = FormValidator.validate_with_model(DemoInput, raw)
    assert not errors
    assert params["name"] == "test"
    assert params["age"] == 30
    assert params["score"] == 98.5
    assert params["active"] is True
    assert params["mode"] == "b"
    assert params["tags"] == ["a", "b", "c"]
    assert params["seeds"] == [1, 2, 3]
    assert params["meta"] == {"key": "value"}


def test_validate_with_model_required_missing():
    raw = {"age": "30"}
    params, errors = FormValidator.validate_with_model(DemoInput, raw)
    assert errors
    assert any("name" in e for e in errors)


def test_validate_with_model_invalid_int():
    raw = {"name": "test", "age": "not_a_number"}
    params, errors = FormValidator.validate_with_model(DemoInput, raw)
    assert errors
    assert any("age" in e for e in errors)


def test_empty_string_becomes_none():
    schema = FormSchemaBuilder.from_pydantic_model("demo", DemoInput)
    raw = {"name": "test", "meta": "   "}
    coerced, _ = FormValidator.validate(schema, raw)
    assert coerced["meta"] is None


def test_validate_against_real_workflow():
    from agent_core.workflows.rna_small_molecule_interaction import RnaSmallMoleculeInteractionInput
    raw = {
        "rna_sequence": "AUGC",
        "smiles": "CCO",
        "scoring_tools": "[\"rnasmol\"]",
    }
    params, errors = FormValidator.validate_with_model(RnaSmallMoleculeInteractionInput, raw)
    assert not errors
    assert params["rna_sequence"] == "AUGC"
    assert params["smiles"] == "CCO"
    assert params["scoring_tools"] == ["rnasmol"]
