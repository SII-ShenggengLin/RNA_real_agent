"""Form-based workflow parameter input layer."""

from .schema_builder import FormField, FormSchema, FormSchemaBuilder
from .validator import FormValidator

__all__ = [
    "FormField",
    "FormSchema",
    "FormSchemaBuilder",
    "FormValidator",
    "TuiFormRenderer",
]


def __getattr__(name: str):
    """Lazy import for TUI renderer so non-interactive CLI avoids ``textual``."""
    if name == "TuiFormRenderer":
        from .renderer import TuiFormRenderer

        return TuiFormRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
