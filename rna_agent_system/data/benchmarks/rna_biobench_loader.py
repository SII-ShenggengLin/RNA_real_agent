"""Unified loader for RNA-BioBench datasets.

This module provides type-safe, versioned access to all benchmark datasets
used in the RosalindAgent paper experiments.

Datasets:
- RNA-BioBench-FullLength-mRNA: 5 targets for Type-I BMC (full-length mRNA)
- RNA-BioBench-Aptamer: 3 targets for Type-II BMC (RNA aptamer)
- RNA-BioBench-Platform: 36 tasks across 11 workflows for platform coverage
- RNA-BioBench-ProcessAware: 12 tasks for cross-LLM process-metric analysis

Usage:
    from data.benchmarks.rna_biobench_loader import (
        load_full_length_mrna_targets,
        load_aptamer_targets,
        load_platform_tasks,
        load_process_aware_task_set,
    )

    targets = load_full_length_mrna_targets()
    for t in targets:
        print(t.target_id, t.protein_length_aa)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

_BENCHMARKS_DIR = Path(__file__).parent.resolve()

_FULL_LENGTH_DIR = _BENCHMARKS_DIR / "RNA-BioBench-FullLength-mRNA"
_APTAMER_DIR = _BENCHMARKS_DIR / "RNA-BioBench-Aptamer"
_PLATFORM_DIR = _BENCHMARKS_DIR / "RNA-BioBench-Platform"
_PROCESS_AWARE_DIR = _BENCHMARKS_DIR / "RNA-BioBench-ProcessAware"


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FullLengthMrnaTarget:
    """A full-length mRNA design benchmark target."""
    target_id: str
    target_name: str
    target_type: str
    accession: str
    protein_sequence: str
    protein_length_aa: int
    expected_cds_length_nt: int
    species_for_codon_optimization: str
    expression_system: str
    organism_scientific: str
    sequence_checksum: str
    paper_references: List[str]
    notes: str

    @property
    def sequence_fasta_path(self) -> Path:
        return _FULL_LENGTH_DIR / "sequences" / f"{self.target_id}.fa"


@dataclass(frozen=True)
class AptamerTarget:
    """An RNA aptamer design benchmark target."""
    target_id: str
    target_name: str
    target_type: str
    pdb_id: str
    pdb_chain: str
    protein_sequence: str
    protein_length_aa: int
    known_hotspot_residues: Optional[str]
    hotspot_source: str
    known_aptamer_reference: Optional[Dict[str, Any]]
    paper_references: List[str]
    notes: str

    @property
    def structure_pdb_path(self) -> Path:
        return _APTAMER_DIR / "structures" / f"{self.pdb_id.lower()}.pdb"


@dataclass(frozen=True)
class PlatformTask:
    """A single platform coverage benchmark task."""
    task_id: str
    workflow: str
    category: str
    description: str
    input: Dict[str, Any]
    expected_tool_chain: List[str]
    evaluation_rubric: Dict[str, Any]
    source: Optional[str]
    paper_reference: Optional[str]


@dataclass(frozen=True)
class ProcessAwareTask:
    """A task in the process-aware LLM comparison set."""
    task_id: str
    workflow: str
    source_task: str
    description: str
    user_query: str
    query_type: str
    expected_workflow: str
    rationale: str


# ─────────────────────────────────────────────────────────────────────────────
# Loader functions
# ─────────────────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_full_length_mrna_targets() -> List[FullLengthMrnaTarget]:
    """Load all 5 full-length mRNA design targets.

    Returns:
        List of FullLengthMrnaTarget dataclasses.
    """
    targets_dir = _FULL_LENGTH_DIR / "targets"
    results: List[FullLengthMrnaTarget] = []
    for json_path in sorted(targets_dir.glob("*.json")):
        if json_path.name == "dataset_manifest.json":
            continue
        data = _load_json(json_path)
        results.append(
            FullLengthMrnaTarget(
                target_id=data["target_id"],
                target_name=data["target_name"],
                target_type=data["target_type"],
                accession=data["accession"],
                protein_sequence=data["protein_sequence"],
                protein_length_aa=data["protein_length_aa"],
                expected_cds_length_nt=data["expected_cds_length_nt"],
                species_for_codon_optimization=data["species_for_codon_optimization"],
                expression_system=data["expression_system"],
                organism_scientific=data.get("organism_scientific", ""),
                sequence_checksum=data.get("sequence_checksum", ""),
                paper_references=data.get("paper_references", []),
                notes=data.get("notes", ""),
            )
        )
    return results


def load_aptamer_targets() -> List[AptamerTarget]:
    """Load all 3 RNA aptamer design targets.

    Returns:
        List of AptamerTarget dataclasses.
    """
    targets_dir = _APTAMER_DIR / "targets"
    results: List[AptamerTarget] = []
    for json_path in sorted(targets_dir.glob("*.json")):
        if json_path.name == "dataset_manifest.json":
            continue
        data = _load_json(json_path)
        results.append(
            AptamerTarget(
                target_id=data["target_id"],
                target_name=data["target_name"],
                target_type=data["target_type"],
                pdb_id=data["pdb_id"],
                pdb_chain=data["pdb_chain"],
                protein_sequence=data.get("protein_sequence", ""),
                protein_length_aa=data.get("protein_length_aa", 0),
                known_hotspot_residues=data.get("known_hotspot_residues") or None,
                hotspot_source=data.get("hotspot_source", ""),
                known_aptamer_reference=data.get("known_aptamer_reference"),
                paper_references=data.get("paper_references", []),
                notes=data.get("notes", ""),
            )
        )
    return results


def load_platform_tasks(
    workflow: Optional[str] = None,
    category: Optional[str] = None,
) -> List[PlatformTask]:
    """Load platform coverage benchmark tasks.

    Args:
        workflow: Filter by workflow ID (e.g., "01_mrna_cds_design").
        category: Filter by category ("basic", "edge", "full", "full-length").

    Returns:
        List of PlatformTask dataclasses.
    """
    tasks_dir = _PLATFORM_DIR / "tasks"
    results: List[PlatformTask] = []
    for json_path in sorted(tasks_dir.rglob("*.json")):
        if json_path.name.endswith("manifest.json"):
            continue
        data = _load_json(json_path)
        if workflow and data.get("workflow") != workflow:
            continue
        if category and data.get("category") != category:
            continue
        results.append(
            PlatformTask(
                task_id=data["task_id"],
                workflow=data["workflow"],
                category=data["category"],
                description=data["description"],
                input=data["input"],
                expected_tool_chain=data["expected_tool_chain"],
                evaluation_rubric=data["evaluation_rubric"],
                source=data.get("source"),
                paper_reference=data.get("paper_reference"),
            )
        )
    return results


def load_process_aware_task_set() -> Dict[str, Any]:
    """Load the process-aware LLM comparison task set.

    Returns:
        Dict containing tasks, llm_backends, metrics, and expected_analysis.
        Each task includes a ``user_query`` (natural language) and a
        ``source_task`` (gold structured input in Platform benchmark).
    """
    path = _PROCESS_AWARE_DIR / "task_set_for_llm_comparison.json"
    return _load_json(path)


def load_process_aware_tasks() -> List[ProcessAwareTask]:
    """Load process-aware tasks as typed dataclasses.

    Returns:
        List of ProcessAwareTask with natural-language queries.
    """
    data = load_process_aware_task_set()
    return [
        ProcessAwareTask(
            task_id=t["task_id"],
            workflow=t["workflow"],
            source_task=t["source_task"],
            description=t["description"],
            user_query=t.get("user_query", ""),
            query_type=t.get("query_type", "general"),
            expected_workflow=t.get("expected_workflow", t["workflow"]),
            rationale=t["rationale"],
        )
        for t in data.get("tasks", [])
    ]


def get_dataset_manifest(dataset: str) -> Dict[str, Any]:
    """Load the manifest for a given dataset.

    Args:
        dataset: One of "full-length-mrna", "aptamer", "platform", "process-aware".

    Returns:
        Manifest dict with metadata.
    """
    mapping = {
        "full-length-mrna": _FULL_LENGTH_DIR / "dataset_manifest.json",
        "aptamer": _APTAMER_DIR / "dataset_manifest.json",
        "platform": _PLATFORM_DIR / "benchmark_manifest.json",
        "process-aware": _PROCESS_AWARE_DIR / "task_set_for_llm_comparison.json",
    }
    path = mapping.get(dataset)
    if not path:
        raise ValueError(f"Unknown dataset: {dataset}. Choose from {list(mapping.keys())}")
    return _load_json(path)


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

def validate_all_datasets() -> Dict[str, List[str]]:
    """Validate all benchmark datasets and report issues.

    Returns:
        Dict mapping dataset name -> list of error messages (empty if OK).
    """
    errors: Dict[str, List[str]] = {}

    # Full-length mRNA
    fl_errors: List[str] = []
    try:
        targets = load_full_length_mrna_targets()
        if len(targets) < 5:
            fl_errors.append(f"Expected at least 5 targets, got {len(targets)}")
        for t in targets:
            if len(t.protein_sequence) == 0:
                fl_errors.append(f"{t.target_id}: empty protein_sequence")
            if not t.sequence_fasta_path.exists():
                fl_errors.append(f"{t.target_id}: FASTA file missing")
    except Exception as e:
        fl_errors.append(str(e))
    errors["RNA-BioBench-FullLength-mRNA"] = fl_errors

    # Aptamer
    apt_errors: List[str] = []
    try:
        targets = load_aptamer_targets()
        if len(targets) < 3:
            apt_errors.append(f"Expected at least 3 targets, got {len(targets)}")
        for t in targets:
            if len(t.protein_sequence) == 0:
                apt_errors.append(f"{t.target_id}: empty protein_sequence")
            if not t.structure_pdb_path.exists():
                apt_errors.append(f"{t.target_id}: PDB file missing ({t.structure_pdb_path})")
    except Exception as e:
        apt_errors.append(str(e))
    errors["RNA-BioBench-Aptamer"] = apt_errors

    # Platform
    plat_errors: List[str] = []
    try:
        tasks = load_platform_tasks()
        manifest = get_dataset_manifest("platform")
        expected = manifest.get("total_tasks", 0)
        if len(tasks) != expected:
            plat_errors.append(f"Expected {expected} tasks, got {len(tasks)}")
    except Exception as e:
        plat_errors.append(str(e))
    errors["RNA-BioBench-Platform"] = plat_errors

    # Process-aware
    pa_errors: List[str] = []
    try:
        data = load_process_aware_task_set()
        tasks = data.get("tasks", [])
        if len(tasks) != 12:
            pa_errors.append(f"Expected 12 tasks, got {len(tasks)}")
        if len(data.get("llm_backends", [])) != 6:
            pa_errors.append(f"Expected 6 LLM backends, got {len(data.get('llm_backends', []))}")
        for t in tasks:
            if not t.get("user_query"):
                pa_errors.append(f"{t.get('task_id', '?')}: missing user_query")
            if not t.get("query_type"):
                pa_errors.append(f"{t.get('task_id', '?')}: missing query_type")
            if not t.get("expected_workflow"):
                pa_errors.append(f"{t.get('task_id', '?')}: missing expected_workflow")
    except Exception as e:
        pa_errors.append(str(e))
    errors["RNA-BioBench-ProcessAware"] = pa_errors

    return errors


if __name__ == "__main__":
    print("RNA-BioBench Dataset Validation")
    print("=" * 50)
    errs = validate_all_datasets()
    all_ok = True
    for name, msgs in errs.items():
        status = "OK" if not msgs else f"{len(msgs)} ERROR(S)"
        print(f"  {name}: {status}")
        for m in msgs:
            print(f"    - {m}")
        if msgs:
            all_ok = False
    print("=" * 50)
    print("All datasets valid!" if all_ok else "Validation failed.")
