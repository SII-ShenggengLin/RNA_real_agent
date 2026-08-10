"""Validate and coerce raw form values against a FormSchema."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from .schema_builder import FormField, FormSchema


class FormValidator:
    """Validate form values using the workflow's Pydantic input model."""

    @staticmethod
    def validate(
        schema: FormSchema,
        raw_values: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Return (coerced_params, error_messages).

        Empty or whitespace-only strings are treated as ``None`` so that optional
        fields left blank are omitted rather than passed as empty strings.
        """
        coerced: dict[str, Any] = {}
        field_map = {f.name: f for f in schema.fields}

        for name, value in raw_values.items():
            field = field_map.get(name)
            if field is None:
                continue
            coerced[name] = FormValidator._coerce_field(field, value)

        return coerced, []

    @staticmethod
    def validate_with_model(
        model_cls: type[BaseModel],
        raw_values: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Validate values directly against a Pydantic model."""
        coerced = {k: FormValidator._coerce_value(v) for k, v in raw_values.items()}
        try:
            validated = model_cls.model_validate(coerced)
            return validated.model_dump(), []
        except ValidationError as exc:
            errors = []
            for err in exc.errors():
                loc = " -> ".join(str(x) for x in err.get("loc", []))
                errors.append(f"{loc}: {err.get('msg', 'invalid value')}")
            return coerced, errors

    @staticmethod
    def _coerce_value(value: Any) -> Any:
        """Heuristic coercion for raw string values coming from a TUI or JSON file."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float, list, dict)):
            return value
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if stripped == "":
            return None

        # JSON list / object
        if (stripped.startswith("[") and stripped.endswith("]")) or (
            stripped.startswith("{") and stripped.endswith("}")
        ):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass

        lower = stripped.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
        if lower in ("none", "null"):
            return None

        # int
        try:
            return int(stripped)
        except ValueError:
            pass

        # float
        try:
            return float(stripped)
        except ValueError:
            pass

        # Comma-separated list heuristic (only when commas are present).
        if "," in stripped:
            return [part.strip() for part in stripped.split(",") if part.strip() != ""]

        return stripped

    @staticmethod
    def _coerce_field(field: FormField, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return None
            value = stripped

        if field.type == "str" or field.type == "literal" or field.type == "file":
            return str(value)

        if field.type == "int":
            return int(value)

        if field.type == "float":
            return float(value)

        if field.type == "bool":
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes", "on")

        if field.type == "list":
            return FormValidator._coerce_list(field, value)

        if field.type == "dict":
            return FormValidator._coerce_dict(value)

        return value

    @staticmethod
    def _coerce_list(field: FormField, value: Any) -> list[Any] | None:
        if isinstance(value, list):
            items = value
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    items = parsed
                else:
                    items = [parsed]
            except json.JSONDecodeError:
                items = [v.strip() for v in value.split(",") if v.strip() != ""]
        else:
            items = [value]

        if field.item_type == "int":
            return [int(x) for x in items]
        if field.item_type == "float":
            return [float(x) for x in items]
        if field.item_type == "bool":
            return [str(x).lower() in ("true", "1", "yes", "on") for x in items]
        return [str(x) for x in items]

    @staticmethod
    def _coerce_dict(value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON object: {exc}") from exc
        raise ValueError(f"Cannot coerce {type(value).__name__} to dict")
