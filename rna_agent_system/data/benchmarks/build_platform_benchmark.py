#!/usr/bin/env python3
"""Build RNA-BioBench-Platform benchmark tasks for all 11 workflows."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent / "RNA-BioBench-Platform"

# Load real target sequences for reuse
FL_DIR = Path(__file__).parent / "RNA-BioBench-FullLength-mRNA" / "targets"
APT_DIR = Path(__file__).parent / "RNA-BioBench-Aptamer" / "targets"


def load_json(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text())


# Reusable sequences
SPIKE_SEQ = load_json(FL_DIR / "SARS-CoV-2_Spike_WT.json")["protein_sequence"]
EPO_SEQ = load_json(FL_DIR / "EPO.json")["protein_sequence"]
GFP_SEQ = load_json(FL_DIR / "GFP.json")["protein_sequence"]
LUC_SEQ = load_json(FL_DIR / "Luciferase.json")["protein_sequence"]
HA_SEQ = load_json(FL_DIR / "Influenza_HA_H1N1.json")["protein_sequence"]

NPRO_SEQ = load_json(APT_DIR / "SARS-CoV-2_Nucleocapsid.json")["protein_sequence"]
THR_SEQ = load_json(APT_DIR / "Thrombin.json")["protein_sequence"]
GFP_APT_SEQ = load_json(APT_DIR / "GFP.json")["protein_sequence"]


def save_task(workflow: str, task_id: str, data: dict[str, Any]) -> None:
    wf_dir = BASE / "tasks" / workflow
    wf_dir.mkdir(parents=True, exist_ok=True)
    path = wf_dir / f"{task_id}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  [saved] {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# 01 mrna_cds_design
# ═══════════════════════════════════════════════════════════════════════════════

def build_mrna_cds_design() -> None:
    wf = "01_mrna_cds_design"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "mrna_cds_design",
            "category": "basic",
            "description": "Short viral protein CDS optimization with LinearDesign",
            "input": {
                "protein_sequence": "MKTLLILTVFGITMLLAVLAQG",
                "design_tool": "LinearDesign",
                "lambda_value": 2.0,
                "cai_species": "Homo sapiens",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "predict_rna_secondary_structure_with_viennarna",
                "compute_rna_sequence_gc_content",
            ],
            "evaluation_rubric": {"cai_threshold": 0.80, "mfe_threshold": -30.0},
            "source": "Synthetic short peptide",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_human_therapeutic",
            "workflow": "mrna_cds_design",
            "category": "full",
            "description": "Human EPO CDS optimization (high-expression therapeutic)",
            "input": {
                "protein_sequence": EPO_SEQ,
                "design_tool": "LinearDesign",
                "lambda_value": 3.0,
                "cai_species": "Homo sapiens",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "predict_rna_secondary_structure_with_viennarna",
                "compute_rna_sequence_gc_content",
                "compute_cai_for_cds_sequence",
            ],
            "evaluation_rubric": {"cai_threshold": 0.85, "mfe_threshold": -100.0},
            "source": "UniProt P01588",
            "paper_reference": "doi:10.1038/313806a0"},
        {
            "task_id": f"{wf}_003_reporter_yeast",
            "workflow": "mrna_cds_design",
            "category": "edge",
            "description": "GFP CDS with yeast codon usage (cross-species edge case)",
            "input": {
                "protein_sequence": GFP_SEQ,
                "design_tool": "LinearDesign",
                "lambda_value": 2.0,
                "cai_species": "Saccharomyces cerevisiae",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "compute_cai_for_cds_sequence",
            ],
            "evaluation_rubric": {"cai_threshold": 0.75, "mfe_threshold": -50.0},
            "source": "UniProt P42212",
            "paper_reference": "doi:10.1126/science.8303295"},
        {
            "task_id": f"{wf}_004_long_vaccine",
            "workflow": "mrna_cds_design",
            "category": "full",
            "description": "SARS-CoV-2 Spike CDS (long vaccine target, >1200 aa)",
            "input": {
                "protein_sequence": SPIKE_SEQ,
                "design_tool": "LinearDesign",
                "lambda_value": 2.0,
                "cai_species": "Homo sapiens",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "predict_rna_secondary_structure_with_viennarna",
                "compute_rna_sequence_gc_content",
                "compute_cai_for_cds_sequence",
            ],
            "evaluation_rubric": {"cai_threshold": 0.80, "mfe_threshold": -500.0},
            "source": "UniProt P0DTC2",
            "paper_reference": "doi:10.1038/s41586-020-2622-0"},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 02 full_length_mrna_design
# ═══════════════════════════════════════════════════════════════════════════════

def build_full_length_mrna_design() -> None:
    wf = "02_full_length_mrna_design"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "full_length_mrna_design",
            "category": "basic",
            "description": "Short reporter protein full-length mRNA with default UTRs",
            "input": {
                "protein_sequence": "MKTLLILTVFGITMLLAVLAQG",
                "design_tool": "LinearDesign",
                "lambda_value": 2.0,
                "cai_species": "Homo sapiens",
                "utr_mode": "default",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "predict_rna_secondary_structure_with_viennarna",
                "compute_rna_sequence_gc_content",
            ],
            "evaluation_rubric": {"junction_mfe_threshold": -15.0, "cai_threshold": 0.80},
            "source": "Synthetic short peptide",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_vaccine_spike",
            "workflow": "full_length_mrna_design",
            "category": "full-length",
            "description": "SARS-CoV-2 Spike full-length mRNA (BMC Type-I core benchmark)",
            "input": {
                "protein_sequence": SPIKE_SEQ,
                "design_tool": "LinearDesign",
                "lambda_value": 2.0,
                "cai_species": "Homo sapiens",
                "utr_mode": "optimized",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "generate_utr_with_gemorna",
                "predict_rna_secondary_structure_with_viennarna",
                "compute_rna_sequence_gc_content",
            ],
            "evaluation_rubric": {
                "junction_5utr_cds_mfe_threshold": -20.0,
                "junction_cds_3utr_mfe_threshold": -15.0,
                "cai_threshold": 0.80},
            "source": "UniProt P0DTC2",
            "paper_reference": "doi:10.1038/s41586-020-2622-0"},
        {
            "task_id": f"{wf}_003_therapeutic_epo",
            "workflow": "full_length_mrna_design",
            "category": "full-length",
            "description": "EPO full-length mRNA with CHO codon optimization",
            "input": {
                "protein_sequence": EPO_SEQ,
                "design_tool": "LinearDesign",
                "lambda_value": 3.0,
                "cai_species": "Homo sapiens",
                "utr_mode": "optimized",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "generate_utr_with_gemorna",
                "predict_rna_secondary_structure_with_viennarna",
                "compute_rna_sequence_gc_content",
            ],
            "evaluation_rubric": {"junction_mfe_threshold": -15.0, "cai_threshold": 0.85},
            "source": "UniProt P01588",
            "paper_reference": "doi:10.1038/313806a0"},
        {
            "task_id": f"{wf}_004_reporter_luciferase",
            "workflow": "full_length_mrna_design",
            "category": "full-length",
            "description": "Firefly luciferase full-length mRNA (benchmark reporter)",
            "input": {
                "protein_sequence": LUC_SEQ,
                "design_tool": "LinearDesign",
                "lambda_value": 2.0,
                "cai_species": "Homo sapiens",
                "utr_mode": "optimized",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "generate_utr_with_gemorna",
                "predict_rna_secondary_structure_with_viennarna",
                "compute_rna_sequence_gc_content",
            ],
            "evaluation_rubric": {"junction_mfe_threshold": -15.0, "cai_threshold": 0.80},
            "source": "UniProt P08659",
            "paper_reference": "doi:10.1016/0003-2697(87)90103-0"},
        {
            "task_id": f"{wf}_005_influenza_ha",
            "workflow": "full_length_mrna_design",
            "category": "full-length",
            "description": "Influenza HA full-length mRNA (high variability vaccine)",
            "input": {
                "protein_sequence": HA_SEQ,
                "design_tool": "LinearDesign",
                "lambda_value": 2.0,
                "cai_species": "Homo sapiens",
                "utr_mode": "optimized",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": [
                "design_mrna_cds_with_lineardesign",
                "generate_utr_with_gemorna",
                "predict_rna_secondary_structure_with_viennarna",
                "compute_rna_sequence_gc_content",
            ],
            "evaluation_rubric": {"junction_mfe_threshold": -15.0, "cai_threshold": 0.80},
            "source": "UniProt P03452",
            "paper_reference": "doi:10.1126/science.1172482"},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 03 mrna_sequence_scoring
# ═══════════════════════════════════════════════════════════════════════════════

def build_mrna_sequence_scoring() -> None:
    wf = "03_mrna_sequence_scoring"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "mrna_sequence_scoring",
            "category": "basic",
            "description": "Single short sequence scoring",
            "input": {
                "sequence": "AUGGCCGAAUGGCCGAAUGGCC",
                "gc_tool_name": "compute_rna_sequence_gc_content",
                "fold_tool_name": "predict_rna_secondary_structure_with_linearfold",
                "run_gc_tool": True,
                "run_fold_tool": True},
            "expected_tool_chain": [
                "compute_rna_sequence_gc_content",
                "predict_rna_secondary_structure_with_linearfold",
            ],
            "evaluation_rubric": {"score_range": [0.0, 100.0]},
            "source": "Synthetic test sequence",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_multi_sequence",
            "workflow": "mrna_sequence_scoring",
            "category": "edge",
            "description": "Multiple sequence ranking comparison",
            "input": {
                "sequences": [
                    "AAAAAAAAUGCCCCCCCCCCUUUUUUUUUUUUUUAAAAAAAAAA",
                    "GCCGCCGCCGCC",
                    "AUGGCCGAAUGGCCGAAUGGCC",
                ],
                "gc_tool_name": "compute_rna_sequence_gc_content",
                "fold_tool_name": "predict_rna_secondary_structure_with_linearfold",
                "run_gc_tool": True,
                "run_fold_tool": True},
            "expected_tool_chain": [
                "compute_rna_sequence_gc_content",
                "predict_rna_secondary_structure_with_linearfold",
            ],
            "evaluation_rubric": {"score_range": [0.0, 100.0], "ranking_uniqueness": True},
            "source": "Synthetic test sequences",
            "paper_reference": None},
        {
            "task_id": f"{wf}_003_real_mrna",
            "workflow": "mrna_sequence_scoring",
            "category": "full",
            "description": "Real mRNA sequence scoring (EPO CDS region)",
            "input": {
                "sequence": EPO_SEQ[:100] + "AUG" + EPO_SEQ[100:200],
                "gc_tool_name": "compute_rna_sequence_gc_content",
                "fold_tool_name": "predict_rna_secondary_structure_with_viennarna",
                "run_gc_tool": True,
                "run_fold_tool": True},
            "expected_tool_chain": [
                "compute_rna_sequence_gc_content",
                "predict_rna_secondary_structure_with_viennarna",
            ],
            "evaluation_rubric": {"score_range": [0.0, 100.0]},
            "source": "UniProt P01588 fragment",
            "paper_reference": "doi:10.1038/313806a0"},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 04 sirna_design
# ═══════════════════════════════════════════════════════════════════════════════

def build_sirna_design() -> None:
    wf = "04_sirna_design"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "sirna_design",
            "category": "basic",
            "description": "Simple siRNA design against short target sequence",
            "input": {
                "mode": "existing",
                "target_sequence": "AUGCCCGGGUUUAAAUUUAAACCCGGGCCC",
                "candidate_count": 4,
                "off_target_scan": False,
                "species": "human",
                "evitar_mode": "si",
                "evitar_predict": "predsi",
                "ncores": 1},
            "expected_tool_chain": [
                "design_sirna_with_evitar",
                "compute_rna_sequence_gc_content",
            ],
            "evaluation_rubric": {"min_candidates": 2, "gc_range": [0.30, 0.70]},
            "source": "Synthetic target",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_human_gene",
            "workflow": "sirna_design",
            "category": "full",
            "description": "siRNA design against human EPO transcript fragment",
            "input": {
                "mode": "existing",
                "target_sequence": EPO_SEQ[:100] + "AUG" + EPO_SEQ[100:200],
                "candidate_count": 5,
                "off_target_scan": False,
                "species": "human",
                "evitar_mode": "si",
                "evitar_predict": "predsi",
                "ncores": 1},
            "expected_tool_chain": [
                "design_sirna_with_evitar",
                "compute_rna_sequence_gc_content",
                "run_blastn_similarity_search",
            ],
            "evaluation_rubric": {"min_candidates": 3, "gc_range": [0.30, 0.70]},
            "source": "UniProt P01588 fragment",
            "paper_reference": "doi:10.1038/313806a0"},
        {
            "task_id": f"{wf}_003_with_offtarget",
            "workflow": "sirna_design",
            "category": "edge",
            "description": "siRNA with off-target scanning enabled",
            "input": {
                "mode": "existing",
                "target_sequence": "AUGCCCGGGUUUAAAUUUAAACCCGGGCCCAAAUUU",
                "candidate_count": 4,
                "off_target_scan": True,
                "species": "human",
                "evitar_mode": "si",
                "evitar_predict": "predsi",
                "ncores": 1},
            "expected_tool_chain": [
                "design_sirna_with_evitar",
                "run_blastn_similarity_search",
                "score_crispr_off_target_with_crisot",
            ],
            "evaluation_rubric": {"min_candidates": 2, "off_target_score_threshold": 0.5},
            "source": "Synthetic target",
            "paper_reference": None},
        {
            "task_id": f"{wf}_004_covid_target",
            "workflow": "sirna_design",
            "category": "full",
            "description": "siRNA design against SARS-CoV-2 Spike fragment",
            "input": {
                "mode": "existing",
                "target_sequence": SPIKE_SEQ[:150] + "AUG" + SPIKE_SEQ[150:300],
                "candidate_count": 5,
                "off_target_scan": False,
                "species": "human",
                "evitar_mode": "si",
                "evitar_predict": "predsi",
                "ncores": 1},
            "expected_tool_chain": [
                "design_sirna_with_evitar",
                "compute_rna_sequence_gc_content",
            ],
            "evaluation_rubric": {"min_candidates": 3, "gc_range": [0.30, 0.70]},
            "source": "UniProt P0DTC2 fragment",
            "paper_reference": "doi:10.1038/s41586-020-2622-0"},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 05 sgrna_design
# ═══════════════════════════════════════════════════════════════════════════════

def build_sgrna_design() -> None:
    wf = "05_sgrna_design"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "sgrna_design",
            "category": "basic",
            "description": "sgRNA handle design with simple seed",
            "input": {
                "seed_sequence": "GAGUCCGAGCAGAAGAAGAA",
                "n_samples": 5,
                "mutation_number": 3,
                "sampling_mode": "mcmc",
                "max_overlap": 5,
                "evaluate_crgpt_score": True,
                "evaluate_crisot": False,
                "weight_nn_score": 0.5,
                "weight_crisot": 0.5},
            "expected_tool_chain": [
                "design_sgrna_handle_with_crgpt",
            ],
            "evaluation_rubric": {"min_candidates": 3, "max_overlap_violations": 0},
            "source": "Synthetic seed",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_with_crisot",
            "workflow": "sgrna_design",
            "category": "edge",
            "description": "sgRNA with CRISOT off-target evaluation",
            "input": {
                "seed_sequence": "GAGUCCGAGCAGAAGAAGAA",
                "n_samples": 5,
                "mutation_number": 3,
                "sampling_mode": "mcmc",
                "max_overlap": 5,
                "evaluate_crgpt_score": True,
                "evaluate_crisot": True,
                "weight_nn_score": 0.5,
                "weight_crisot": 0.5},
            "expected_tool_chain": [
                "design_sgrna_handle_with_crgpt",
                "score_sgrna_handle_with_crgpt",
                "score_crispr_off_target_with_crisot",
            ],
            "evaluation_rubric": {"min_candidates": 3, "crisot_score_threshold": 0.6},
            "source": "Synthetic seed",
            "paper_reference": None},
        {
            "task_id": f"{wf}_003_real_target",
            "workflow": "sgrna_design",
            "category": "full",
            "description": "sgRNA for human gene targeting",
            "input": {
                "target_sequence": EPO_SEQ[:30],
                "n_samples": 5,
                "mutation_number": 3,
                "sampling_mode": "mcmc",
                "max_overlap": 5,
                "evaluate_crgpt_score": True,
                "evaluate_crisot": False,
                "weight_nn_score": 0.5,
                "weight_crisot": 0.5},
            "expected_tool_chain": [
                "design_sgrna_handle_with_crgpt",
            ],
            "evaluation_rubric": {"min_candidates": 3},
            "source": "UniProt P01588 fragment",
            "paper_reference": "doi:10.1038/313806a0"},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 06 rna_secondary_structure_design
# ═══════════════════════════════════════════════════════════════════════════════

def build_rna_secondary_structure_design() -> None:
    wf = "06_rna_secondary_structure"
    tasks = [
        {
            "task_id": f"{wf}_001_basic_hairpin",
            "workflow": "rna_secondary_structure_design",
            "category": "basic",
            "description": "Simple hairpin structure inverse folding",
            "input": {
                "target_structure": "((((....))))",
                "start_sequence": None,
                "repeats": 3,
                "num_invocations": 5,
                "temp_c": 37.0,
                "function_mode": "MFE"},
            "expected_tool_chain": [
                "predict_rna_secondary_structure_with_viennarna",
            ],
            "evaluation_rubric": {"structure_match": True, "mfe_threshold": -5.0},
            "source": "Synthetic hairpin",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_complex_structure",
            "workflow": "rna_secondary_structure_design",
            "category": "edge",
            "description": "Complex multiloop structure",
            "input": {
                "target_structure": "..((((...))))..(((...)))..",
                "start_sequence": None,
                "repeats": 3,
                "num_invocations": 10,
                "temp_c": 37.0,
                "function_mode": "MFE"},
            "expected_tool_chain": [
                "predict_rna_secondary_structure_with_viennarna",
            ],
            "evaluation_rubric": {"structure_match": True, "mfe_threshold": -10.0},
            "source": "Synthetic multiloop",
            "paper_reference": None},
        {
            "task_id": f"{wf}_003_ires_mimic",
            "workflow": "rna_secondary_structure_design",
            "category": "full",
            "description": "IRES-like structured element design",
            "input": {
                "target_structure": "(((((((...)))))))...((((...))))...",
                "start_sequence": None,
                "repeats": 5,
                "num_invocations": 10,
                "temp_c": 37.0,
                "function_mode": "MFE"},
            "expected_tool_chain": [
                "predict_rna_secondary_structure_with_viennarna",
            ],
            "evaluation_rubric": {"structure_match": True, "mfe_threshold": -15.0},
            "source": "Synthetic IRES-like structure",
            "paper_reference": None},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 07 rna_tertiary_structure_design
# ═══════════════════════════════════════════════════════════════════════════════

def build_rna_tertiary_structure_design() -> None:
    wf = "07_rna_tertiary_structure"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "rna_tertiary_structure_design",
            "category": "basic",
            "description": "Short RNA tertiary structure design with RhoDesign",
            "input": {
                "structure_filepath": "workspace/test_structure.pdb",
                "secondary_structure_filepath": None,
                "design_tools": ["RhoDesign"],
                "n_samples_per_tool": 3,
                "rhodesign_temperature": 0.1,
                "rhodesign_temperature_range": 0.05,
                "ribodiffusion_sampling_steps": 200,
                "ribodiffusion_cond_scale": 1.0,
                "ribodiffusion_checkpoint_name": "ribodiffusion_base",
                "weight_rhofold": 0.5,
                "weight_rmsd": 0.5},
            "expected_tool_chain": [
                "generate_rna_tertiary_structure_with_rhodesign",
                "predict_rna_tertiary_structure_with_rhofold",
            ],
            "evaluation_rubric": {"mean_plddt_threshold": 70.0, "rmsd_threshold": 2.0},
            "source": "Synthetic placeholder structure",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_dual_tool",
            "workflow": "rna_tertiary_structure_design",
            "category": "edge",
            "description": "Tertiary structure design with both RhoDesign and RiboDiffusion",
            "input": {
                "structure_filepath": "workspace/test_structure.pdb",
                "secondary_structure_filepath": None,
                "design_tools": ["RhoDesign", "RiboDiffusion"],
                "n_samples_per_tool": 2,
                "rhodesign_temperature": 0.1,
                "rhodesign_temperature_range": 0.05,
                "ribodiffusion_sampling_steps": 200,
                "ribodiffusion_cond_scale": 1.0,
                "ribodiffusion_checkpoint_name": "ribodiffusion_base",
                "weight_rhofold": 0.5,
                "weight_rmsd": 0.5},
            "expected_tool_chain": [
                "generate_rna_tertiary_structure_with_rhodesign",
                "generate_rna_tertiary_structure_with_ribodiffusion",
                "predict_rna_tertiary_structure_with_rhofold",
            ],
            "evaluation_rubric": {"mean_plddt_threshold": 65.0},
            "source": "Synthetic placeholder structure",
            "paper_reference": None},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 08 rna_aptamer_design
# ═══════════════════════════════════════════════════════════════════════════════

def build_rna_aptamer_design() -> None:
    wf = "08_rna_aptamer_design"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "rna_aptamer_design",
            "category": "basic",
            "description": "Simple aptamer design against synthetic protein",
            "input": {
                "protein_sequence": "MKTLLILTVFGITMLLAVLAQG",
                "chain_id": "A",
                "aptamer_length": 30,
                "hotspot_residues": None,
                "n_odesign_samples": 3,
                "odesign_seeds": [42],
                "weight_egarps": 0.5,
                "weight_rhofold": 0.5},
            "expected_tool_chain": [
                "identify_protein_binding_hotspots",
                "build_odesign_aptamer_input_json",
                "run_odesign_inference",
                "extract_rna_sequence_from_cif",
                "predict_rna_tertiary_structure_with_rhofold",
                "score_rna_protein_complex_with_egarps",
            ],
            "evaluation_rubric": {"min_candidates": 1, "egarps_threshold": 0.2},
            "source": "Synthetic short peptide",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_nucleocapsid",
            "workflow": "rna_aptamer_design",
            "category": "full-length",
            "description": "Aptamer design against SARS-CoV-2 Nucleocapsid (BMC Type-II benchmark)",
            "input": {
                "protein_structure_path": "data/benchmarks/RNA-BioBench-Aptamer/structures/6m3m.pdb",
                "chain_id": "A",
                "aptamer_length": 35,
                "hotspot_residues": None,
                "n_odesign_samples": 5,
                "odesign_seeds": [42, 43],
                "weight_egarps": 0.5,
                "weight_rhofold": 0.5},
            "expected_tool_chain": [
                "identify_protein_binding_hotspots",
                "build_odesign_aptamer_input_json",
                "run_odesign_inference",
                "extract_rna_sequence_from_cif",
                "predict_rna_tertiary_structure_with_rhofold",
                "score_rna_protein_complex_with_egarps",
                "predict_rna_protein_complex_with_proteinx",
                "analyze_rna_protein_interface",
            ],
            "evaluation_rubric": {
                "min_candidates": 2,
                "egarps_threshold": 0.30,
                "rhofold_plddt_threshold": 70.0,
                "proteinx_iptm_threshold": 0.60},
            "source": "PDB 6M3M",
            "paper_reference": "doi:10.1101/2020.04.17.046920"},
        {
            "task_id": f"{wf}_003_thrombin",
            "workflow": "rna_aptamer_design",
            "category": "full-length",
            "description": "Aptamer design against human thrombin (classic TBA target)",
            "input": {
                "protein_structure_path": "data/benchmarks/RNA-BioBench-Aptamer/structures/1hao.pdb",
                "chain_id": "H",
                "aptamer_length": 30,
                "hotspot_residues": None,
                "n_odesign_samples": 5,
                "odesign_seeds": [42],
                "weight_egarps": 0.5,
                "weight_rhofold": 0.5},
            "expected_tool_chain": [
                "identify_protein_binding_hotspots",
                "build_odesign_aptamer_input_json",
                "run_odesign_inference",
                "extract_rna_sequence_from_cif",
                "predict_rna_tertiary_structure_with_rhofold",
                "score_rna_protein_complex_with_egarps",
            ],
            "evaluation_rubric": {
                "min_candidates": 2,
                "egarps_threshold": 0.30,
                "rhofold_plddt_threshold": 70.0},
            "source": "PDB 1HAO",
            "paper_reference": "pmid:8318863"},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 09 rna_small_molecule_interaction
# ═══════════════════════════════════════════════════════════════════════════════

def build_rna_small_molecule_interaction() -> None:
    wf = "09_rna_small_molecule"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "rna_small_molecule_interaction",
            "category": "basic",
            "description": "Simple RNA-small molecule interaction scoring",
            "input": {
                "rna_sequence": "GGGAAACCC",
                "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
                "rna_structure_path": None,
                "secondary_structure": None,
                "scoring_tools": ["GerNA-Bind"],
                "dataset": None,
                "split_method": None},
            "expected_tool_chain": [
                "score_rna_small_molecule_interaction_with_gerna_bind",
            ],
            "evaluation_rubric": {"binding_score_range": [0.0, 1.0]},
            "source": "Synthetic RNA + caffeine SMILES",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_multi_tool",
            "workflow": "rna_small_molecule_interaction",
            "category": "edge",
            "description": "RNA-small molecule with multiple scoring tools",
            "input": {
                "rna_sequence": "GGGAAACCCGGGAAACCC",
                "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
                "rna_structure_path": None,
                "secondary_structure": "(((...)))(((...)))",
                "scoring_tools": ["GerNA-Bind", "RNAsmol"],
                "dataset": None,
                "split_method": None},
            "expected_tool_chain": [
                "score_rna_small_molecule_interaction_with_gerna_bind",
                "score_rna_small_molecule_interaction_with_rnasmol",
            ],
            "evaluation_rubric": {"binding_score_range": [0.0, 1.0], "cross_tool_agreement": True},
            "source": "Synthetic RNA + caffeine SMILES",
            "paper_reference": None},
        {
            "task_id": f"{wf}_003_riboswitch",
            "workflow": "rna_small_molecule_interaction",
            "category": "full",
            "description": "Riboswitch-like RNA element with theophylline",
            "input": {
                "rna_sequence": "GGCUUGAUGAGUCCGAAAGGACGAAACAGA",
                "smiles": "CN1C=NC2=C1C(=O)NC(=O)N2C",
                "rna_structure_path": None,
                "secondary_structure": None,
                "scoring_tools": ["GerNA-Bind"],
                "dataset": None,
                "split_method": None},
            "expected_tool_chain": [
                "score_rna_small_molecule_interaction_with_gerna_bind",
            ],
            "evaluation_rubric": {"binding_score_range": [0.0, 1.0]},
            "source": "Synthetic riboswitch fragment",
            "paper_reference": None},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 10 aso_target_screening
# ═══════════════════════════════════════════════════════════════════════════════

def _aso_tool_chain(binding_tool: str) -> list[str]:
    """Return correct expected tool chain for ASO target screening."""
    chain = [
        "predict_rna_local_accessibility_profile_vienna",
        "compute_aso_target_accessibility_vienna",
    ]
    if binding_tool == "rnaup":
        chain.append("compute_rna_rna_interaction_vienna")
    elif binding_tool == "rnacofold":
        chain.append("compute_sirna_duplex_binding_vienna")
    return chain


def build_aso_target_screening() -> None:
    wf = "10_aso_target_screening"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "aso_target_screening",
            "category": "basic",
            "description": "ASO target screening on short synthetic transcript (defaults: 18mer, step=1, top=5, RNAup)",
            "input": {
                "target_mrna_filepath": "workspace/test_mrna.fa",
                "aso_length": 18,
                "window_step": 1,
                "top_n_windows": 5,
                "binding_evaluation_tool": "rnaup"},
            "expected_tool_chain": _aso_tool_chain("rnaup"),
            "evaluation_rubric": {"min_windows": 3, "binding_score_threshold": -10.0},
            "source": "Synthetic transcript",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_real_transcript",
            "workflow": "aso_target_screening",
            "category": "full",
            "description": "ASO screening on human EPO transcript (20mer, step=1, top=10, RNAup)",
            "input": {
                "target_mrna_filepath": "workspace/epo_mrna.fa",
                "aso_length": 20,
                "window_step": 1,
                "top_n_windows": 10,
                "binding_evaluation_tool": "rnaup"},
            "expected_tool_chain": _aso_tool_chain("rnaup"),
            "evaluation_rubric": {"min_windows": 5, "binding_score_threshold": -15.0},
            "source": "UniProt P01588",
            "paper_reference": "doi:10.1038/313806a0"},
        {
            "task_id": f"{wf}_003_cofold",
            "workflow": "aso_target_screening",
            "category": "edge",
            "description": "ASO screening with RNAcofold for duplex evaluation (18mer, step=2, top=5)",
            "input": {
                "target_mrna_filepath": "workspace/test_mrna.fa",
                "aso_length": 18,
                "window_step": 2,
                "top_n_windows": 5,
                "binding_evaluation_tool": "rnacofold"},
            "expected_tool_chain": _aso_tool_chain("rnacofold"),
            "evaluation_rubric": {"min_windows": 3, "duplex_mfe_threshold": -20.0},
            "source": "Synthetic transcript",
            "paper_reference": None},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# 11 ires_prediction
# ═══════════════════════════════════════════════════════════════════════════════

def build_ires_prediction() -> None:
    wf = "11_ires_prediction"
    tasks = [
        {
            "task_id": f"{wf}_001_basic",
            "workflow": "ires_prediction",
            "category": "basic",
            "description": "IRES prediction on synthetic 5'UTR sequence",
            "input": {
                "sequence_filepath": "workspace/test_5utr.fa",
                "iresfinder_mode": 0,
                "probability_threshold": 0.5,
                "window_size": 50,
                "step_size": 10,
                "top_n_candidates": 3,
                "run_structural_validation": False},
            "expected_tool_chain": [
                "predict_ires_with_iresfinder",
            ],
            "evaluation_rubric": {"min_candidates": 1, "probability_threshold": 0.5},
            "source": "Synthetic 5'UTR",
            "paper_reference": None},
        {
            "task_id": f"{wf}_002_viral_utr",
            "workflow": "ires_prediction",
            "category": "full",
            "description": "IRES prediction on viral 5'UTR (EMCV-like)",
            "input": {
                "sequence_filepath": "workspace/viral_5utr.fa",
                "iresfinder_mode": 1,
                "probability_threshold": 0.6,
                "window_size": 100,
                "step_size": 20,
                "top_n_candidates": 5,
                "run_structural_validation": True},
            "expected_tool_chain": [
                "predict_ires_with_iresfinder",
                "predict_rna_secondary_structure_with_viennarna",
            ],
            "evaluation_rubric": {"min_candidates": 2, "probability_threshold": 0.6},
            "source": "Synthetic viral 5'UTR",
            "paper_reference": None},
        {
            "task_id": f"{wf}_003_mode2",
            "workflow": "ires_prediction",
            "category": "edge",
            "description": "IRES prediction mode 2 (full sequence scan)",
            "input": {
                "sequence_filepath": "workspace/test_5utr_long.fa",
                "iresfinder_mode": 2,
                "probability_threshold": 0.4,
                "window_size": 50,
                "step_size": 25,
                "top_n_candidates": 5,
                "run_structural_validation": False},
            "expected_tool_chain": [
                "predict_ires_with_iresfinder",
            ],
            "evaluation_rubric": {"min_candidates": 1, "probability_threshold": 0.4},
            "source": "Synthetic long 5'UTR",
            "paper_reference": None},
    ]
    for t in tasks:
        save_task(wf, t["task_id"], t)


# ═══════════════════════════════════════════════════════════════════════════════
# Manifest
# ═══════════════════════════════════════════════════════════════════════════════

def build_manifest() -> None:
    import time
    manifest = {
        "dataset_name": "RNA-BioBench-Platform",
        "schema_version": "1.0.0",
        "description": "Platform coverage benchmark: 11 workflows x 3-5 canonical test cases",
        "created_date": time.strftime("%Y-%m-%d"),
        "workflows": [
            {"id": "01_mrna_cds_design", "name": "mRNA CDS Design", "task_count": 4},
            {"id": "02_full_length_mrna_design", "name": "Full-Length mRNA Design", "task_count": 5},
            {"id": "03_mrna_sequence_scoring", "name": "mRNA Sequence Scoring", "task_count": 3},
            {"id": "04_sirna_design", "name": "siRNA Design", "task_count": 4},
            {"id": "05_sgrna_design", "name": "sgRNA Design", "task_count": 3},
            {"id": "06_rna_secondary_structure", "name": "RNA Secondary Structure Design", "task_count": 3},
            {"id": "07_rna_tertiary_structure", "name": "RNA Tertiary Structure Design", "task_count": 2},
            {"id": "08_rna_aptamer_design", "name": "RNA Aptamer Design", "task_count": 3},
            {"id": "09_rna_small_molecule", "name": "RNA-Small Molecule Interaction", "task_count": 3},
            {"id": "10_aso_target_screening", "name": "ASO Target Screening", "task_count": 3},
            {"id": "11_ires_prediction", "name": "IRES Prediction", "task_count": 3},
        ],
        "total_tasks": 36,
        "task_categories": {
            "basic": "Canonical inputs for smoke testing",
            "edge": "Mixed-modality or boundary-case inputs",
            "full": "Real biological sequences/structures",
            "full-length": "Multi-module tasks requiring BMC"}}
    path = BASE / "benchmark_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\n  [saved] {path}")


if __name__ == "__main__":
    print("Building RNA-BioBench-Platform benchmark tasks...")
    build_mrna_cds_design()
    build_full_length_mrna_design()
    build_mrna_sequence_scoring()
    build_sirna_design()
    build_sgrna_design()
    build_rna_secondary_structure_design()
    build_rna_tertiary_structure_design()
    build_rna_aptamer_design()
    build_rna_small_molecule_interaction()
    build_aso_target_screening()
    build_ires_prediction()
    build_manifest()
    print("\nDone!")
