"""Minimal LangChain-tool registry by name.

The graph in ``nodes.py`` historically used ``TOOLS_BY_NAME`` built from the same tool list.
This module provides an explicit registry API without replacing ``TOOL_SPECS``.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, MutableMapping, Optional


class ToolNotRegisteredError(KeyError):
    """Raised when lookup by tool name finds no registered tool."""

    def __init__(self, tool_name: str):
        super().__init__(tool_name)
        self.tool_name = tool_name


def _tool_name(tool: Any) -> str:
    """Resolve LangChain tool identity (``.name``)."""

    name = getattr(tool, "name", None)
    if isinstance(name, str) and name:
        return name
    raise ValueError(f"Registered object has no usable .name attribute: {type(tool)!r}")


class ToolRegistry:
    """Register LangChain-compatible tools or any callable exposing ``.invoke(dict)``.

    Typical entries are LangChain ``@tool`` wrappers from ``agent_core.tools``.
    """

    def __init__(self, initial: Optional[MutableMapping[str, Any]] = None):
        self._tools: MutableMapping[str, Any] = dict(initial or {})

    def register(self, tool: Any, *, name: Optional[str] = None) -> None:
        """Register ``tool`` under ``name``, or its LangChain ``.name``."""

        resolved = name or _tool_name(tool)
        self._tools[resolved] = tool

    def register_many(self, tools: Iterable[Any]) -> None:
        """Register multiple tools."""

        for tool in tools:
            self.register(tool)

    def unregister(self, name: str) -> None:
        """Remove a registration."""

        del self._tools[name]

    def get(self, name: str) -> Any:
        """Return tool by name or raise ``ToolNotRegisteredError``."""

        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotRegisteredError(name) from exc

    def has(self, name: str) -> bool:
        """Return True if ``name`` is registered."""

        return name in self._tools

    def list_names(self) -> list[str]:
        """Alphabetically sorted registered names."""

        return sorted(self._tools.keys())

    def snapshot(self) -> Mapping[str, Any]:
        """Read-only mapping view (copy)."""

        return dict(self._tools)
