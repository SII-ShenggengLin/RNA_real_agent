"""TUI form renderer based on Textual."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Checkbox, Collapsible, Input, Label, Select, Static, TextArea

from .schema_builder import FormField, FormSchema


class FormApp(App[dict[str, Any]]):
    """Textual app that renders a workflow parameter form."""

    CSS = """
    Screen { align: center middle; }
    #form-container {
        width: 95%;
        height: 95%;
        border: solid $primary;
        padding: 1 2;
    }
    #title { text-align: center; text-style: bold; margin-bottom: 1; }
    #subtitle { text-align: center; color: $text-muted; margin-bottom: 1; }
    .field-label { margin-top: 1; margin-bottom: 0; }
    .field-description { color: $text-muted; margin-bottom: 1; }
    .field-widget { width: 100%; }
    .sequence-area { height: 6; }
    .json-area { height: 4; }
    #button-bar { height: auto; margin-top: 2; }
    #button-bar Button { margin-right: 2; }
    """

    def __init__(
        self,
        schema: FormSchema,
        prefilled: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.schema = schema
        self.prefilled = prefilled or {}
        self._result: dict[str, Any] | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="form-container"):
            yield Static(self.schema.workflow_title, id="title")
            yield Static(f"Workflow: {self.schema.workflow}", id="subtitle")

            basic_fields = [f for f in self.schema.fields if f.ui_group == "basic"]
            advanced_fields = [f for f in self.schema.fields if f.ui_group == "advanced"]

            with ScrollableContainer():
                for field in basic_fields:
                    yield from self._render_field(field)

                if advanced_fields:
                    with Collapsible(title="▶ 高级参数", collapsed=True):
                        for field in advanced_fields:
                            yield from self._render_field(field)

            with Horizontal(id="button-bar"):
                yield Button("提交 (Ctrl+S)", id="submit", variant="primary")
                yield Button("取消 (Ctrl+C)", id="cancel", variant="error")
                yield Button("重置 (Ctrl+R)", id="reset")

    def _render_field(self, field: FormField) -> ComposeResult:
        yield Label(field.name, classes="field-label")
        if field.description:
            yield Static(field.description, classes="field-description")

        widget_id = f"field-{field.name}"
        value = self.prefilled.get(field.name, field.default)

        if self._is_sequence_field(field):
            text = "" if value is None else str(value)
            yield TextArea(text=text, id=widget_id, classes="field-widget sequence-area")
        elif field.type == "str" or field.type == "file":
            text = "" if value is None else str(value)
            yield Input(value=text, placeholder=field.file_type_hint or "", id=widget_id, classes="field-widget")
        elif field.type == "int" or field.type == "float":
            text = "" if value is None else str(value)
            yield Input(value=text, id=widget_id, classes="field-widget")
        elif field.type == "bool":
            checked = bool(value) if value is not None else False
            yield Checkbox(field.name, value=checked, id=widget_id, classes="field-widget")
        elif field.type == "literal":
            options = [(choice, choice) for choice in (field.choices or [])]
            value = value if value is not None else field.default
            yield Select(options, value=value, id=widget_id, classes="field-widget")
        elif field.type in ("list", "dict"):
            text = self._encode_complex(value)
            yield TextArea(text=text, id=widget_id, classes="field-widget json-area")
        else:
            text = "" if value is None else str(value)
            yield Input(value=text, id=widget_id, classes="field-widget")

    @staticmethod
    def _is_sequence_field(field: FormField) -> bool:
        sequence_names = {
            "protein_sequence",
            "rna_sequence",
            "target_sequence",
            "sequence",
            "sequences",
            "target_structure",
            "secondary_structure",
            "start_sequence",
            "smiles",
            "crgpt_design_seed_sequence",
            "crisot_target_sequence",
            "seed_sequence",
            "guide_sequence",
        }
        if field.name in sequence_names:
            return True
        lowered = (field.name + " " + field.description).lower()
        return "sequence" in lowered or "structure" in lowered or "smiles" in lowered

    @staticmethod
    def _encode_complex(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, dict)):
            import json

            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "submit":
            self._submit()
        elif button_id == "cancel":
            self._result = {}
            self.exit(self._result)
        elif button_id == "reset":
            self._reset()

    def _submit(self) -> None:
        result: dict[str, Any] = {}
        for field in self.schema.fields:
            widget_id = f"field-{field.name}"
            try:
                widget = self.query_one(f"#{widget_id}")
            except Exception:
                continue
            value = self._read_widget(widget, field)
            result[field.name] = value
        self._result = result
        self.exit(self._result)

    def _read_widget(self, widget: Any, field: FormField) -> Any:
        if isinstance(widget, TextArea):
            text = widget.text
            return text if text != "" else None
        if isinstance(widget, Input):
            text = widget.value
            return text if text != "" else None
        if isinstance(widget, Checkbox):
            return widget.value
        if isinstance(widget, Select):
            value = widget.value
            if value == Select.BLANK:
                return None
            return value
        return None

    def _reset(self) -> None:
        for field in self.schema.fields:
            widget_id = f"field-{field.name}"
            try:
                widget = self.query_one(f"#{widget_id}")
            except Exception:
                continue
            value = field.default
            if isinstance(widget, TextArea):
                widget.text = "" if value is None else str(value)
            elif isinstance(widget, Input):
                widget.value = "" if value is None else str(value)
            elif isinstance(widget, Checkbox):
                widget.value = bool(value) if value is not None else False
            elif isinstance(widget, Select):
                widget.value = value if value is not None else Select.BLANK

    def action_submit(self) -> None:
        self._submit()

    def action_cancel(self) -> None:
        self._result = {}
        self.exit(self._result)


class TuiFormRenderer:
    """Render a FormSchema as a Textual TUI and return the user input."""

    @staticmethod
    def render(schema: FormSchema, prefilled: dict[str, Any] | None = None) -> dict[str, Any]:
        app = FormApp(schema, prefilled=prefilled or {})
        return app.run()
