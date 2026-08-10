"""Shared utilities for RNA agent microservices.

Eliminates copy-paste duplication of path-resolution, sequence-normalization,
subprocess-running, and FastAPI boilerplate across service modules.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional, Tuple

from fastapi import FastAPI, HTTPException


def get_rna_agent_system_root(caller_file: str = __file__, depth: int = 2) -> Path:
    """Return the ``rna_agent_system/`` directory from a microservice ``main.py``.

    *caller_file* should be ``__file__`` from the calling module.
    *depth* defaults to 2 because ``main.py`` lives at
    ``rna_agent_system/microservices/<svc>/main.py``.
    """
    return Path(caller_file).resolve().parents[depth]


# ──────────────────────────────────────────────────────────────────────────────
# Path resolution
# ──────────────────────────────────────────────────────────────────────────────


def resolve_host_path(raw: str, project_root: Path) -> Path:
    """Resolve repo-relative or absolute paths as seen from the Linux server.

    This is the functional equivalent of the inline ``_resolve_host_path``
    copies found in nearly every microservice.
    """
    text = raw.strip().strip('"').strip("'")
    p = Path(text).expanduser()
    if p.is_absolute():
        return p.resolve()

    root_name = project_root.name
    if text.startswith(f"{root_name}/"):
        text = text[len(f"{root_name}/"):]

    candidate = (project_root / text).resolve()
    if candidate.exists() or candidate.parent.exists():
        return candidate
    return Path(text).resolve()


# ──────────────────────────────────────────────────────────────────────────────
# Sequence normalization
# ──────────────────────────────────────────────────────────────────────────────


def normalize_rna_sequence(raw: str) -> str:
    """Extract sequence from plain or FASTA text; normalize to RNA uppercase."""
    lines = [
        ln.strip()
        for ln in raw.splitlines()
        if ln.strip() and not ln.lstrip().startswith(">")
    ]
    merged = "".join(lines).upper().replace("T", "U")
    return re.sub(r"[^AUGC]", "", merged)


def fasta_from_sequence_text(raw: str, default_id: str = "query", rna_mode: bool = False) -> str:
    """Build a one-entry FASTA from plain or FASTA-like text.

    If *rna_mode* is ``False`` (the default) RNA ``U`` is converted to DNA ``T``
    for blastn compatibility.
    """
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.lstrip().startswith(">")]
    seq = "".join(lines).upper()
    if not rna_mode:
        seq = seq.replace("U", "T")
        seq = re.sub(r"[^ACGTN]", "", seq)
    else:
        seq = seq.replace("T", "U")
        seq = re.sub(r"[^AUGC]", "", seq)
    if not seq:
        raise ValueError("No nucleotide letters found in query after normalization.")
    header_lines = [ln for ln in raw.splitlines() if ln.strip().startswith(">")]
    header = header_lines[0].lstrip(">").strip() if header_lines else default_id
    return f">{header}\n{seq}\n"


# ──────────────────────────────────────────────────────────────────────────────
# Binary / subprocess helpers
# ──────────────────────────────────────────────────────────────────────────────


def require_binary(name: str) -> str:
    """Return the absolute path to *name* or raise ``HTTPException(503)``."""
    path = shutil.which(name)
    if not path:
        raise HTTPException(status_code=503, detail=f"{name} not found in PATH.")
    return path


def run_subprocess(
    cmd: list[str],
    *,
    stdin: Optional[str] = None,
    cwd: Optional[Path] = None,
    timeout: Optional[float] = None,
    check: bool = True,
) -> Tuple[str, str, int]:
    """Run a subprocess and return ``(stdout, stderr, returncode)``.

    If *check* is ``True`` and the return code is non-zero, raises
    :exc:`RuntimeError` with stderr included.
    """
    proc = subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"Command failed (exit {proc.returncode}): {err}")
    return proc.stdout, proc.stderr, proc.returncode


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI factory
# ──────────────────────────────────────────────────────────────────────────────


def create_service_app(
    title: str,
    description: str,
    version: str,
) -> FastAPI:
    """Create a standard :class:`FastAPI` app for a microservice."""
    return FastAPI(title=title, description=description, version=version)


def health_response(
    status: str,
    **extras: Any,
) -> dict[str, Any]:
    """Standardise health-endpoint payload."""
    return {"status": status, **extras}


# ──────────────────────────────────────────────────────────────────────────────
# Error-handling decorator
# ──────────────────────────────────────────────────────────────────────────────


def endpoint_errors(
    detail_prefix: str = "",
    runtime_status: int = 503,
    validation_status: int = 400,
):
    """Decorator that catches common exceptions and maps them to ``HTTPException``.

    Usage::

        @app.post("/fold")
        @endpoint_errors(detail_prefix="Fold failed")
        def fold(payload: FoldRequest) -> FoldResponse:
            ...
    """
    import inspect
    import typing

    def decorator(fn):
        # Resolve annotations in the *original* module's namespace so FastAPI
        # doesn't try to evaluate string forward refs in service_kit's globals.
        try:
            hints = typing.get_type_hints(fn)
        except Exception:
            hints = getattr(fn, "__annotations__", {}) or {}

        sig = inspect.signature(fn)
        # Rebuild parameters with resolved annotations so inspect.signature
        # returns actual types instead of strings.
        new_params = [
            param.replace(annotation=hints.get(name, param.annotation))
            for name, param in sig.parameters.items()
        ]
        new_sig = sig.replace(
            parameters=new_params,
            return_annotation=hints.get("return", sig.return_annotation),
        )

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except ValueError as exc:
                raise HTTPException(status_code=validation_status, detail=str(exc)) from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=runtime_status, detail=str(exc)) from exc
            except Exception as exc:
                prefix = f"{detail_prefix}: " if detail_prefix else ""
                raise HTTPException(
                    status_code=500, detail=f"{prefix}{exc}"
                ) from exc

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        wrapper.__module__ = fn.__module__
        wrapper.__qualname__ = fn.__qualname__
        wrapper.__signature__ = new_sig
        wrapper.__annotations__ = hints
        return wrapper
    return decorator



