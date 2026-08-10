"""LinearDesign microservice for protein-to-mRNA CDS design.

INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
关联文件清单（修改时必须全部同步）：
  - microservices/lineardesign_service/main.py  ← 本文件
  - agent_core/tools.py :: design_mrna_cds_with_lineardesign /
                          design_mrna_cds_batch_with_lineardesign
  - agent_core/tool_specs.py :: LinearDesignCdsOutput /
                                LinearDesignCdsBatchOutput /
                                design_mrna_cds_with_lineardesign ToolSpec
  - agent_core/state.py :: lineardesign_* fields
  - docs/tools/design_mrna_cds_with_lineardesign.md
  - docs/change_logs/lineardesign_interface_v0.2.0.md
  - workflow_api/mrna_handler.py
  - workflow_api/mrna_schemas.py
规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
本次修改的基准日期：2026-04-24。
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


APP_DIR = Path(__file__).resolve().parent
# ``main.py`` lives at ``rna_agent_system/microservices/lineardesign_service/main.py``:
# parents[0] = microservices/, parents[1] = rna_agent_system/ (do NOT use parents[2] = repo root).
_RNA_AGENT_SYSTEM_ROOT = APP_DIR.parents[1]


def _canonical_lineardesign_root() -> Path:
    """Project-standard path: ``rna_agent_system/external_repos/LinearDesign``."""
    return (_RNA_AGENT_SYSTEM_ROOT / "external_repos" / "LinearDesign").resolve()


def _resolve_lineardesign_root() -> Path:
    """Resolve LinearDesign checkout: canonical path under ``rna_agent_system/external_repos/``,
    or ``LINEARDESIGN_ROOT`` when set (must contain ``bin/LinearDesign_2D`` after ``make``).
    """
    override = os.environ.get("LINEARDESIGN_ROOT", "").strip()
    if override:
        root = Path(override).expanduser().resolve()
        if (root / "bin" / "LinearDesign_2D").exists():
            return root

    canonical = _canonical_lineardesign_root()
    if (canonical / "bin" / "LinearDesign_2D").exists():
        return canonical

    return canonical


def _resolve_codon_usage_path(lineardesign_root: Path, path_value: Optional[str]) -> Path:
    default_path = lineardesign_root / "codon_usage_freq_table_human.csv"
    if not path_value:
        return default_path

    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate

    under_ld = (lineardesign_root / candidate).resolve()
    if under_ld.exists():
        return under_ld

    repo_relative = (_RNA_AGENT_SYSTEM_ROOT / candidate).resolve()
    if repo_relative.exists():
        return repo_relative

    return under_ld


def _extract_output_fields(raw_output: str) -> tuple[str, str, float, float]:
    seq_match = re.search(r"mRNA sequence:\s*([AUGC]+)", raw_output)
    structure_match = re.search(r"mRNA structure:\s*([().]+)", raw_output)
    mfe_match = re.search(r"mRNA folding free energy:\s*([-+]?\d*\.?\d+)", raw_output)
    cai_match = re.search(r"mRNA CAI:\s*([-+]?\d*\.?\d+)", raw_output)

    if not seq_match or not structure_match or not mfe_match or not cai_match:
        raise ValueError(
            "LinearDesign output parsing failed. "
            "Expected mRNA sequence, structure, MFE, and CAI fields."
        )

    return (
        seq_match.group(1).strip(),
        structure_match.group(1).strip(),
        float(mfe_match.group(1)),
        float(cai_match.group(1)),
    )


def _reject_oversized_protein(protein_sequence: str) -> None:
    """Reject proteins whose DP lattice would exceed the local memory budget.

    LinearDesign's memory grows roughly quadratically with protein length
    (~7.5 GiB measured at 500 aa, 2026-08-06). Unbounded runs of very long
    proteins previously exhausted the 200 GiB container cgroup, and the
    kernel OOM killer SIGKILLed unrelated processes. The bin/LinearDesign_2D
    wrapper caps the address space as a last resort; this guard fails fast
    with an actionable message instead of burning memory until the cap hits.
    Override via LINEARDESIGN_MAX_AA.
    """
    max_aa = int(os.environ.get("LINEARDESIGN_MAX_AA", "1800"))
    n_aa = len(protein_sequence)
    if n_aa > max_aa:
        raise RuntimeError(
            f"Protein sequence too long for LinearDesign in this environment: "
            f"{n_aa} aa > limit {max_aa} aa (memory grows ~quadratically, "
            f"~7.5 GiB at 500 aa; {n_aa} aa would exceed the 100 GiB "
            "address-space cap). Split the protein, or raise "
            "LINEARDESIGN_MAX_AA / LINEARDESIGN_MAX_RSS_KB if more memory "
            "is available."
        )


def _run_lineardesign_once(
    lineardesign_bin: Path,
    lineardesign_root: Path,
    protein_sequence: str,
    lambda_value: float,
    verbose: bool,
    codon_usage_path: Path,
    timeout_seconds: Optional[float] = None,
) -> dict[str, Any]:
    """Execute LinearDesign binary for a single protein sequence.

    Returns a dict with keys: generated_sequence, structure, mfe, cai_score,
    raw_output, stderr.
    """
    _reject_oversized_protein(protein_sequence)
    cmd = [
        str(lineardesign_bin),
        f"{lambda_value}",
        "1" if verbose else "0",
        str(codon_usage_path),
    ]
    env = os.environ.copy()
    process = subprocess.run(
        cmd,
        input=protein_sequence + "\n",
        text=True,
        capture_output=True,
        cwd=str(lineardesign_root),
        env=env,
        check=False,
        timeout=timeout_seconds,
    )

    if process.returncode != 0:
        raise RuntimeError(
            "LinearDesign execution failed. "
            f"returncode={process.returncode}; stderr={process.stderr.strip()}"
        )

    generated_sequence, structure, mfe, cai_score = _extract_output_fields(process.stdout)
    return {
        "generated_sequence": generated_sequence,
        "structure": structure,
        "mfe": mfe,
        "cai_score": cai_score,
        "raw_output": process.stdout,
        "stderr": process.stderr,
    }


app = FastAPI(
    title="LinearDesign Service (Port 8014 Deployment)",
    description="Design mRNA CDS from a protein sequence via LinearDesign.",
    version="0.2.0-port8014",
)


class LinearDesignRequest(BaseModel):
    protein_sequence: str = Field(..., min_length=1, description="Input protein sequence.")
    lambda_value: float = Field(
        default=0.0,
        ge=0.0,
        description="LinearDesign lambda balancing MFE and CAI.",
    )
    codon_usage_path: Optional[str] = Field(
        default=None,
        description="Optional codon usage CSV path. Defaults to human table in LinearDesign repo.",
    )
    verbose: bool = Field(default=False, description="Enable verbose output in LinearDesign.")


class LinearDesignResponse(BaseModel):
    generated_sequence: str
    structure: str
    mfe: float
    cai_score: float
    lambda_value: float
    codon_usage_path: str
    model: str = "LinearDesign"
    raw_output: str
    stderr: str


class LinearDesignBatchRequest(BaseModel):
    protein_sequences: list[str] = Field(
        ...,
        min_length=1,
        description="List of protein sequences to design in batch.",
    )
    lambda_value: float = Field(
        default=0.0,
        ge=0.0,
        description="LinearDesign lambda balancing MFE and CAI (applied to all sequences).",
    )
    codon_usage_path: Optional[str] = Field(
        default=None,
        description="Optional codon usage CSV path. Defaults to human table in LinearDesign repo.",
    )
    verbose: bool = Field(default=False, description="Enable verbose output in LinearDesign.")


class LinearDesignBatchItem(BaseModel):
    """Result for one sequence in a batch run."""

    success: bool
    generated_sequence: str = ""
    structure: str = ""
    mfe: float = 0.0
    cai_score: float = 0.0
    raw_output: str = ""
    stderr: str = ""
    error: str = ""


class LinearDesignBatchResponse(BaseModel):
    items: list[LinearDesignBatchItem]
    count: int
    lambda_value: float
    codon_usage_path: str
    model: str = "LinearDesign"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate/cds", response_model=LinearDesignResponse)
def generate_cds(payload: LinearDesignRequest) -> LinearDesignResponse:
    lineardesign_root = _resolve_lineardesign_root()
    lineardesign_bin = lineardesign_root / "bin" / "LinearDesign_2D"
    if not lineardesign_bin.exists():
        canonical = _canonical_lineardesign_root()
        raise HTTPException(
            status_code=500,
            detail=(
                f"LinearDesign binary not found: {lineardesign_bin}. "
                f"Expected checkout at {canonical} (run `make` there), "
                "or set LINEARDESIGN_ROOT to a directory that contains bin/LinearDesign_2D."
            ),
        )

    codon_usage_path = _resolve_codon_usage_path(lineardesign_root, payload.codon_usage_path)
    if not codon_usage_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Codon usage table not found: {codon_usage_path}",
        )

    protein_sequence = payload.protein_sequence.strip().upper()
    if not protein_sequence:
        raise HTTPException(status_code=400, detail="Protein sequence is empty.")

    # Empirical: 0.8 s/aa + 180 s buffer to match client-side timeout.
    seq_len = len(protein_sequence)
    timeout_seconds = max(300, int(seq_len * 0.8) + 180)

    try:
        result = _run_lineardesign_once(
            lineardesign_bin=lineardesign_bin,
            lineardesign_root=lineardesign_root,
            protein_sequence=protein_sequence,
            lambda_value=payload.lambda_value,
            verbose=payload.verbose,
            codon_usage_path=codon_usage_path,
            timeout_seconds=timeout_seconds,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return LinearDesignResponse(
        generated_sequence=result["generated_sequence"],
        structure=result["structure"],
        mfe=result["mfe"],
        cai_score=result["cai_score"],
        lambda_value=payload.lambda_value,
        codon_usage_path=str(codon_usage_path),
        raw_output=result["raw_output"],
        stderr=result["stderr"],
    )


@app.post("/generate/cds/batch", response_model=LinearDesignBatchResponse)
def generate_cds_batch(payload: LinearDesignBatchRequest) -> LinearDesignBatchResponse:
    """Batch design CDS for multiple protein sequences.

    Each sequence is run independently against the same lambda / codon table /
    verbose settings, mirroring the upstream ``cat FASTA_FILE | ./lineardesign``
    capability.
    """
    lineardesign_root = _resolve_lineardesign_root()
    lineardesign_bin = lineardesign_root / "bin" / "LinearDesign_2D"
    if not lineardesign_bin.exists():
        canonical = _canonical_lineardesign_root()
        raise HTTPException(
            status_code=500,
            detail=(
                f"LinearDesign binary not found: {lineardesign_bin}. "
                f"Expected checkout at {canonical} (run `make` there), "
                "or set LINEARDESIGN_ROOT to a directory that contains bin/LinearDesign_2D."
            ),
        )

    codon_usage_path = _resolve_codon_usage_path(lineardesign_root, payload.codon_usage_path)
    if not codon_usage_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Codon usage table not found: {codon_usage_path}",
        )

    items: list[LinearDesignBatchItem] = []
    for idx, raw_seq in enumerate(payload.protein_sequences):
        protein_sequence = raw_seq.strip().upper()
        if not protein_sequence:
            items.append(
                LinearDesignBatchItem(
                    success=False,
                    error=f"Sequence at index {idx} is empty.",
                )
            )
            continue
        try:
            # Per-sequence timeout to prevent a single long sequence from blocking the batch.
            seq_len = len(protein_sequence)
            timeout_seconds = max(300, int(seq_len * 0.8) + 180)
            result = _run_lineardesign_once(
                lineardesign_bin=lineardesign_bin,
                lineardesign_root=lineardesign_root,
                protein_sequence=protein_sequence,
                lambda_value=payload.lambda_value,
                verbose=payload.verbose,
                codon_usage_path=codon_usage_path,
                timeout_seconds=timeout_seconds,
            )
            items.append(
                LinearDesignBatchItem(
                    success=True,
                    generated_sequence=result["generated_sequence"],
                    structure=result["structure"],
                    mfe=result["mfe"],
                    cai_score=result["cai_score"],
                    raw_output=result["raw_output"],
                    stderr=result["stderr"],
                )
            )
        except (RuntimeError, ValueError) as exc:
            items.append(
                LinearDesignBatchItem(
                    success=False,
                    error=str(exc),
                )
            )

    return LinearDesignBatchResponse(
        items=items,
        count=len(items),
        lambda_value=payload.lambda_value,
        codon_usage_path=str(codon_usage_path),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Junction-aware CDS design endpoint (2026-08, additive only).
# 依赖 C++ JUNCTION-PATCH（external_repos/LinearDesign/src，2026-08）：
# LinearDesign_2D 支持 argc ∈ {4,5,7,8}，argv[4]=w_jun、argv[5]=flank5_rna、
# argv[6]=flank3_rna、argv[7]=junction_window_nt；flank 模式额外输出
# ``CDS sequence:`` / ``CDS CAI:`` 两行。上方 v0.2.0 锁定代码零改动。
# ═══════════════════════════════════════════════════════════════════════════════

# Default number of junction-side flank nucleotides forwarded to the binary.
DEFAULT_FLANK_NT = 21


class LinearDesignJunctionAwareRequest(BaseModel):
    protein_sequence: str = Field(..., min_length=1, description="Input protein sequence.")
    lambda_value: float = Field(
        default=0.0,
        ge=0.0,
        description="LinearDesign lambda balancing MFE and CAI.",
    )
    utr5_flank: Optional[str] = Field(
        default=None,
        description="Optional 5' UTR flank RNA sequence; the junction-side flank_nt "
        "(default 21) nt are folded as fixed sequence together with the CDS.",
    )
    utr3_flank: Optional[str] = Field(
        default=None,
        description="Optional 3' UTR flank RNA sequence; the junction-side flank_nt "
        "(default 21) nt are folded as fixed sequence together with the CDS.",
    )
    junction_weight: float = Field(
        default=0.0,
        ge=0.0,
        description="w_jun: penalty in kcal/mol applied per newly formed base pair "
        "touching a junction window (0 disables the penalty).",
    )
    junction_window_nt: int = Field(
        default=20,
        gt=0,
        description="Half-width (nt) of the two junction windows W1/W2 around the "
        "flank5|CDS and CDS|flank3 boundaries.",
    )
    flank_nt: int = Field(
        default=DEFAULT_FLANK_NT,
        description="Number of junction-side flank nucleotides used per side; must be "
        "a multiple of 3 and >= 3.",
    )
    codon_usage_path: Optional[str] = Field(
        default=None,
        description="Optional codon usage CSV path. Defaults to human table in LinearDesign repo.",
    )
    verbose: bool = Field(default=False, description="Enable verbose output in LinearDesign.")


class LinearDesignJunctionAwareResponse(BaseModel):
    generated_sequence: str = Field(
        description="Full-construct RNA sequence (flank5 + CDS + flank3)."
    )
    structure: str = Field(description="Full-construct dot-bracket structure.")
    mfe: float = Field(
        description="C++ printed energy = CKY objective value: thermodynamic MFE plus "
        "junction_weight x junction_window_pair_count (equals thermodynamic MFE when "
        "junction_weight == 0 or no flanks are used)."
    )
    cai_score: float = Field(description="CAI computed on the CDS region only.")
    lambda_value: float
    codon_usage_path: str
    model: str = "LinearDesign"
    raw_output: str
    stderr: str
    cds_sequence: str = Field(description="CDS region with flanks stripped.")
    cds_cai: float = Field(description="CAI of the CDS region (mirrors cai_score).")
    full_construct_sequence: str = Field(
        description="Alias of generated_sequence (flank5 + CDS + flank3)."
    )
    utr5_flank: str = Field(description="Actually used 5' flank (junction-side slice).")
    utr3_flank: str = Field(description="Actually used 3' flank (junction-side slice).")
    junction_weight: float
    junction_window_nt: int
    flank_nt: int
    junction_window_pair_count: int = Field(
        description="Number of base pairs in `structure` with at least one endpoint in "
        "W1 = [max(0, L5-w), L5+w) or W2 = [L5+Lcds-w, L5+Lcds+w) (clipped to the "
        "construct), the same windows the C++ junction penalty uses."
    )
    mfe_thermo: float = Field(
        description="Thermodynamic MFE = mfe - junction_weight x "
        "junction_window_pair_count when flanks are present; equals mfe when no "
        "flanks are used (legacy call, penalty not applied)."
    )


def _normalize_junction_flank(raw: Optional[str], field_name: str) -> str:
    """Uppercase + T->U a flank sequence; reject non-ACGU characters with 422."""
    if not raw:
        return ""
    flank = raw.strip().upper().replace("T", "U")
    if not flank:
        return ""
    invalid = sorted(set(flank) - set("ACGU"))
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid {field_name}: only ACGU(T) characters are allowed, "
                f"got {''.join(invalid)!r}."
            ),
        )
    return flank


def _slice_junction_flank(flank: str, flank_nt: int, *, is_5prime: bool) -> str:
    """Take the junction-side flank slice: last ``flank_nt`` nt for 5' flanks,
    first ``flank_nt`` nt for 3' flanks. Shorter flanks fall back to the largest
    multiple-of-3 length; flanks with fewer than 3 usable nt are rejected (422).
    """
    if not flank:
        return ""
    if len(flank) >= flank_nt:
        take = flank_nt
    else:
        take = len(flank) - (len(flank) % 3)
    if take < 3:
        side = "utr5_flank" if is_5prime else "utr3_flank"
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {side}: need at least 3 nt (a whole pseudo-codon) of flank sequence.",
        )
    return flank[-take:] if is_5prime else flank[:take]


def _count_junction_window_pairs(structure: str, l5: int, lcds: int, window_nt: int) -> int:
    """Count dot-bracket pairs with at least one endpoint in the C++ junction windows
    W1 = [max(0, L5-w), L5+w) and W2 = [L5+Lcds-w, L5+Lcds+w), clipped to [0, total).
    Coordinates are full-construct 0-based nucleotide indices.
    """
    total = len(structure)
    w1_lo, w1_hi = max(0, l5 - window_nt), min(total, l5 + window_nt)
    w2 = l5 + lcds
    w2_lo, w2_hi = max(0, w2 - window_nt), min(total, w2 + window_nt)

    def _in_window(pos: int) -> bool:
        return (w1_lo <= pos < w1_hi) or (w2_lo <= pos < w2_hi)

    stack: list[int] = []
    count = 0
    for i, ch in enumerate(structure):
        if ch == "(":
            stack.append(i)
        elif ch == ")" and stack:
            j = stack.pop()
            if _in_window(i) or _in_window(j):
                count += 1
    return count


def _extract_junction_output_fields(raw_output: str) -> tuple[str, float]:
    """Parse the two extra flank-mode lines (``CDS sequence:`` / ``CDS CAI:``)."""
    cds_match = re.search(r"CDS sequence:\s*([AUGC]+)", raw_output)
    cds_cai_match = re.search(r"CDS CAI:\s*([-+]?\d*\.?\d+)", raw_output)
    if not cds_match or not cds_cai_match:
        raise ValueError(
            "LinearDesign junction-mode output parsing failed. "
            "Expected CDS sequence and CDS CAI fields."
        )
    return cds_match.group(1).strip(), float(cds_cai_match.group(1))


def _run_lineardesign_junction_aware_once(
    lineardesign_bin: Path,
    lineardesign_root: Path,
    protein_sequence: str,
    lambda_value: float,
    verbose: bool,
    codon_usage_path: Path,
    junction_weight: float,
    flank5_rna: str,
    flank3_rna: str,
    junction_window_nt: int,
    timeout_seconds: Optional[float] = None,
) -> dict[str, Any]:
    """Execute the patched LinearDesign binary with junction arguments (argc == 8).

    Returns the legacy keys (generated_sequence = full construct, structure, mfe,
    cai_score = CDS CAI, raw_output, stderr) plus cds_sequence / cds_cai.
    """
    _reject_oversized_protein(protein_sequence)
    cmd = [
        str(lineardesign_bin),
        f"{lambda_value}",
        "1" if verbose else "0",
        str(codon_usage_path),
        f"{junction_weight}",
        flank5_rna,
        flank3_rna,
        f"{junction_window_nt}",
    ]
    env = os.environ.copy()
    process = subprocess.run(
        cmd,
        input=protein_sequence + "\n",
        text=True,
        capture_output=True,
        cwd=str(lineardesign_root),
        env=env,
        check=False,
        timeout=timeout_seconds,
    )

    if process.returncode != 0:
        raise RuntimeError(
            "LinearDesign execution failed. "
            f"returncode={process.returncode}; stderr={process.stderr.strip()}"
        )

    generated_sequence, structure, mfe, _cai = _extract_output_fields(process.stdout)
    cds_sequence, cds_cai = _extract_junction_output_fields(process.stdout)
    return {
        "generated_sequence": generated_sequence,
        "structure": structure,
        "mfe": mfe,
        "cai_score": cds_cai,
        "cds_sequence": cds_sequence,
        "cds_cai": cds_cai,
        "raw_output": process.stdout,
        "stderr": process.stderr,
    }


@app.post("/generate/cds_junction_aware", response_model=LinearDesignJunctionAwareResponse)
def generate_cds_junction_aware(
    payload: LinearDesignJunctionAwareRequest,
) -> LinearDesignJunctionAwareResponse:
    """Junction-aware CDS design: fixed UTR flanks join the global fold and a
    junction-window pair penalty (w_jun) is applied inside the CKY objective.

    With both flanks empty the call degenerates to the legacy 4-argument binary
    invocation and legacy parsing, so zero-flank behavior is identical to
    ``/generate/cds``.
    """
    lineardesign_root = _resolve_lineardesign_root()
    lineardesign_bin = lineardesign_root / "bin" / "LinearDesign_2D"
    if not lineardesign_bin.exists():
        canonical = _canonical_lineardesign_root()
        raise HTTPException(
            status_code=500,
            detail=(
                f"LinearDesign binary not found: {lineardesign_bin}. "
                f"Expected checkout at {canonical} (run `make` there), "
                "or set LINEARDESIGN_ROOT to a directory that contains bin/LinearDesign_2D."
            ),
        )

    codon_usage_path = _resolve_codon_usage_path(lineardesign_root, payload.codon_usage_path)
    if not codon_usage_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Codon usage table not found: {codon_usage_path}",
        )

    protein_sequence = payload.protein_sequence.strip().upper()
    if not protein_sequence:
        raise HTTPException(status_code=400, detail="Protein sequence is empty.")

    if payload.flank_nt < 3 or payload.flank_nt % 3 != 0:
        raise HTTPException(
            status_code=422,
            detail="flank_nt must be a multiple of 3 and >= 3.",
        )

    flank5 = _slice_junction_flank(
        _normalize_junction_flank(payload.utr5_flank, "utr5_flank"),
        payload.flank_nt,
        is_5prime=True,
    )
    flank3 = _slice_junction_flank(
        _normalize_junction_flank(payload.utr3_flank, "utr3_flank"),
        payload.flank_nt,
        is_5prime=False,
    )

    # Timeout uses the full-construct length (nt), keeping the 0.8 s/unit + 180 s rule.
    total_nt = 3 * len(protein_sequence) + len(flank5) + len(flank3)
    timeout_seconds = max(300, int(total_nt * 0.8) + 180)

    flanks_present = bool(flank5 or flank3)
    try:
        if flanks_present:
            result = _run_lineardesign_junction_aware_once(
                lineardesign_bin=lineardesign_bin,
                lineardesign_root=lineardesign_root,
                protein_sequence=protein_sequence,
                lambda_value=payload.lambda_value,
                verbose=payload.verbose,
                codon_usage_path=codon_usage_path,
                junction_weight=payload.junction_weight,
                flank5_rna=flank5,
                flank3_rna=flank3,
                junction_window_nt=payload.junction_window_nt,
                timeout_seconds=timeout_seconds,
            )
        else:
            # Zero-flank legacy path: 4-argument call, legacy parsing, penalty not applied.
            result = _run_lineardesign_once(
                lineardesign_bin=lineardesign_bin,
                lineardesign_root=lineardesign_root,
                protein_sequence=protein_sequence,
                lambda_value=payload.lambda_value,
                verbose=payload.verbose,
                codon_usage_path=codon_usage_path,
                timeout_seconds=timeout_seconds,
            )
            result["cds_sequence"] = result["generated_sequence"]
            result["cds_cai"] = result["cai_score"]
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    pair_count = _count_junction_window_pairs(
        result["structure"],
        len(flank5),
        len(result["cds_sequence"]),
        payload.junction_window_nt,
    )
    if flanks_present:
        mfe_thermo = result["mfe"] - payload.junction_weight * pair_count
    else:
        # Legacy call: the penalty was never applied, so mfe is already thermodynamic.
        mfe_thermo = result["mfe"]

    return LinearDesignJunctionAwareResponse(
        generated_sequence=result["generated_sequence"],
        structure=result["structure"],
        mfe=result["mfe"],
        cai_score=result["cai_score"],
        lambda_value=payload.lambda_value,
        codon_usage_path=str(codon_usage_path),
        raw_output=result["raw_output"],
        stderr=result["stderr"],
        cds_sequence=result["cds_sequence"],
        cds_cai=result["cds_cai"],
        full_construct_sequence=result["generated_sequence"],
        utr5_flank=flank5,
        utr3_flank=flank3,
        junction_weight=payload.junction_weight,
        junction_window_nt=payload.junction_window_nt,
        flank_nt=payload.flank_nt,
        junction_window_pair_count=pair_count,
        mfe_thermo=mfe_thermo,
    )
