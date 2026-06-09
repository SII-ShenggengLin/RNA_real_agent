#!/usr/bin/env python3
"""Build RNA-BioBench-ProcessAware dataset for cross-LLM behavior analysis."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent / "RNA-BioBench-ProcessAware"


def build_task_set() -> None:
    """Select representative tasks from Platform benchmark for LLM comparison."""
    
    # Representative task IDs (subset of Platform benchmark)
    # v1.2.0: 24 tasks covering all 11 workflows with diverse query types
    task_set = {
        "dataset_name": "RNA-BioBench-ProcessAware",
        "schema_version": "1.2.0",
        "description": (
            "Process-aware behavior analysis task set with natural-language queries. "
            "Same NL queries run across 6 LLM backends to measure process metrics vs accuracy. "
            "Each task includes a user_query (natural language), a source_task (gold structured input), "
            "and an expected_workflow for validation. v1.2.0 adds 12 tasks (total 24), fixes source_task "
            "mismatches, and covers all 11 workflows including rna_tertiary_structure_design and mrna_sequence_scoring."
        ),
        "created_date": time.strftime("%Y-%m-%d"),
        "task_count": 24,
        "tasks": [
            # --- mrna_cds_design (3 tasks) ---
            {
                "task_id": "PA_001",
                "workflow": "mrna_cds_design",
                "source_task": "01_mrna_cds_design_002",
                "description": "Human GFP CDS optimization with LinearDesign",
                "rationale": "Therapeutic reporter; tests tool chain correctness",
                "user_query": "请为人类的绿色荧光蛋白（GFP）设计最优的 mRNA CDS。使用 LinearDesign 工具，在 MFE 和 CAI 之间取平衡，密码子偏好针对人类优化。",
                "query_type": "explicit",
                "expected_workflow": "mrna_cds_design",
            },
            {
                "task_id": "PA_002",
                "workflow": "mrna_cds_design",
                "source_task": "01_mrna_cds_design_004",
                "description": "GFP CDS optimization for yeast expression",
                "rationale": "Cross-species codon usage; tests species-aware parsing",
                "user_query": "我要在酵母里表达 GFP，帮我优化一下它的 mRNA 编码序列，用酵母的密码子偏好表。",
                "query_type": "cross_species",
                "expected_workflow": "mrna_cds_design",
            },
            {
                "task_id": "PA_015",
                "workflow": "mrna_cds_design",
                "source_task": "01_mrna_cds_design_003",
                "description": "SARS-CoV-2 Spike CDS with CAI-priority",
                "rationale": "Tests lambda parameter inference from user intent; long vaccine target",
                "user_query": "我要表达 SARS-CoV-2 的 Spike 蛋白，请用 LinearDesign 设计 CDS，优先保证翻译效率（CAI），lambda 设高一些。",
                "query_type": "therapeutic_intent",
                "expected_workflow": "mrna_cds_design",
            },
            # --- full_length_mrna_design (4 tasks) ---
            {
                "task_id": "PA_003",
                "workflow": "full_length_mrna_design",
                "source_task": "02_full_length_mrna_design_002_vaccine_spike",
                "description": "SARS-CoV-2 Spike full-length mRNA vaccine",
                "rationale": "BMC Type-I core; tests multi-module coordination",
                "user_query": "设计一条全长 mRNA 疫苗，编码 SARS-CoV-2 的 Spike 蛋白。5'UTR 和 3'UTR 都用短序列模式，CDS 部分要兼顾稳定性和翻译效率。",
                "query_type": "explicit_multi_param",
                "expected_workflow": "full_length_mrna_design",
            },
            {
                "task_id": "PA_004",
                "workflow": "full_length_mrna_design",
                "source_task": "02_full_length_mrna_design_003_therapeutic_epo",
                "description": "EPO therapeutic full-length mRNA",
                "rationale": "Therapeutic full-length; tests UTR optimization",
                "user_query": "我需要为人类的促红细胞生成素（EPO）设计一条治疗用的全长 mRNA。UTR 用中等长度，CDS 优先保证 CAI，因为治疗蛋白需要高表达。",
                "query_type": "therapeutic_intent",
                "expected_workflow": "full_length_mrna_design",
            },
            {
                "task_id": "PA_019",
                "workflow": "full_length_mrna_design",
                "source_task": "02_full_length_mrna_design_004_reporter_gfp",
                "description": "GFP full-length mRNA with long UTR",
                "rationale": "Tests reporter gene full-length design with explicit UTR mode",
                "user_query": "为 GFP 设计一条全长 mRNA，用于哺乳动物细胞中的报告基因表达。UTR 用长序列模式，lambda 取 4，兼顾稳定性和表达量。",
                "query_type": "explicit_multi_param",
                "expected_workflow": "full_length_mrna_design",
            },
            {
                "task_id": "PA_024",
                "workflow": "full_length_mrna_design",
                "source_task": "02_full_length_mrna_design_005_a1at",
                "description": "A1AT therapeutic mRNA with yeast CAI",
                "rationale": "Tests cross-species full-length design with therapeutic protein",
                "user_query": "为 alpha-1 抗胰蛋白酶（A1AT）设计全长 mRNA，用于酵母表达系统。UTR 模式用 all，lambda 取平衡值。",
                "query_type": "cross_species",
                "expected_workflow": "full_length_mrna_design",
            },
            # --- sirna_design (3 tasks) ---
            {
                "task_id": "PA_005",
                "workflow": "sirna_design",
                "source_task": "04_sirna_design_002_human_gene",
                "description": "siRNA design against human gene fragment",
                "rationale": "Tests RNAi workflow with synthetic human-like target",
                "user_query": "设计几个靶向人类 EPO 基因的 siRNA 候选序列，用于基因沉默实验。",
                "query_type": "simple_intent",
                "expected_workflow": "sirna_design",
            },
            {
                "task_id": "PA_006",
                "workflow": "sirna_design",
                "source_task": "04_sirna_design_003_with_offtarget",
                "description": "siRNA with off-target scanning",
                "rationale": "Tests multi-tool chain and safety filtering",
                "user_query": "给我设计一段 siRNA，靶向序列是 AUGCCCGGGUUUAAACCCGGGUUUAAACCCGGGUUUAAACCCGGGUUUAAACCCGGGUUUAAACCCGGGUUUAAACCCGGG，设计完成后一定要做脱靶扫描，安全性很重要。",
                "query_type": "safety_constrained",
                "expected_workflow": "sirna_design",
            },
            {
                "task_id": "PA_016",
                "workflow": "sirna_design",
                "source_task": "04_sirna_design_004_covid_target",
                "description": "siRNA design against SARS-CoV-2-like fragment",
                "rationale": "Tests antiviral siRNA design on pathogen target",
                "user_query": "针对这段 SARS-CoV-2 病毒 RNA 片段设计 siRNA，用于抗病毒研究，需要 5 条候选序列。靶向序列是 AUUAAAGGUUUAUACCUUCCCAGGUAACAAACCAACCAACUUUCGAUCUCUUGUAGAUCUGUUCUCUAAACGAACUUUAAAAUCUGUGUGGCUGUCACUCGGCUGCAUGCUUAGUGCACU。",
                "query_type": "antiviral_intent",
                "expected_workflow": "sirna_design",
            },
            # --- sgrna_design (2 tasks) ---
            {
                "task_id": "PA_007",
                "workflow": "sgrna_design",
                "source_task": "05_sgrna_design_002_with_crisot",
                "description": "sgRNA with CRISOT evaluation",
                "rationale": "Tests CRISPR design with off-target scoring",
                "user_query": "我要设计一段靶向 ATGCATGCATGCATGCATGCTGG 的 sgRNA，scaffold 用 CGTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTGCG，设计完成后用 CRISOT 做脱靶评估。",
                "query_type": "explicit_with_seed",
                "expected_workflow": "sgrna_design",
            },
            {
                "task_id": "PA_017",
                "workflow": "sgrna_design",
                "source_task": "05_sgrna_design_001_basic",
                "description": "Basic sgRNA handle design without off-target scan",
                "rationale": "Tests sgRNA design with explicit scaffold and constrained tool chain",
                "user_query": "基于以下 scaffold 序列设计 sgRNA handle：AGTTGGTAGCTAGTCCTTATGAAATGAGATGCTAGTCCGTTATCAACTGAAAAAGTGATCGATCG，生成 5 个变体，只做 CRISPR 活性评分，不做脱靶分析。",
                "query_type": "explicit_with_seed",
                "expected_workflow": "sgrna_design",
            },
            # --- rna_secondary_structure_design (2 tasks) ---
            {
                "task_id": "PA_008",
                "workflow": "rna_secondary_structure_design",
                "source_task": "06_rna_secondary_structure_003_ires_mimic",
                "description": "IRES-like structure inverse folding",
                "rationale": "Tests structure design with functional constraint",
                "user_query": "我有一个二级结构目标：(((((((...)))))))...((((...))))...，请帮我设计能折叠成这个结构的 RNA 序列。",
                "query_type": "structure_targeted",
                "expected_workflow": "rna_secondary_structure_design",
            },
            {
                "task_id": "PA_018",
                "workflow": "rna_secondary_structure_design",
                "source_task": "06_rna_secondary_structure_001_basic_hairpin",
                "description": "Simple hairpin inverse folding",
                "rationale": "Tests basic inverse folding with simple hairpin target",
                "user_query": "我想设计一个能折叠成简单发夹结构的 RNA 序列，二级结构目标是 ((((....))))，请用 ViennaRNA 的逆折叠工具帮我生成几条候选。",
                "query_type": "structure_targeted",
                "expected_workflow": "rna_secondary_structure_design",
            },
            # --- rna_tertiary_structure_design (1 task) ---
            {
                "task_id": "PA_013",
                "workflow": "rna_tertiary_structure_design",
                "source_task": "07_rna_tertiary_structure_001_basic",
                "description": "Short RNA tertiary structure design with RhoDesign",
                "rationale": "Tests tertiary structure inverse folding with single tool",
                "user_query": "我有一段 tRNA-Phe 的三级结构 PDB 文件（1EHZ），请用 RhoDesign 帮我设计出能折叠成这个结构的 RNA 序列，生成 3 条候选序列。",
                "query_type": "structure_targeted",
                "expected_workflow": "rna_tertiary_structure_design",
            },
            # --- rna_aptamer_design (2 tasks) ---
            {
                "task_id": "PA_009",
                "workflow": "rna_aptamer_design",
                "source_task": "08_rna_aptamer_design_002_nucleocapsid",
                "description": "Aptamer design against SARS-CoV-2 Nucleocapsid",
                "rationale": "BMC Type-II core; tests hotspot + ligand coupling",
                "user_query": "我想设计一个 RNA aptamer，能够特异性结合 SARS-CoV-2 的 Nucleocapsid 蛋白。请从 PDB 6M3M 的结构出发进行设计。",
                "query_type": "target_protein",
                "expected_workflow": "rna_aptamer_design",
            },
            {
                "task_id": "PA_020",
                "workflow": "rna_aptamer_design",
                "source_task": "08_rna_aptamer_design_003_thrombin",
                "description": "Aptamer design against human thrombin",
                "rationale": "Tests classic aptamer target (TBA) with structure-based design",
                "user_query": "我想设计一个 RNA aptamer 靶向人源凝血酶（thrombin），参考 PDB 1HAO 的结构，长度控制在 30 nt 左右。",
                "query_type": "target_protein",
                "expected_workflow": "rna_aptamer_design",
            },
            # --- rna_small_molecule_interaction (2 tasks) ---
            {
                "task_id": "PA_010",
                "workflow": "rna_small_molecule_interaction",
                "source_task": "09_rna_small_molecule_002_multi_tool",
                "description": "RNA-small molecule with multi-tool scoring",
                "rationale": "Tests cross-tool agreement",
                "user_query": "预测一下这段 RNA（GGGAAACCCGGGAAACCC）和咖啡因（SMILES: CN1C=NC2=C1C(=O)N(C(=O)N2C)C）之间有没有结合倾向。",
                "query_type": "interaction_prediction",
                "expected_workflow": "rna_small_molecule_interaction",
            },
            {
                "task_id": "PA_021",
                "workflow": "rna_small_molecule_interaction",
                "source_task": "09_rna_small_molecule_003_riboswitch",
                "description": "Riboswitch-theophylline interaction prediction",
                "rationale": "Tests riboswitch-ligand interaction scoring",
                "user_query": "预测这段核糖开关 RNA（GGCUUGAUGAGUCCGAAAGGACGAAACAGA）和茶碱（SMILES: CN1C=NC2=C1C(=O)NC(=O)N2C）之间是否存在结合作用。",
                "query_type": "interaction_prediction",
                "expected_workflow": "rna_small_molecule_interaction",
            },
            # --- aso_target_screening (2 tasks) ---
            {
                "task_id": "PA_011",
                "workflow": "aso_target_screening",
                "source_task": "10_aso_target_screening_002_real_transcript",
                "description": "ASO screening on human EPO",
                "rationale": "Tests screening workflow on real transcript",
                "user_query": "在人类 EPO 的 mRNA 转录本上筛选最适合 ASO 结合的区域，要求结合位点容易接近。",
                "query_type": "screening_intent",
                "expected_workflow": "aso_target_screening",
            },
            {
                "task_id": "PA_022",
                "workflow": "aso_target_screening",
                "source_task": "10_aso_target_screening_001_basic",
                "description": "Basic ASO screening on synthetic transcript",
                "rationale": "Tests basic ASO screening workflow",
                "user_query": "在一段测试用的 mRNA 转录本上筛选适合 ASO 结合的可及区域，ASO 长度 18mer，返回排名前 5 的位点。",
                "query_type": "screening_intent",
                "expected_workflow": "aso_target_screening",
            },
            # --- ires_prediction (2 tasks) ---
            {
                "task_id": "PA_012",
                "workflow": "ires_prediction",
                "source_task": "11_ires_prediction_002_mode0_structural",
                "description": "IRES prediction on synthetic 5'UTR with structural validation",
                "rationale": "Tests prediction with structural validation",
                "user_query": "检测这段 5'UTR 序列中是否存在潜在的 IRES 元件，帮助确认它是否能介导非帽依赖的翻译起始。同时做一下结构验证。",
                "query_type": "prediction_intent",
                "expected_workflow": "ires_prediction",
            },
            {
                "task_id": "PA_023",
                "workflow": "ires_prediction",
                "source_task": "11_ires_prediction_001_basic",
                "description": "Basic IRES prediction without structural validation",
                "rationale": "Tests basic IRES prediction with minimal tool chain",
                "user_query": "检测这段 5'UTR 序列中是否存在 IRES 元件，用默认参数就行，不需要做结构验证。",
                "query_type": "prediction_intent",
                "expected_workflow": "ires_prediction",
            },
            # --- mrna_sequence_scoring (1 task) ---
            {
                "task_id": "PA_014",
                "workflow": "mrna_sequence_scoring",
                "source_task": "03_mrna_sequence_scoring_003_real_mrna",
                "description": "Real mRNA sequence scoring for EPO CDS",
                "rationale": "Tests deterministic scoring workflow on real transcript",
                "user_query": "请评估这段 EPO mRNA 编码序列的质量，计算 GC 含量并用 ViennaRNA 预测二级结构。序列是 AUGGGCGUGCACGAGUGCCCCGCCUGGCUGUGGCUGCUGCUGAGCCUGCUGAGCCUGCCCCUGGGCCUGCCCGUGCUGGGCGCCCCCCCCAGACUGAUCUGCGACAGCAGAGUGCUGGAGAGAUACCUGCUGGAGGCCAAGGAGGCCGAGAACAUCACCACCGGCUGCGCCGAGCACUGCAGCCUGAACGAGAACAUCACCGUGCCCGACACCAAGGUGAACUUCUACGCCUGGAAGAGAAUGGAGGUGGGCCAGCAGGCCGUGGAGGUGUGGCAGGGCCUGGCCCUGCUGAGCGAGGCCGCCGGCGUGCUGAGAGGCCAGGCCCUGCUGGUGAACAGCAGCCAGCCCUGGGAGCCCCUGCAGCUGCACGUGGACAAGGCCGUGAGCGGCCUGAGAAGCUGACCACCCUGCUGAGAGCCCUGGGCGCCCAGAAGGAGGCCAUCAGCCCCCCCGACGCCGCCAGCGCCGCCCCCCUGAGAACCAUCACCGCCGACACCUUCAGAAAGCUGUUCAGAGUGUACAGCAACUUCCUGAGAGGCAAGCUGAAGCUGUACACCGGCGAGGCCUGCAGAACCGGCGACAGA。",
                "query_type": "scoring_intent",
                "expected_workflow": "mrna_sequence_scoring",
            },
        ],
        "llm_backends": [
            {
                "name": "DeepSeek-V4-Pro",
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
                "temperature": 0.1,
                "max_tokens": 4096,
                "notes": "Primary LLM for RosalindAgent",
            },
            {
                "name": "GPT-4",
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 4096,
                "notes": "Strong general-purpose baseline",
            },
            {
                "name": "GPT-3.5-Turbo",
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "temperature": 0.1,
                "max_tokens": 4096,
                "notes": "Faster/cheaper baseline",
            },
            {
                "name": "Claude-3.5-Sonnet",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.1,
                "max_tokens": 4096,
                "notes": "Anthropic baseline",
            },
            {
                "name": "Qwen2.5-72B",
                "provider": "alibaba",
                "model": "qwen2.5-72b-instruct",
                "temperature": 0.1,
                "max_tokens": 4096,
                "notes": "Open-weight Chinese model",
            },
            {
                "name": "Gemma-2-27B",
                "provider": "google",
                "model": "gemma-2-27b-it",
                "temperature": 0.1,
                "max_tokens": 4096,
                "notes": "Lightweight open-weight model",
            },
        ],
        "metrics": [
            {"name": "Task Accuracy", "definition": "Final output satisfies biological rubric", "scale": "binary"},
            {"name": "Tool Correctness", "definition": "Invoked tools match expected workflow gold path", "scale": "exact_match"},
            {"name": "Evidence Grounding", "definition": "Critic claims cite tool-derived values", "scale": "regex_audit"},
            {"name": "Trace Completeness", "definition": "Structured trace contains all decisions, I/O, prompts", "scale": "binary_check"},
            {"name": "Failure Rate", "definition": "Crashes / timeouts / empty returns", "scale": "binary"},
            {"name": "Latency", "definition": "End-to-end execution time", "scale": "seconds"},
            {"name": "Cost", "definition": "LLM API cost per task", "scale": "USD"},
        ],
        "expected_analysis": [
            "Correlation between Tool Correctness and Task Accuracy (expected >0.8)",
            "Trace Completeness stability across accuracy variance",
            "BMC accuracy variance < ReAct accuracy variance",
            "BMC process metrics saturate (high reliability)",
            "Cross-workflow variance in Tool Correctness (tertiary structure vs CDS design)",
            "Query type difficulty ranking: explicit > simple_intent > cross_species > structure_targeted",
        ],
    }
    
    path = BASE / "task_set_for_llm_comparison.json"
    path.write_text(json.dumps(task_set, indent=2, ensure_ascii=False))
    print(f"  [saved] {path}")


if __name__ == "__main__":
    print("Building RNA-BioBench-ProcessAware dataset...")
    build_task_set()
    print("Done!")
