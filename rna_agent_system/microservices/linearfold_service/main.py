"""LinearFold RNA secondary-structure prediction microservice.

Upstream: https://github.com/LinearFold/LinearFold
This service directly invokes the upstream C++ binaries
(``bin/linearfold_c`` and ``bin/linearfold_v``) to avoid being limited by the
thin Python wrapper script, thereby exposing the full upstream capability set.

═══════════════════════════════════════════════════════════════════════════════
LinearFold INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
═══════════════════════════════════════════════════════════════════════════════
关联文件清单（修改时必须全部同步）：
  - microservices/linearfold_service/main.py  ← 本文件
  - agent_core/tools.py :: LinearFoldSecondaryInput / LinearFoldEvalInput /
                           LinearFoldZukerSuboptInput /
                           predict_rna_secondary_structure_with_linearfold /
                           evaluate_rna_structure_with_linearfold /
                           predict_rna_secondary_structure_with_linearfold_zuker
  - agent_core/tool_specs.py :: LinearFoldOutput / LinearFoldEvalOutput /
                                LinearFoldZukerSuboptOutput /
                                predict_rna_secondary_structure_with_linearfold /
                                evaluate_rna_structure_with_linearfold /
                                predict_rna_secondary_structure_with_linearfold_zuker
                                ToolSpec entries
                           _build_linearfold_eval_tool_args /
                           _build_linearfold_zuker_tool_args
  - docs/tools/predict_rna_secondary_structure_with_linearfold.md
  - docs/workflows/rna_secondary_structure_linearfold_workflow.md
  - docs/tasks/rna_secondary_structure_linearfold.md
  - rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md
规则：任何字段增删、端点路径/签名变动、返回值结构调整、C++ 二进制调用方式
      变更，必须同时更新上述全部文件并重新跑通端到端测试。违反此规则的提交
      将被回退。
本次修改的基准日期：2026-04-25。
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from microservices.service_kit import (
    create_service_app,
    endpoint_errors,
    get_rna_agent_system_root,
    health_response,
    normalize_rna_sequence,
    run_subprocess,
)

APP_DIR = Path(__file__).resolve().parent
_RNA_AGENT_SYSTEM_ROOT = get_rna_agent_system_root(str(APP_DIR / "main.py"), depth=2)

# Regex for a structure + energy line, e.g. "....((..)).... (-3.50)"
_STRUCTURE_LINE = re.compile(r"^([.()]+)\s+\(\s*(-?\d+(?:\.\d+)?)\s*\)\s*$")


def _canonical_linearfold_root() -> Path:
    return (_RNA_AGENT_SYSTEM_ROOT / "external_repos" / "LinearFold").resolve()


def _resolve_linearfold_root() -> Path:
    override = os.environ.get("LINEARFOLD_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _canonical_linearfold_root()


def _linearfold_binaries_exist(root: Path) -> Tuple[bool, str]:
    c = root / "bin" / "linearfold_c"
    v = root / "bin" / "linearfold_v"
    if not c.is_file() or not v.is_file():
        return False, f"Missing {c} or {v}; run `make` under {root}."
    return True, "ok"


def _build_cmd(
    root: Path,
    *,
    beam_size: int = 100,
    use_vienna: bool = False,
    sharpturn: bool = False,
    verbose: bool = False,
    is_eval: bool = False,
    constraints: bool = False,
    zuker: bool = False,
    delta: float = 5.0,
    shape_file_path: str = "",
    fasta: bool = False,
    dangles: int = 2,
) -> List[str]:
    ok, msg = _linearfold_binaries_exist(root)
    if not ok:
        raise RuntimeError(msg)
    binary = root / ("bin/linearfold_v" if use_vienna else "bin/linearfold_c")
    return [
        str(binary),
        str(beam_size),
        "1" if sharpturn else "0",
        "1" if verbose else "0",
        "1" if is_eval else "0",
        "1" if constraints else "0",
        "1" if zuker else "0",
        str(delta),
        shape_file_path,
        "1" if fasta else "0",
        str(dangles),
    ]


def _run(cmd: List[str], stdin: str, cwd: Path) -> str:
    stdout, _, _ = run_subprocess(cmd, stdin=stdin, cwd=cwd, timeout=600)
    return stdout


def _parse_fold_stdout(stdout: str) -> Tuple[str, float, str]:
    lines = [ln.rstrip() for ln in stdout.splitlines() if ln.strip()]
    seq = ""
    structure = ""
    mfe = 0.0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.fullmatch(r"[AUGC]+", line.upper()):
            seq = line.upper()
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            m = _STRUCTURE_LINE.match(nxt)
            if m:
                if re.fullmatch(r"[AUGC]+", line.upper()) or re.fullmatch(r"[?.()]+", line):
                    structure = m.group(1)
                    mfe = float(m.group(2))
                    i += 2
                    continue
        i += 1
    if not structure:
        raise ValueError(
            "Could not parse LinearFold output; expected sequence line followed by "
            "'dot-bracket (energy)'."
        )
    return structure, mfe, seq


def _parse_zuker_stdout(stdout: str) -> Tuple[List[Tuple[str, float]], str]:
    lines = [ln.rstrip() for ln in stdout.splitlines() if ln.strip()]
    seq = ""
    structures: List[Tuple[str, float]] = []
    for line in lines:
        line = line.strip()
        if re.fullmatch(r"[AUGC]+", line.upper()) and not seq:
            seq = line.upper()
            continue
        if "Zuker suboptimal structures" in line:
            continue
        m = _STRUCTURE_LINE.match(line)
        if m:
            structures.append((m.group(1), float(m.group(2))))
    if not structures:
        raise ValueError("Could not parse Zuker suboptimal output.")
    return structures, seq


def _parse_eval_stdout(stdout: str) -> Tuple[float, str, Optional[str]]:
    lines = [ln.rstrip() for ln in stdout.splitlines() if ln.strip()]
    seq = ""
    energy = 0.0
    verbose_lines: List[str] = []
    structure_line_idx = -1
    for idx in range(len(lines) - 1, -1, -1):
        m = _STRUCTURE_LINE.match(lines[idx].strip())
        if m:
            structure_line_idx = idx
            energy = float(m.group(2))
            break
    if structure_line_idx < 0:
        raise ValueError("Could not parse LinearFold eval output: no structure line found.")
    if structure_line_idx > 0:
        candidate_seq = lines[structure_line_idx - 1].strip()
        if re.fullmatch(r"[AUGC]+", candidate_seq.upper()):
            seq = candidate_seq.upper()
            if structure_line_idx > 1:
                verbose_lines = lines[: structure_line_idx - 1]
        else:
            verbose_lines = lines[:structure_line_idx]
    verbose_details = "\n".join(verbose_lines) if verbose_lines else None
    return energy, seq, verbose_details


app = create_service_app(
    title="LinearFold Service (Port 8015)",
    description=(
        "Linear-time RNA secondary structure prediction via LinearFold. "
        "Exposes the full upstream surface: standard fold, constrained fold, "
        "SHAPE-guided fold, Zuker suboptimal enumeration, and energy evaluation."
    ),
    version="0.2.0",
)


# ---------------------------------------------------------------------------
# /fold — standard, constrained, or SHAPE-guided folding
# ---------------------------------------------------------------------------

class FoldRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence (plain text or FASTA body).")
    beam_size: int = Field(default=100, ge=0, le=10000, description="Beam size; 0 means infinite beam.")
    use_vienna: bool = Field(default=False, description="If true, use LinearFold-V (Vienna parameters); else LinearFold-C.")
    dangles: int = Field(default=2, description="0 or 2; passed to LinearFold --dangles.")
    sharpturn: bool = Field(default=False, description="Enable sharpturn in prediction.")
    constraints: Optional[str] = Field(
        default=None,
        description="Optional constraint string (? . ( ) ) for constrained prediction. Length must match the sequence.",
    )
    shape_file_path: Optional[str] = Field(
        default=None,
        description="Optional path to SHAPE reactivity data file. Mutually exclusive with ``constraints``.",
    )


class FoldResponse(BaseModel):
    sequence: str
    structure: str
    mfe: float
    backend: str
    model: str = "LinearFold"


@app.post("/fold", response_model=FoldResponse)
@endpoint_errors(detail_prefix="LinearFold fold failed")
def fold(payload: FoldRequest) -> FoldResponse:
    if payload.dangles not in (0, 2):
        raise ValueError("dangles must be 0 or 2.")

    root = _resolve_linearfold_root()
    sequence = normalize_rna_sequence(payload.sequence)
    if not sequence:
        raise ValueError("No RNA sequence after normalization.")

    if payload.constraints is not None and payload.shape_file_path is not None:
        raise ValueError("Cannot use constraints and SHAPE simultaneously.")

    if payload.constraints is not None:
        constraint = payload.constraints.strip()
        if len(constraint) != len(sequence):
            raise ValueError("Constraint length must match sequence length.")
        stdin = f"{sequence}\n{constraint}\n"
        is_constraints = True
    else:
        stdin = f"{sequence}\n"
        is_constraints = False

    shape_path = payload.shape_file_path or ""

    cmd = _build_cmd(
        root,
        beam_size=payload.beam_size,
        use_vienna=payload.use_vienna,
        sharpturn=payload.sharpturn,
        is_eval=False,
        constraints=is_constraints,
        zuker=False,
        delta=5.0,
        shape_file_path=shape_path,
        dangles=payload.dangles,
    )
    stdout = _run(cmd, stdin, root)
    structure, mfe, out_seq = _parse_fold_stdout(stdout)

    backend = "LinearFold-V" if payload.use_vienna else "LinearFold-C"
    return FoldResponse(
        sequence=out_seq or sequence,
        structure=structure,
        mfe=mfe,
        backend=backend,
    )


# ---------------------------------------------------------------------------
# /fold/zuker_subopt — Zuker suboptimal structures
# ---------------------------------------------------------------------------

class ZukerSuboptRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence.")
    beam_size: int = Field(default=100, ge=0, le=10000)
    use_vienna: bool = Field(default=False)
    dangles: int = Field(default=2)
    sharpturn: bool = Field(default=False)
    delta: float = Field(default=5.0, ge=0.0, description="Energy range (kcal/mol) for suboptimal structures.")


class SuboptimalStructure(BaseModel):
    structure: str
    energy: float


class ZukerSuboptResponse(BaseModel):
    sequence: str
    mfe: float
    structures: List[SuboptimalStructure]
    backend: str
    model: str = "LinearFold"


@app.post("/fold/zuker_subopt", response_model=ZukerSuboptResponse)
@endpoint_errors(detail_prefix="LinearFold Zuker subopt failed")
def zuker_subopt(payload: ZukerSuboptRequest) -> ZukerSuboptResponse:
    if payload.dangles not in (0, 2):
        raise ValueError("dangles must be 0 or 2.")

    root = _resolve_linearfold_root()
    sequence = normalize_rna_sequence(payload.sequence)
    if not sequence:
        raise ValueError("No RNA sequence after normalization.")

    cmd = _build_cmd(
        root,
        beam_size=payload.beam_size,
        use_vienna=payload.use_vienna,
        sharpturn=payload.sharpturn,
        is_eval=False,
        constraints=False,
        zuker=True,
        delta=payload.delta,
        dangles=payload.dangles,
    )
    stdout = _run(cmd, f"{sequence}\n", root)
    structures, out_seq = _parse_zuker_stdout(stdout)

    backend = "LinearFold-V" if payload.use_vienna else "LinearFold-C"
    mfe = structures[0][1] if structures else 0.0
    return ZukerSuboptResponse(
        sequence=out_seq or sequence,
        mfe=mfe,
        structures=[SuboptimalStructure(structure=s, energy=e) for s, e in structures],
        backend=backend,
    )


# ---------------------------------------------------------------------------
# /eval — evaluate free energy of a known structure
# ---------------------------------------------------------------------------

class EvalRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence.")
    structure: str = Field(..., min_length=1, description="Dot-bracket secondary structure to evaluate.")
    use_vienna: bool = Field(default=False)
    dangles: int = Field(default=2)
    verbose: bool = Field(default=False, description="Return per-loop energy decomposition.")


class EvalResponse(BaseModel):
    sequence: str
    structure: str
    energy: float
    backend: str
    model: str = "LinearFold"
    verbose_details: Optional[str] = None


@app.post("/eval", response_model=EvalResponse)
@endpoint_errors(detail_prefix="LinearFold eval failed")
def eval_structure(payload: EvalRequest) -> EvalResponse:
    if payload.dangles not in (0, 2):
        raise ValueError("dangles must be 0 or 2.")

    root = _resolve_linearfold_root()
    sequence = normalize_rna_sequence(payload.sequence)
    if not sequence:
        raise ValueError("No RNA sequence after normalization.")

    structure = payload.structure.strip()
    if len(structure) != len(sequence):
        raise ValueError("Structure length must match sequence length.")

    cmd = _build_cmd(
        root,
        use_vienna=payload.use_vienna,
        verbose=payload.verbose,
        is_eval=True,
        dangles=payload.dangles,
    )
    stdout = _run(cmd, f"{sequence}\n{structure}\n", root)
    energy, out_seq, verbose_details = _parse_eval_stdout(stdout)

    backend = "LinearFold-V" if payload.use_vienna else "LinearFold-C"
    return EvalResponse(
        sequence=out_seq or sequence,
        structure=structure,
        energy=energy,
        backend=backend,
        verbose_details=verbose_details,
    )


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str | bool]:
    root = _resolve_linearfold_root()
    ok, msg = _linearfold_binaries_exist(root)
    return health_response(
        "ok" if ok else "degraded",
        linearfold_root=str(root),
        binaries_ready=ok,
        detail=msg if not ok else "LinearFold binaries present.",
    )
