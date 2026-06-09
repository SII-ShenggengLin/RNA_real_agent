#!/usr/bin/env python3
"""Expand RNA-BioBench-Platform benchmark tasks."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent.resolve()

# Load real sequences for reuse
def load_seq(tid: str) -> str:
    p = BASE / "RNA-BioBench-FullLength-mRNA" / "targets" / f"{tid}.json"
    return json.loads(p.read_text())["protein_sequence"]

SPIKE_SEQ = load_seq("SARS-CoV-2_Spike_WT")
HA_SEQ = load_seq("Influenza_HA_H1N1")
EPO_SEQ = load_seq("EPO")
GFP_SEQ = load_seq("GFP")
LUC_SEQ = load_seq("Luciferase")


def count_tasks(wf: str) -> int:
    return len(list((BASE / "RNA-BioBench-Platform" / "tasks" / wf).glob("*.json")))


def save_task(wf: str, tid: str, data: dict) -> None:
    path = BASE / "RNA-BioBench-Platform" / "tasks" / wf / f"{tid}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"    [saved] {tid}")


def generate_supplement() -> None:
    # ── 01 mrna_cds_design (need +6 = 10) ──
    wf = "01_mrna_cds_design"
    idx = count_tasks(wf) + 1
    extras = [
        ("A1AT", "Alpha-1-antitrypsin CDS", "full", "LinearDesign", "Homo sapiens", 3.0),
        ("Transferrin", "Transferrin CDS", "full", "LinearDesign", "Homo sapiens", 2.0),
        ("Beta_galactosidase", "Beta-galactosidase CDS", "edge", "RNARL", "Escherichia coli", 2.0),
        ("Ovalbumin", "Ovalbumin CDS", "full", "LinearDesign", "Gallus gallus", 2.0),
        ("HIV-1_Env_gp120", "HIV-1 gp120 CDS", "full", "LinearDesign", "Homo sapiens", 2.0),
        ("Growth_hormone", "Growth hormone CDS", "full", "LinearDesign", "Homo sapiens", 2.0),
    ]
    for tid, desc, cat, tool, species, lam in extras:
        try:
            seq = load_seq(tid)
        except Exception as e:
            print(f"  Skip {tid}: {e}")
            continue
        save_task(wf, f"{wf}_{idx:03d}_{tid.lower()}", {
            "task_id": f"{wf}_{idx:03d}_{tid.lower()}",
            "workflow": "mrna_cds_design",
            "category": cat,
            "description": desc,
            "input": {
                "protein_sequence": seq,
                "design_tool": tool,
                "lambda_value": lam,
                "cai_species": species,
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": ["design_mrna_cds_with_lineardesign", "predict_rna_secondary_structure_with_viennarna", "compute_rna_sequence_gc_content"],
            "evaluation_rubric": {"cai_threshold": 0.80, "mfe_threshold": -100.0},
            "source": f"UniProt expansion target {tid}",
            "paper_reference": None})
        idx += 1

    # ── 02 full_length_mrna_design (need +5 = 10) ──
    wf = "02_full_length_mrna_design"
    idx = count_tasks(wf) + 1
    extras = [
        ("HIV-1_Env_gp120", "HIV-1 gp120 full-length mRNA", "full-length"),
        ("RSV_F_protein", "RSV F protein full-length mRNA", "full-length"),
        ("Zika_E_protein", "Zika E protein full-length mRNA", "full-length"),
        ("HPV16_L1", "HPV16 L1 full-length mRNA", "full-length"),
        ("Insulin", "Insulin full-length mRNA", "full-length"),
    ]
    for tid, desc, cat in extras:
        try:
            seq = load_seq(tid)
        except Exception as e:
            print(f"  Skip {tid}: {e}")
            continue
        save_task(wf, f"{wf}_{idx:03d}_{tid.lower()}", {
            "task_id": f"{wf}_{idx:03d}_{tid.lower()}",
            "workflow": "full_length_mrna_design",
            "category": cat,
            "description": desc,
            "input": {
                "protein_sequence": seq,
                "design_tool": "LinearDesign",
                "lambda_value": 2.0,
                "cai_species": "Homo sapiens",
                "utr_mode": "optimized",
                "run_fold": True,
                "run_gc": True},
            "expected_tool_chain": ["design_mrna_cds_with_lineardesign", "generate_utr_with_gemorna", "predict_rna_secondary_structure_with_viennarna", "compute_rna_sequence_gc_content"],
            "evaluation_rubric": {"junction_mfe_threshold": -15.0, "cai_threshold": 0.80},
            "source": f"UniProt expansion target {tid}",
            "paper_reference": None})
        idx += 1

    # ── 03 mrna_sequence_scoring (need +7 = 10) ──
    wf = "03_mrna_sequence_scoring"
    idx = count_tasks(wf) + 1
    seqs = [
        ("gc_rich", "GGGCGGCCGCGGCGGCGGCGGCGGCGGC", "high GC test"),
        ("au_rich", "AAAAAAAAUUUUUUUUUUUUUUUUUUUU", "high AU test"),
        ("balanced_long", "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGCAUGCGCAUGCGC", "balanced long"),
        ("repeats", "CAGCAGCAGCAGCAGCAGCAGCAGCAGCAG", "triplet repeat"),
        ("spike_fragment", SPIKE_SEQ[:200], "Spike N-terminal fragment"),
        ("ha_fragment", HA_SEQ[:150], "HA fragment"),
        ("luciferase_fragment", "AUG" + LUC_SEQ[:100], "Luciferase fragment with start"),
    ]
    for sid, seq, desc in seqs:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "mrna_sequence_scoring",
            "category": "edge",
            "description": f"Sequence scoring: {desc}",
            "input": {
                "sequence": seq,
                "gc_tool_name": "compute_rna_sequence_gc_content",
                "fold_tool_name": "predict_rna_secondary_structure_with_viennarna",
                "run_gc_tool": True,
                "run_fold_tool": True},
            "expected_tool_chain": ["compute_rna_sequence_gc_content", "predict_rna_secondary_structure_with_viennarna"],
            "evaluation_rubric": {"score_range": [0.0, 100.0]},
            "source": "Synthetic/compositional test",
            "paper_reference": None})
        idx += 1

    # ── 04 sirna_design (need +6 = 10) ──
    wf = "04_sirna_design"
    idx = count_tasks(wf) + 1
    sirna_targets = [
        ("epo_fragment2", EPO_SEQ[50:250], "EPO mid-region", "full"),
        ("gfp_fragment", GFP_SEQ[:200], "GFP fragment", "full"),
        ("luciferase_fragment", LUC_SEQ[:250], "Luciferase fragment", "full"),
        ("long_target", "AUG" + "CCCGGGAAAUUU" * 20, "Long repetitive target", "edge"),
        ("gc_rich_target", "GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC", "GC-rich target", "edge"),
        ("au_rich_target", "AAAAAAAAUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU", "AU-rich target", "edge"),
    ]
    for sid, seq, desc, cat in sirna_targets:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "sirna_design",
            "category": cat,
            "description": f"siRNA design: {desc}",
            "input": {
                "mode": "existing",
                "target_sequence": seq,
                "candidate_count": 5,
                "off_target_scan": False,
                "species": "human",
                "evitar_mode": "si",
                "evitar_predict": "predsi",
                "ncores": 1},
            "expected_tool_chain": ["design_sirna_with_evitar", "compute_rna_sequence_gc_content"],
            "evaluation_rubric": {"min_candidates": 3, "gc_range": [0.30, 0.70]},
            "source": desc,
            "paper_reference": None})
        idx += 1

    # ── 05 sgrna_design (need +7 = 10) ──
    wf = "05_sgrna_design"
    idx = count_tasks(wf) + 1
    seeds = [
        ("seed_001", "GAGUCCGAGCAGAAGAAGAA", "mcmc", 3, True, True),
        ("seed_002", "UUUAAACCCGGGAAACCCGGG", "mcmc", 2, True, False),
        ("seed_003", "AAAGGGCCCAAAGGGCCCAA", "random", 4, True, True),
        ("seed_004", "CCCGGGAAACCCGGGAAACC", "mcmc", 3, False, True),
        ("seed_005", "GGGCCCAAAGGGCCCAAAGG", "random", 5, True, False),
        ("seed_006", "AAACCCGGGAAACCCGGGAA", "mcmc", 3, True, True),
        ("seed_007", "UUUGGGCCCAAAUUUGGGCC", "mcmc", 2, True, True),
    ]
    for sid, seed, mode, mut, crgpt, crisot in seeds:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "sgrna_design",
            "category": "edge",
            "description": f"sgRNA design with seed {sid}",
            "input": {
                "seed_sequence": seed,
                "n_samples": 5,
                "mutation_number": mut,
                "sampling_mode": mode,
                "max_overlap": 5,
                "evaluate_crgpt_score": crgpt,
                "evaluate_crisot": crisot,
                "weight_nn_score": 0.5,
                "weight_crisot": 0.5},
            "expected_tool_chain": ["design_sgrna_handle_with_crgpt"] + (["score_sgrna_handle_with_crgpt"] if crgpt else []) + (["score_crispr_off_target_with_crisot"] if crisot else []),
            "evaluation_rubric": {"min_candidates": 3, "max_overlap_violations": 0},
            "source": "Synthetic seed variation",
            "paper_reference": None})
        idx += 1

    # ── 06 rna_secondary_structure_design (need +7 = 10) ──
    wf = "06_rna_secondary_structure"
    idx = count_tasks(wf) + 1
    structures = [
        ("bulge", "(((.(((...))).)))", "RNA with bulge"),
        ("internal_loop", "(((...((...))...)))", "RNA with internal loop"),
        ("pseudoknot_simple", "((((....))))", "Simple stem-loop"),
        ("long_hairpin", "((((((........))))))", "Long hairpin"),
        ("cloverleaf", "..((((...))))..((((...))))..", "Cloverleaf mimic"),
        ("triple_stem", "((((...))))((((...))))((((...))))", "Triple stem"),
        ("asymmetric", "((((...((...))...))))", "Asymmetric internal loop"),
    ]
    for sid, struct, desc in structures:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "rna_secondary_structure_design",
            "category": "edge",
            "description": desc,
            "input": {
                "target_structure": struct,
                "start_sequence": None,
                "repeats": 3,
                "num_invocations": 5,
                "temp_c": 37.0,
                "function_mode": "MFE"},
            "expected_tool_chain": ["predict_rna_secondary_structure_with_viennarna"],
            "evaluation_rubric": {"structure_match": True, "mfe_threshold": -10.0},
            "source": "Synthetic structure",
            "paper_reference": None})
        idx += 1

    # ── 07 rna_tertiary_structure_design (need +8 = 10) ──
    wf = "07_rna_tertiary_structure"
    idx = count_tasks(wf) + 1
    configs = [
        ("ribodiffusion_only", ["RiboDiffusion"], 3, 200, 1.0, 0.6, 0.4),
        ("rhodesign_high_temp", ["RhoDesign"], 3, 0.2, 0.05, 0.5, 0.5),
        ("rhodesign_low_temp", ["RhoDesign"], 5, 0.05, 0.02, 0.7, 0.3),
        ("dual_equal", ["RhoDesign", "RiboDiffusion"], 2, 0.1, 0.05, 0.5, 0.5),
        ("ribodiffusion_high_step", ["RiboDiffusion"], 2, 500, 1.2, 0.4, 0.6),
        ("rhofold_heavy", ["RhoDesign", "RiboDiffusion"], 3, 0.1, 0.05, 0.8, 0.2),
        ("rmsd_heavy", ["RhoDesign", "RiboDiffusion"], 3, 0.1, 0.05, 0.2, 0.8),
        ("all_tools", ["RhoDesign", "RiboDiffusion"], 2, 0.1, 0.05, 0.5, 0.5),
    ]
    for sid, tools, n, temp, temp_range, w_rho, w_rmsd in configs:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "rna_tertiary_structure_design",
            "category": "edge",
            "description": f"Tertiary structure design: {sid}",
            "input": {
                "structure_filepath": "workspace/test_structure.pdb",
                "secondary_structure_filepath": None,
                "design_tools": tools,
                "n_samples_per_tool": n,
                "rhodesign_temperature": temp if isinstance(temp, float) else 0.1,
                "rhodesign_temperature_range": temp_range if isinstance(temp_range, float) else 0.05,
                "ribodiffusion_sampling_steps": temp if isinstance(temp, int) else 200,
                "ribodiffusion_cond_scale": 1.0,
                "ribodiffusion_checkpoint_name": "ribodiffusion_base",
                "weight_rhofold": w_rho,
                "weight_rmsd": w_rmsd},
            "expected_tool_chain": ["generate_rna_tertiary_structure_with_rhodesign", "generate_rna_tertiary_structure_with_ribodiffusion", "predict_rna_tertiary_structure_with_rhofold"],
            "evaluation_rubric": {"mean_plddt_threshold": 65.0},
            "source": "Parameter variation test",
            "paper_reference": None})
        idx += 1

    # ── 08 rna_aptamer_design (need +7 = 10) ──
    wf = "08_rna_aptamer_design"
    idx = count_tasks(wf) + 1
    apt_targets = [
        ("vegf", "VEGF", "data/benchmarks/RNA-BioBench-Aptamer/structures/1vpf.pdb", "A", 35, [42]),
        ("lysozyme", "Lysozyme", "data/benchmarks/RNA-BioBench-Aptamer/structures/6lyz.pdb", "A", 30, [42, 43]),
        ("streptavidin", "Streptavidin", "data/benchmarks/RNA-BioBench-Aptamer/structures/1stp.pdb", "A", 30, [42]),
        ("rnase_a", "RNase A", "data/benchmarks/RNA-BioBench-Aptamer/structures/7rsa.pdb", "A", 35, [42, 43, 44]),
        ("tnf_alpha", "TNF-alpha", "data/benchmarks/RNA-BioBench-Aptamer/structures/1tnf.pdb", "A", 35, [42]),
        ("carbonic_anhydrase", "Carbonic anhydrase II", "data/benchmarks/RNA-BioBench-Aptamer/structures/1ca2.pdb", "A", 30, [42, 43]),
        ("trypsin", "Trypsin", "data/benchmarks/RNA-BioBench-Aptamer/structures/1mct.pdb", "A", 30, [42]),
    ]
    for sid, desc, pdb, chain, length, seeds in apt_targets:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "rna_aptamer_design",
            "category": "full-length",
            "description": f"Aptamer design against {desc}",
            "input": {
                "protein_structure_path": pdb,
                "chain_id": chain,
                "aptamer_length": length,
                "hotspot_residues": None,
                "n_odesign_samples": 5,
                "odesign_seeds": seeds,
                "weight_egarps": 0.5,
                "weight_rhofold": 0.5},
            "expected_tool_chain": ["identify_protein_binding_hotspots", "build_odesign_aptamer_input_json", "run_odesign_inference", "extract_rna_sequence_from_cif", "predict_rna_tertiary_structure_with_rhofold", "score_rna_protein_complex_with_egarps"],
            "evaluation_rubric": {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0},
            "source": f"PDB structure {pdb.split('/')[-1]}",
            "paper_reference": None})
        idx += 1

    # ── 08 rna_aptamer_design edge cases (+10 = 20) ──
    wf = "08_rna_aptamer_design"
    idx = count_tasks(wf) + 1
    aptamer_edge_cases = [
        # (suffix, description, pdb, chain, length, hotspot, samples, seeds, egarps_w, rhofold_w, tool_chain_extra, rubric_extra)
        ("explicit_hotspot", "explicitly provided hotspot residues", "data/benchmarks/RNA-BioBench-Aptamer/structures/1vpf.pdb", "A", 35, "A/48,A/82,A/84,A/86,A/90", 5, [42], 0.5, 0.5,
         [], {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("short_aptamer", "short aptamer (15 nt)", "data/benchmarks/RNA-BioBench-Aptamer/structures/1hao.pdb", "H", 15, None, 5, [42], 0.5, 0.5,
         [], {"min_candidates": 1, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("long_aptamer", "long aptamer (80 nt)", "data/benchmarks/RNA-BioBench-Aptamer/structures/1stp.pdb", "A", 80, None, 5, [42], 0.5, 0.5,
         [], {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("min_samples", "minimum ODesign samples (n=1)", "data/benchmarks/RNA-BioBench-Aptamer/structures/6lyz.pdb", "A", 30, None, 1, [42], 0.5, 0.5,
         [], {"min_candidates": 1, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("max_samples", "maximum ODesign samples (n=20)", "data/benchmarks/RNA-BioBench-Aptamer/structures/1mct.pdb", "A", 30, None, 20, [42], 0.5, 0.5,
         [], {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("high_binding_weight", "prioritize binding affinity (EGARPS weight 0.8)", "data/benchmarks/RNA-BioBench-Aptamer/structures/1ca2.pdb", "A", 30, None, 5, [42], 0.8, 0.15,
         [], {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("high_fold_weight", "prioritize RNA foldability (RhoFold weight 0.8)", "data/benchmarks/RNA-BioBench-Aptamer/structures/7rsa.pdb", "A", 35, None, 5, [42], 0.15, 0.8,
         [], {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("only_egarps", "binding-only scoring (EGARPS weight 1.0)", "data/benchmarks/RNA-BioBench-Aptamer/structures/1tnf.pdb", "A", 35, None, 5, [42], 1.0, 0.0,
         [], {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("dual_input", "both protein sequence and structure provided", "data/benchmarks/RNA-BioBench-Aptamer/structures/1vpf.pdb", "A", 35, None, 5, [42], 0.5, 0.5,
         [], {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0}),
        ("default_weights", "default scoring weights (EGARPS 0.33 / RhoFold 0.33)", "data/benchmarks/RNA-BioBench-Aptamer/structures/6m3m.pdb", "A", 35, None, 5, [42], 0.33, 0.33,
         ["predict_rna_protein_complex_with_proteinx", "analyze_rna_protein_interface"],
         {"min_candidates": 2, "egarps_threshold": 0.30, "rhofold_plddt_threshold": 70.0, "proteinx_iptm_threshold": 0.60}),
    ]
    for sid, desc, pdb, chain, length, hotspot, samples, seeds, egarps_w, rhofold_w, tool_chain_extra, rubric in aptamer_edge_cases:
        base_tools = ["build_odesign_aptamer_input_json", "run_odesign_inference", "extract_rna_sequence_from_cif",
                      "predict_rna_tertiary_structure_with_rhofold", "score_rna_protein_complex_with_egarps"]
        if hotspot is None:
            base_tools = ["identify_protein_binding_hotspots"] + base_tools
        tool_chain = base_tools + tool_chain_extra
        inp = {
            "protein_structure_path": pdb,
            "chain_id": chain,
            "aptamer_length": length,
            "hotspot_residues": hotspot,
            "n_odesign_samples": samples,
            "odesign_seeds": seeds,
            "weight_egarps": egarps_w,
            "weight_rhofold": rhofold_w}
        if sid == "dual_input":
            inp["protein_sequence"] = "VVKFMDVYQRSYCHPIETLVDIFQEYPDEIEYIFKPSCVPLMRCGGCCNDEGLECVPTEESNITMQIMRIKPHQGQHIGEMSFLQHNKCECRPK"
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "rna_aptamer_design",
            "category": "edge",
            "description": f"{desc} against {pdb.split('/')[-1].replace('.pdb', '')}",
            "input": inp,
            "expected_tool_chain": tool_chain,
            "evaluation_rubric": rubric,
            "source": f"PDB structure {pdb.split('/')[-1]}" if sid != "dual_input" else "PDB structure 1vpf.pdb",
            "paper_reference": None})
        idx += 1

    # ── 09 rna_small_molecule_interaction (need +7 = 10) ──
    wf = "09_rna_small_molecule"
    idx = count_tasks(wf) + 1
    interactions = [
        ("theophylline", "GGGAAACCC", "CN1C=NC2=C1C(=O)NC(=O)N2C", "Theophylline aptamer"),
        ("tetracycline", "GGGCGCAUGCGCAUACGCAUGCGCAUACGCAUGCGCCC", "CN(C)C1C2CC3CC(C2)CC1C3", "Tetracycline riboswitch"),
        ("neomycin", "GGGAAACCCGGGAAACCC", "NC1C(N)C2OC(C(O)C2O)C1O", "Aminoglycoside-RNA"),
        ("fmoc_lys", "AUGCGCAUGCGCAUGCGC", "C1=CC=C(CC(C(=O)O)NC(=O)OCC2C3=CC=CC=C3C4=CC=CC=C24)C=C1", "FMOC-Lysine analog"),
        ("guanine", "GGGAAACCC", "O=C1NC=NC2=C1NC=N2", "Guanine riboswitch"),
        ("adenine", "GGGAAACCC", "NC1=NC=NC2=C1NC=N2", "Adenine riboswitch"),
        ("spermine", "GGGCGGCCGCGGCGGCGGC", "C(CCN)CCN", "Polyamine-RNA interaction"),
    ]
    for sid, rna, smiles, desc in interactions:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "rna_small_molecule_interaction",
            "category": "edge",
            "description": desc,
            "input": {
                "rna_sequence": rna,
                "smiles": smiles,
                "rna_structure_path": None,
                "secondary_structure": None,
                "scoring_tools": ["GerNA-Bind"],
                "dataset": None,
                "split_method": None},
            "expected_tool_chain": ["score_rna_small_molecule_interaction_with_gerna_bind"],
            "evaluation_rubric": {"binding_score_range": [0.0, 1.0]},
            "source": "Literature-known interaction",
            "paper_reference": None})
        idx += 1

    # ── 10 aso_target_screening (need +7 = 10) ──
    wf = "10_aso_target_screening"
    idx = count_tasks(wf) + 1

    def _aso_tool_chain(binding_tool: str) -> list[str]:
        chain = [
            "predict_rna_local_accessibility_profile_vienna",
            "compute_aso_target_accessibility_vienna",
        ]
        if binding_tool == "rnaup":
            chain.append("compute_rna_rna_interaction_vienna")
        elif binding_tool == "rnacofold":
            chain.append("compute_sirna_duplex_binding_vienna")
        return chain

    aso_configs = [
        # (suffix, aso_length, window_step, top_n, binding_tool, category)
        ("short_15mer", 15, 1, 5, "rnacofold", "edge"),
        ("long_25mer", 25, 1, 5, "rnaup", "edge"),
        ("step_2", 22, 2, 7, "rnacofold", "edge"),
        ("step_5", 20, 5, 3, "rnaup", "edge"),
        ("rnaup_eval", 20, 1, 8, "rnaup", "edge"),
        ("rnacofold_eval", 18, 1, 5, "rnacofold", "edge"),
        ("top_10", 18, 1, 10, "rnacofold", "edge"),
    ]
    for sid, length, step, top, tool, cat in aso_configs:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "aso_target_screening",
            "category": cat,
            "description": f"ASO screening: {length}mer, step={step}, top={top}, binding_eval={tool}",
            "input": {
                "target_mrna_filepath": "workspace/test_mrna.fa",
                "aso_length": length,
                "window_step": step,
                "top_n_windows": top,
                "binding_evaluation_tool": tool},
            "expected_tool_chain": _aso_tool_chain(tool),
            "evaluation_rubric": {"min_windows": 2, "binding_score_threshold": -10.0},
            "source": "Parameter variation test",
            "paper_reference": None})
        idx += 1

    # ── 11 ires_prediction (need +7 = 10) ──
    wf = "11_ires_prediction"
    idx = count_tasks(wf) + 1
    ires_configs = [
        ("mode0_short", 0, 0.5, 50, 10, 3, False, "basic"),
        ("mode0_long_window", 0, 0.5, 100, 20, 5, False, "edge"),
        ("mode1_high_thresh", 1, 0.7, 50, 10, 3, False, "edge"),
        ("mode1_structural", 1, 0.6, 100, 20, 5, True, "full"),
        ("mode2_scan", 2, 0.4, 50, 25, 5, False, "edge"),
        ("mode0_low_thresh", 0, 0.3, 50, 10, 5, False, "edge"),
        ("mode2_long_window", 2, 0.5, 100, 50, 3, False, "edge"),
    ]
    for sid, mode, thresh, wsize, step, top, struct, cat in ires_configs:
        save_task(wf, f"{wf}_{idx:03d}_{sid}", {
            "task_id": f"{wf}_{idx:03d}_{sid}",
            "workflow": "ires_prediction",
            "category": cat,
            "description": f"IRES prediction mode={mode}, thresh={thresh}, window={wsize}",
            "input": {
                "sequence_filepath": "workspace/test_5utr.fa",
                "iresfinder_mode": mode,
                "probability_threshold": thresh,
                "window_size": wsize,
                "step_size": step,
                "top_n_candidates": top,
                "run_structural_validation": struct},
            "expected_tool_chain": ["predict_ires_with_iresfinder"] + (["predict_rna_secondary_structure_with_viennarna"] if struct else []),
            "evaluation_rubric": {"min_candidates": 1, "probability_threshold": thresh},
            "source": "Parameter variation test",
            "paper_reference": None})
        idx += 1


def update_manifest() -> None:
    tasks_dir = BASE / "RNA-BioBench-Platform" / "tasks"
    new_counts = {}
    for wf_dir in sorted(tasks_dir.iterdir()):
        if wf_dir.is_dir():
            new_counts[wf_dir.name] = len(list(wf_dir.glob("*.json")))
    
    manifest = {
        "dataset_name": "RNA-BioBench-Platform",
        "schema_version": "1.1.0",
        "description": "Platform coverage benchmark: 11 workflows x 10 canonical test cases",
        "created_date": time.strftime("%Y-%m-%d"),
        "workflows": [
            {"id": "01_mrna_cds_design", "name": "mRNA CDS Design", "task_count": new_counts.get("01_mrna_cds_design", 0)},
            {"id": "02_full_length_mrna_design", "name": "Full-Length mRNA Design", "task_count": new_counts.get("02_full_length_mrna_design", 0)},
            {"id": "03_mrna_sequence_scoring", "name": "mRNA Sequence Scoring", "task_count": new_counts.get("03_mrna_sequence_scoring", 0)},
            {"id": "04_sirna_design", "name": "siRNA Design", "task_count": new_counts.get("04_sirna_design", 0)},
            {"id": "05_sgrna_design", "name": "sgRNA Design", "task_count": new_counts.get("05_sgrna_design", 0)},
            {"id": "06_rna_secondary_structure", "name": "RNA Secondary Structure Design", "task_count": new_counts.get("06_rna_secondary_structure", 0)},
            {"id": "07_rna_tertiary_structure", "name": "RNA Tertiary Structure Design", "task_count": new_counts.get("07_rna_tertiary_structure", 0)},
            {"id": "08_rna_aptamer_design", "name": "RNA Aptamer Design", "task_count": new_counts.get("08_rna_aptamer_design", 0)},
            {"id": "09_rna_small_molecule", "name": "RNA-Small Molecule Interaction", "task_count": new_counts.get("09_rna_small_molecule", 0)},
            {"id": "10_aso_target_screening", "name": "ASO Target Screening", "task_count": new_counts.get("10_aso_target_screening", 0)},
            {"id": "11_ires_prediction", "name": "IRES Prediction", "task_count": new_counts.get("11_ires_prediction", 0)},
        ],
        "total_tasks": sum(new_counts.values()),
        "task_categories": {
            "basic": "Canonical inputs for smoke testing",
            "edge": "Mixed-modality or boundary-case inputs",
            "full": "Real biological sequences/structures",
            "full-length": "Multi-module tasks requiring BMC"}}
    (BASE / "RNA-BioBench-Platform" / "benchmark_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    print(f"\n  Updated manifest: {sum(new_counts.values())} total tasks")
    for k, v in sorted(new_counts.items()):
        print(f"    {k}: {v}")


if __name__ == "__main__":
    print("Expanding RNA-BioBench-Platform tasks...")
    generate_supplement()
    update_manifest()
    print("\nDone!")
