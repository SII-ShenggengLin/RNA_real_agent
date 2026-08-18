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


# ═══════════════════════════════════════════════════════════════════════════════
# Junction-aware CDS design endpoint (2026-08, additive only).
# 依赖 C++ JUNCTION-PATCH（external_repos/LinearDesign/src，2026-08）：
# LinearDesign_2D 支持 argc ∈ {4,5,7,8}，argv[4]=w_jun、argv[5]=flank5_rna、
# argv[6]=flank3_rna、argv[7]=junction_window_nt；flank 模式额外输出
# ``CDS sequence:`` / ``CDS CAI:`` 两行。上方 v0.2.0 锁定代码零改动。
# ═══════════════════════════════════════════════════════════════════════════════

# Default number of junction-side flank nucleotides forwarded to the binary.
DEFAULT_FLANK_NT = 21


