"""Platform tool inventory manifest — single source of truth for "which tools
exist, what they are, and who calls them" (W1.1 oracle ontology, 2026-08-18).

The manifest merges three sources:

- the ToolSpec ontology (``kind``, ``OracleDescriptor``) from
  ``agent_core/tool_specs.py``;
- the microservice mapping from ``agent_core/services/service_manager.py``;
- an AST scan of production code (workflows/agents/pipeline) and experiment
  drivers for real call sites (string literals or imports of tool names).

Completeness is enforced, not assumed: a tool with no caller anywhere and no
explicit reservation below raises ``InventoryError``.  The generated JSON is
the paper's supplementary tool table; regenerate with::

    PYTHONPATH=. python -m agent_core.tool_inventory [output.json]
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

RESERVED_TOOLS: dict[str, str] = {
    # Empty since 2026-08-18: the reserved wrappers (CRISOT suite alternates,
    # LinearFold evaluate/zuker modes, batch LinearDesign, codonw-slim) were
    # deleted together with their tools. New reservations go here.
}
_PRODUCTION_DIRS = (
    _PROJECT_ROOT / "agent_core" / "workflows",
    _PROJECT_ROOT / "agent_core" / "agents",
    _PROJECT_ROOT / "agent_core" / "pipeline",
)
_EXPERIMENT_GLOBS = (_PROJECT_ROOT / "experiments" / "**" / "*.py", _PROJECT_ROOT / "run_pa_test.py")


class InventoryError(RuntimeError):
    """A tool is unclassified: no caller and no explicit reservation."""


def _scan_files(paths: list[Path], tool_names: set[str]) -> dict[str, list[str]]:
    """Map tool name -> files that reference it (string literal or import)."""
    callers: dict[str, set[str]] = {name: set() for name in tool_names}
    for path in paths:
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in tool_names:
                found.add(node.value)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in tool_names:
                        found.add(alias.name)
        for name in found:
            callers[name].add(str(path.relative_to(_PROJECT_ROOT)))
    return {name: sorted(files) for name, files in callers.items()}


def _collect_paths(globs: tuple[Any, ...]) -> list[Path]:
    paths: list[Path] = []
    for pattern in globs:
        p = Path(pattern)
        if p.is_file():
            paths.append(p)
        else:
            paths.extend(p.parent.glob(p.name) if p.parent.exists() else [])
    return paths


def production_callers(tool_names: set[str]) -> dict[str, list[str]]:
    files: list[Path] = []
    for d in _PRODUCTION_DIRS:
        if d.exists():
            files.extend(sorted(d.glob("*.py")))
    files = [f for f in files if f.name != "__init__.py"]
    return _scan_files(files, tool_names)


def experiment_callers(tool_names: set[str]) -> dict[str, list[str]]:
    files: list[Path] = []
    experiment_dir = _PROJECT_ROOT / "experiments"
    if experiment_dir.exists():
        files.extend(sorted(experiment_dir.glob("**/*.py")))
    pa = _PROJECT_ROOT / "run_pa_test.py"
    if pa.exists():
        files.append(pa)
    return _scan_files([f for f in files if "__pycache__" not in f.parts], tool_names)


def build_inventory() -> dict[str, Any]:
    """Build the full inventory manifest; raises ``InventoryError`` on gaps."""
    from agent_core.services.service_manager import CAPABILITY_SERVICE_MAP
    from agent_core.tool_specs import TOOL_SPECS

    tool_names = set(TOOL_SPECS)
    prod = production_callers(tool_names)
    exp = experiment_callers(tool_names)

    tools: list[dict[str, Any]] = []
    for name, spec in sorted(TOOL_SPECS.items()):
        if prod.get(name):
            status = "production"
        elif exp.get(name):
            status = "experiment_only"
        elif name in RESERVED_TOOLS:
            status = "reserved"
        else:
            raise InventoryError(
                f"tool {name!r} has no caller in production or experiment code and no "
                "explicit reservation in RESERVED_TOOLS; wire it, reserve it, or remove it"
            )
        service = CAPABILITY_SERVICE_MAP.get(name)
        tools.append(
            {
                "name": name,
                "display_name": spec.display_name,
                "kind": spec.kind.value,
                "oracle": (
                    {
                        "oracle_id": spec.oracle.oracle_id,
                        "evidence_use": spec.oracle.evidence_use.value,
                        "governance": spec.oracle.governance.value,
                        "default_task_type": spec.oracle.default_task_type,
                    }
                    if spec.oracle is not None
                    else None
                ),
                "service": (
                    {"host": service.host, "port": service.port}
                    if service is not None
                    else None
                ),
                "status": status,
                "reserved_reason": RESERVED_TOOLS.get(name),
                "production_callers": prod.get(name, []),
                "experiment_callers": exp.get(name, []),
            }
        )

    status_counts = {s: sum(1 for t in tools if t["status"] == s) for s in ("production", "experiment_only", "reserved")}
    kind_counts: dict[str, int] = {}
    for t in tools:
        kind_counts[t["kind"]] = kind_counts.get(t["kind"], 0) + 1
    return {
        "schema_version": "tool_inventory_v1",
        "summary": {
            "total_tools": len(tools),
            "scientific_tools": len(tools),
            "status": status_counts,
            "kind": kind_counts,
            "service_backed": sum(1 for t in tools if t["service"] is not None),
        },
        "tools": tools,
    }


def write_manifest(path: str | Path) -> Path:
    manifest = build_inventory()
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else _PROJECT_ROOT / "experiments" / "results" / "tool_inventory.json"
    out = write_manifest(target)
    summary = build_inventory()["summary"]
    print(json.dumps(summary, indent=2))
    print(f"manifest written: {out}")
