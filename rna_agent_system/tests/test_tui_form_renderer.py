"""Tests for TuiFormRenderer using Textual's pilot."""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual", reason="textual is an optional TUI dependency")

from textual.widgets import TextArea

from agent_core.form import FormSchemaBuilder
from agent_core.form.renderer import FormApp
from agent_core.workflows.rna_small_molecule_interaction import RnaSmallMoleculeInteractionInput


@pytest.mark.anyio
async def test_form_app_submits_params():
    schema = FormSchemaBuilder.from_pydantic_model(
        "rna_small_molecule_interaction", RnaSmallMoleculeInteractionInput
    )
    app = FormApp(schema, prefilled={})
    async with app.run_test() as pilot:
        # Set widget values directly; pilot typing into TextArea is brittle.
        app.query_one("#field-rna_sequence", TextArea).text = "AUGCAUGC"
        app.query_one("#field-smiles", TextArea).text = "CCO"
        await pilot.click("#submit")
        await pilot.pause()

    result = app._result
    assert result["rna_sequence"] == "AUGCAUGC"
    assert result["smiles"] == "CCO"
    assert result["scoring_tools"] is not None
