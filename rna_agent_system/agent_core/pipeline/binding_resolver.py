"""Resolve input bindings of the form $node_id.field.path."""

from __future__ import annotations

import re
from typing import Any


class BindingResolutionError(ValueError):
    """Raised when an input binding cannot be resolved."""

    pass


class BindingResolver:
    """Resolve path expressions against a mapping of node results.

    Supported syntax (V1):
    - $node_id.field.subfield
    - $alias.field
    - $node_id.all_candidates[0].sequence
    - integer indexing only; slices are not implemented in V1
    """

    _INDEX_RE = re.compile(r"^([^\[]+)\[(\d+)\]$")

    def __init__(self, node_results: dict[str, Any], alias_to_node_id: dict[str, str] | None = None):
        self.node_results = node_results
        self.alias_to_node_id = alias_to_node_id or {}

    def resolve(self, expression: str) -> Any:
        """Resolve a binding expression and return the referenced value."""
        if not isinstance(expression, str) or not expression.startswith("$"):
            return expression

        body = expression[1:]
        parts = body.split(".")
        if not parts:
            raise BindingResolutionError(f"Empty binding expression: {expression!r}")

        first_part = parts[0]
        first_part, index = self._split_index(first_part)

        node_id = self.alias_to_node_id.get(first_part, first_part)
        if node_id not in self.node_results:
            raise BindingResolutionError(
                f"Binding {expression!r} references unknown node/alias: {first_part}"
            )

        value: Any = self.node_results[node_id]
        if index is not None:
            value = self._index_value(value, index, expression)

        for part in parts[1:]:
            part, index = self._split_index(part)
            value = self._get_attr(value, part, expression)
            if index is not None:
                value = self._index_value(value, index, expression)

        return value

    def resolve_params(self, bindings: dict[str, str]) -> dict[str, Any]:
        """Resolve a mapping of parameter names to binding expressions."""
        return {key: self.resolve(expr) for key, expr in bindings.items()}

    @classmethod
    def _split_index(cls, part: str) -> tuple[str, int | None]:
        match = cls._INDEX_RE.match(part)
        if match:
            return match.group(1), int(match.group(2))
        return part, None

    def _index_value(self, value: Any, index: int, expression: str) -> Any:
        try:
            return value[index]
        except (TypeError, IndexError, KeyError) as exc:
            raise BindingResolutionError(
                f"Cannot index into value for binding {expression!r}: {exc}"
            ) from exc

    def _get_attr(self, value: Any, name: str, expression: str) -> Any:
        if value is None:
            raise BindingResolutionError(
                f"Cannot access {name!r} on None for binding {expression!r}"
            )

        # Pydantic model attribute.
        if hasattr(value, name):
            return getattr(value, name)

        # If the value is an AgentResult wrapper and the field is not on it,
        # transparently access the wrapped workflow_result.
        if hasattr(value, "workflow_result") and value.workflow_result is not None:
            inner = value.workflow_result
            if hasattr(inner, name):
                return getattr(inner, name)
            if isinstance(inner, dict) and name in inner:
                return inner[name]

        # Mapping key.
        if isinstance(value, dict) and name in value:
            return value[name]

        raise BindingResolutionError(
            f"Cannot resolve {name!r} on {type(value).__name__} for binding {expression!r}"
        )
