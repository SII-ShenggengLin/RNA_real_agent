"""Tests for FormSchemaBuilder."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field
from typing import Literal, Optional, List

from agent_core.form import FormSchemaBuilder


class DemoInput(BaseModel):
    protein_sequence: str = Field(..., description="Amino-acid string")
    design_tool: Literal["a", "b", "all"] = Field(default="all", description="Tool")
    lambda_value: Optional[float] = Field(default=None, description="Lambda")
    vienna_fold_temp_c: float = Field(default=37.0, description="Temperature")
    custom_flag: bool = Field(
        default=False,
        description="Custom flag",
        json_schema_extra={"ui_group": "advanced"},
    )


def test_build_schema_basic_fields():
    schema = FormSchemaBuilder.from_pydantic_model("demo", DemoInput)
    field_map = {f.name: f for f in schema.fields}

    assert field_map["protein_sequence"].required is True
    assert field_map["protein_sequence"].type == "str"
    assert field_map["protein_sequence"].ui_group == "basic"

    assert field_map["design_tool"].type == "literal"
    assert field_map["design_tool"].choices == ["a", "b", "all"]
    assert field_map["design_tool"].ui_group == "basic"

    assert field_map["lambda_value"].type == "float"
    assert field_map["lambda_value"].required is False
    assert field_map["lambda_value"].default is None


def test_advanced_prefix_default():
    schema = FormSchemaBuilder.from_pydantic_model("demo", DemoInput)
    field_map = {f.name: f for f in schema.fields}
    assert field_map["vienna_fold_temp_c"].ui_group == "advanced"


def test_explicit_ui_group_override():
    schema = FormSchemaBuilder.from_pydantic_model("demo", DemoInput)
    field_map = {f.name: f for f in schema.fields}
    assert field_map["custom_flag"].ui_group == "advanced"


def test_all_workflow_models_build():
    """Smoke test: every registered workflow must produce a FormSchema."""
    from agent_core.runner import AgentRunner
    from agent_core.tool_executor import ToolExecutor
    from agent_core.tool_executor import build_default_tool_registry

    runner = AgentRunner(
        executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
    )
    for wf_name, wf in runner.workflow_registry.items():
        if not hasattr(wf, "input_model") or wf.input_model is None:
            continue
        schema = FormSchemaBuilder.from_pydantic_model(wf_name, wf.input_model)
        assert schema.workflow == wf_name
        assert schema.fields
        basic = [f for f in schema.fields if f.ui_group == "basic"]
        advanced = [f for f in schema.fields if f.ui_group == "advanced"]
        assert basic, f"{wf_name}: no basic fields"
        for f in schema.fields:
            assert f.type in {"str", "int", "float", "bool", "literal", "list", "dict", "file"}
