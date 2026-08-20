"""siRNA design workflow — antiviral (Evitar) and generic sliding-window (Layer 2).

Antiviral mode: target FASTA → Evitar → candidate siRNAs → duplex evaluation →
    off-target scan → score → rank.

Generic mode: target sequence → sliding window (19–21 nt) → local filter →
    duplex evaluation → BLAST off-target → score → rank.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  SirnaDesignWorkflow INTERFACE LOCK (v1.3.0; v1.2.0 + asymmetry_component ranking dimension (terminal 5-bp NN end asymmetry via sirna-duplex v0.5.0; absent on older services → dimension drops pool-wide); v1.2.0 = ASF reference-point ranking over efficiency/specificity components — Borda rank_* / total_rank become diagnostics) —— 禁止单方面变更              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 sirna_design workflow 的权威实现。任何字段增删、函数签名变动、      ║
║  返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：               ║
║                                                                               ║
║    - agent_core/workflows/sirna_design.py  ← 本文件                          ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/quality_profiles/__init__.py                                  ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/agents/quality_agent.py                                       ║
║    - agent_core/agents/specialist_agent.py                                    ║
║    - agent_core/agents/pipeline_agent.py                                      ║
║    - agent_core/quality_profiles/sirna_design.py                              ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - tests/test_sirna_design_workflow.py                                      ║
║    - tests/test_sirna_workflow_api.py                                         ║
║    - tests/test_cli_sirna_entry.py                                            ║
║    - docs/INTERFACE_LOCKS.md                                                  ║
║    - docs/WORKFLOWS.md                                                        ║
║    - AGENTS.md                                                                ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.constants.species import DEFAULT_REFERENCE_SPECIES_ID, REFERENCE_SPECIES_IDS
from agent_core.file_manager import PROJECT_ROOT, read_sequence, save_sequence
from agent_core.sequence_utils import normalize_rna_sequence
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.multi_objective import apply_reference_point_ranking
from agent_core.workflows.evaluators import (
    CompositeEvaluator,
    DuplexBindingEvaluator,
    GCContentEvaluator,
    SelfStructureEvaluator,
)

_LOGGER = logging.getLogger("agent_core.workflows.sirna_design")

# Small helpers


_RC_MAP: dict[str, str] = {"A": "U", "U": "A", "G": "C", "C": "G"}


def _reverse_complement(rna_seq: str) -> str:
    """Return reverse complement of a normalized RNA sequence."""
    return "".join(_RC_MAP.get(base, base) for base in reversed(rna_seq.upper()))


def _has_consecutive_homopolymer(seq: str, max_run: int = 3) -> bool:
    """Return True if *seq* contains a run of identical bases longer than *max_run*."""
    if not seq:
        return False
    current = seq[0]
    count = 1
    for ch in seq[1:]:
        if ch == current:
            count += 1
            if count > max_run:
                return True
        else:
            current = ch
            count = 1
    return False


def _local_gc_content(seq: str) -> float:
    """Fast local GC fraction for filtering (no microservice call)."""
    if not seq:
        return 0.0
    gc = seq.count("G") + seq.count("C")
    return gc / len(seq)


# Input model — INTERFACE LOCKED (v1.0.0)
#
# Do NOT rename, remove, or narrow the type of any field without updating
# INTERFACE_LOCKS.md §10 and re-running the full test suite.


class SirnaDesignInput(BaseModel):
    """Input for the siRNA design workflow.

    DEFAULT PARAMETERS ARE CAREFULLY TUNED — DO NOT CHANGE THEM LIGHTLY.
    The defaults (mode=antiviral, candidate_count=10, maxgc=0.60, mingc=0.25,
    blast_perc_identity=90.0) are chosen by domain experts for typical use cases.
    Only override a parameter when the user EXPLICITLY requests a different value
    with clear biological justification. When in doubt, OMIT the parameter and
    let the workflow use its defaults.
    """
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
    evitar_filepath: Any = Field(default=None, description="[evitar] filepath: Workspace file path to the input FASTA file. For existing mode it is typically the reference viral genome; for predesign mode it is a multi-virus FASTA.")
    evitar_service_url: Any = Field(default='http://127.0.0.1:8016/design', description="[evitar] service_url: REST endpoint of the Evitar microservice.")
    evitar_strains_path: Any = Field(default=None, description="[evitar] strains_path: FASTA file of viral strain sequences. In existing mode it is used for cross-strain coverage; in predesign mode, if provided, it replaces the input file as the multi-strain input.")
    evitar_off_target: Any = Field(default=False, description="[evitar] off_target: Enables Evitar off-target evaluation against the transcriptome and 3'UTR FASTA files.")
    evitar_ncores: Any = Field(default=1, description="[evitar] ncores: Number of threads passed to Evitar. In existing mode it controls dividefa/select_siRNA parallelism; in predesign mode it controls the Perl threads worker pool.")
    evitar_p3utr_path: Any = Field(default=None, description="[evitar] p3utr_path: FASTA file of 3'UTR regions used for miRNA-like off-target evaluation.")
    evitar_transcriptome_path: Any = Field(default=None, description="[evitar] transcriptome_path: FASTA file of the transcriptome used for perfect/imperfect off-target evaluation.")
    evitar_weight_path: Any = Field(default=None, description="[evitar] weight_path: Gene-weight file for tissue-specific off-target scoring. Format: ENSEMBL ID, Gene Symbol, weight.")
    evitar_sumtype: Any = Field(default=None, description="[evitar] sumtype: Selection algorithm for predesign mode. Allowed values: SGAR or greedy. If omitted, upstream defaults to SGAR.")
    evitar_limitnum: Any = Field(default=None, description="[evitar] limitnum: Maximum number of siRNAs/Cas13 gRNAs to output in predesign mode. The Evitar.pl code initializes this to 50; the README documents 30. The wrapper passes None to use the upstream default.")
    evitar_repeatnum: Any = Field(default=None, description="[evitar] repeatnum: Multi-siRNA penalty factor for predesign mode. The Evitar.pl code initializes this to 2; the README documents 3. The wrapper passes None to use the upstream default.")
    evitar_pmcuff: Any = Field(default=None, description="[evitar] pmcuff: Perfect-match off-target cutoff. Default upstream value is 1. Candidates with perfect-match off-target count >= pmcuff are removed.")
    evitar_umcuff: float = Field(default=None, description="[evitar] umcuff: Imperfect-match off-target score cutoff. Default upstream value is 20.")
    evitar_mircuff: float = Field(default=None, description="[evitar] mircuff: miRNA-like off-target score cutoff. Default upstream value is 20000.")
    evitar_maxgc: float = Field(default=None, description="[evitar] maxgc: Maximal GC-content cutoff for siRNA prediction. Default upstream value is 0.6.")
    evitar_mingc: float = Field(default=None, description="[evitar] mingc: Minimal GC-content cutoff for siRNA prediction. Default upstream value is 0.25.")
    evitar_middlegc: float = Field(default=None, description="[evitar] middlegc: Suboptimal GC-content threshold. Default upstream value is 0.55. GC content between middlegc and maxgc is considered suboptimal and receives a reduced score.")
    evitar_allow_path: Any = Field(default=None, description="[evitar] allow_path: Text file with one allowed siRNA sequence per line. These sequences are forced into the predesign output when SGARallowban is used.")
    evitar_ban_path: Any = Field(default=None, description="[evitar] ban_path: Text file with one banned siRNA sequence per line. These sequences are excluded from the design output.")
    evitar_output: Any = Field(default=None, description="[evitar] output: Hidden upstream parameter that is automatically set by the Evitar microservice to a workspace file in workspace/evitar_service/. Evitar.pl requires --output.")
    evitar_temp: Any = Field(default='.temptempsi', description="[evitar] temp: Hidden upstream parameter for the temporary working directory. The microservice overrides this with a per-request UUID-named subdirectory to avoid race conditions.")
    evitar_offtargetperfect: Any = Field(default=False, description="[evitar] offtargetperfect: Hidden upstream switch parsed by Evitar.pl. When present, it acts like off-target mode for the SGAR/greedy selection step even if --offtarget is not used.")
    evitar_verifytype: Any = Field(default='perfect', description="[evitar] verifytype: Hidden upstream parameter parsed by Evitar.pl. Its value is initialized but not used in the documented execution path.")
    evitar_mutationrate: Any = Field(default=None, description="[evitar] mutationrate: Hidden upstream parameter passed to select_siRNA via -m when strains are provided. It controls mutation-rate tolerance during strain-specific filtering.")
    evitar_parameterRNAxs: Any = Field(default=None, description="[evitar] parameterRNAxs: Hidden upstream parameter appended verbatim to the portableRNAxs command when predict='rnaxs'.")
    evitar_RNAplfold: Any = Field(default=None, description="[evitar] RNAplfold: Hidden upstream parameter passed as -p to predictsiRNA or portableRNAxs, overriding RNAplfold settings.")
    evitar_offtargetwholematch: Any = Field(default=None, description="[evitar] offtargetwholematch: Hidden upstream parameter parsed by Evitar.pl but not used in the documented execution path.")
    evitar_offtargetpartmatch: Any = Field(default=None, description="[evitar] offtargetpartmatch: Hidden upstream parameter parsed by Evitar.pl but not used in the documented execution path.")
    evitar_offtargetmirna: Any = Field(default=None, description="[evitar] offtargetmirna: Hidden upstream parameter parsed by Evitar.pl but not used in the documented execution path.")
    evitar_range: Any = Field(default=None, description="[evitar] range: Hidden upstream parameter parsed by Evitar.pl but not used in the documented execution path.")
    gc_filepath: str = Field(default=None, description="[gc] filepath: Path to RNA or DNA sequence (workspace or server absolute); FASTA or plain text.")
    gc_service_url: str = Field(default='http://127.0.0.1:8020/gc-content', description="[gc] service_url: POST endpoint for GC content microservice.")
    gc_timeout_seconds: float = Field(default=120.0, description="[gc] timeout_seconds: HTTP request timeout in seconds.")
    sirna_duplex_filepath: str = Field(default=None, description="[sirna_duplex] filepath: Workspace file with two FASTA records (sense then antisense) or two plain RNA lines without headers.")
    sirna_duplex_temp_c: float = Field(default=37.0, description="[sirna_duplex] temp_c: Folding temperature (Celsius).")
    sirna_duplex_dangles: int = Field(default=2, description="[sirna_duplex] dangles: Dangling-end model.")
    sirna_duplex_no_lp: bool = Field(default=False, description="[sirna_duplex] no_lp: Disallow lonely pairs.")
    sirna_duplex_no_gu: bool = Field(default=False, description="[sirna_duplex] no_gu: Disallow GU pairs.")
    sirna_duplex_no_closing_gu: bool = Field(default=False, description="[sirna_duplex] no_closing_gu: Disallow GU closing pairs.")
    sirna_duplex_salt: Optional[float] = Field(default=None, description="[sirna_duplex] salt: Salt concentration (M).")
    sirna_duplex_no_tetra: bool = Field(default=False, description="[sirna_duplex] no_tetra: Omit special hairpin loop energies.")
    sirna_duplex_energy_model: Optional[int] = Field(default=None, description="[sirna_duplex] energy_model: Energy model index.")
    sirna_duplex_nsp: Optional[str] = Field(default=None, description="[sirna_duplex] nsp: Non-standard pair specification.")
    sirna_duplex_param_file: Optional[str] = Field(default=None, description="[sirna_duplex] param_file: Custom parameter file.")
    sirna_duplex_constraint: Optional[str] = Field(default=None, description="[sirna_duplex] constraint: Hard constraint dot-bracket string.")
    sirna_duplex_shape_file: Optional[str] = Field(default=None, description="[sirna_duplex] shape_file: Path to SHAPE reactivity data file.")
    sirna_duplex_shape_method: str = Field(default='D', description="[sirna_duplex] shape_method: SHAPE method: D, Z, or W.")
    sirna_duplex_concentrations: bool = Field(default=False, description="[sirna_duplex] concentrations: Compute equilibrium concentrations.")
    sirna_duplex_conc_a: Optional[float] = Field(default=None, description="[sirna_duplex] conc_a: Initial monomer A concentration [mol/L].")
    sirna_duplex_conc_b: Optional[float] = Field(default=None, description="[sirna_duplex] conc_b: Initial monomer B concentration [mol/L].")
    sirna_duplex_partfunc: bool = Field(default=False, description="[sirna_duplex] partfunc: Compute partition function for dimer.")
    sirna_duplex_service_url: str = Field(default='http://127.0.0.1:8003/sirna-duplex', description="[sirna_duplex] service_url: REST endpoint for ViennaRNA duplex cofold.")
    sirna_duplex_noPS: bool = Field(default=False, description="[sirna_duplex] --noPS: 微服务内部固定传入 --noPS，禁止生成 PostScript 结构图。")
    sirna_duplex_all_pf: bool = Field(default=False, description="[sirna_duplex] --all_pf: 上游 RNAcofold -a，计算 AA/BB 单体与 AB 二聚体的配分函数。")
    sirna_duplex_centroid: bool = Field(default=False, description="[sirna_duplex] --centroid: 上游 RNAcofold --centroid，计算 centroid 结构。")
    sirna_duplex_gquad: bool = Field(default=False, description="[sirna_duplex] --gquad: 上游 RNAcofold -g，考虑 G-四链体形成。")
    sirna_duplex_maxBPspan: int = Field(default=-1, description="[sirna_duplex] --maxBPspan: 上游 --maxBPspan，限制最大碱基对跨度；默认 -1 表示无限制。")
    sirna_duplex_batch: bool = Field(default=False, description="[sirna_duplex] --batch: 上游 --batch，对多条序列使用同一约束文件。")
    sirna_duplex_verbose: bool = Field(default=False, description="[sirna_duplex] --verbose: 上游 -v，输出详细日志。")
    vienna_fold_filepath: str = Field(default=None, description="[vienna_fold] filepath: Path to RNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.")
    vienna_fold_temp_c: float = Field(default=37.0, description="[vienna_fold] temp_c: Folding temperature (Celsius).")
    vienna_fold_dangles: int = Field(default=2, description="[vienna_fold] dangles: Dangling-end model.")
    vienna_fold_no_lp: bool = Field(default=False, description="[vienna_fold] no_lp: Disallow lonely pairs.")
    vienna_fold_no_gu: bool = Field(default=False, description="[vienna_fold] no_gu: Disallow GU pairs.")
    vienna_fold_no_closing_gu: bool = Field(default=False, description="[vienna_fold] no_closing_gu: Disallow GU closing pairs.")
    vienna_fold_salt: Optional[float] = Field(default=None, description="[vienna_fold] salt: Salt concentration (M).")
    vienna_fold_no_tetra: bool = Field(default=False, description="[vienna_fold] no_tetra: Omit special hairpin loop energies.")
    vienna_fold_energy_model: Optional[int] = Field(default=None, description="[vienna_fold] energy_model: Energy model index.")
    vienna_fold_nsp: Optional[str] = Field(default=None, description="[vienna_fold] nsp: Non-standard pair specification.")
    vienna_fold_param_file: Optional[str] = Field(default=None, description="[vienna_fold] param_file: Custom parameter file.")
    vienna_fold_constraint: Optional[str] = Field(default=None, description="[vienna_fold] constraint: Hard constraint dot-bracket string.")
    vienna_fold_shape_file: Optional[str] = Field(default=None, description="[vienna_fold] shape_file: Path to SHAPE reactivity data file.")
    vienna_fold_shape_method: str = Field(default='D', description="[vienna_fold] shape_method: SHAPE method: D, Z, or W.")
    vienna_fold_partfunc: bool = Field(default=False, description="[vienna_fold] partfunc: Compute partition function and centroid.")
    vienna_fold_circ: bool = Field(default=False, description="[vienna_fold] circ: Assume circular RNA.")
    vienna_fold_gquad: bool = Field(default=False, description="[vienna_fold] gquad: Include G-quadruplex formation.")
    vienna_fold_service_url: str = Field(default='http://127.0.0.1:8003/fold', description="[vienna_fold] service_url: ViennaRNA fold endpoint.")
    vienna_fold_noDP: bool = Field(default=False, description="[vienna_fold] --noDP: 上游 --noDP，禁止生成 dot-plot PostScript。")
    vienna_fold_maxBPspan: int = Field(default=-1, description="[vienna_fold] --maxBPspan: 上游 --maxBPspan，默认 -1 无限制。")
    vienna_fold_MEA: Any = Field(default=None, description="[vienna_fold] --MEA: 上游 --MEA[=gamma]，基于最大期望精度预测结构。")
    vienna_fold_batch: bool = Field(default=False, description="[vienna_fold] --batch: 上游 --batch，批量使用约束。")
    vienna_fold_canonicalBPonly: bool = Field(default=False, description="[vienna_fold] --canonicalBPonly: 上游 --canonicalBPonly，从约束中移除非规范碱基对。")
    vienna_fold_enforceConstraint: bool = Field(default=False, description="[vienna_fold] --enforceConstraint: 上游 --enforceConstraint，强制约束中圆括号表示的碱基对必须形成。")
    vienna_fold_shapeConversion: str = Field(default='O', description="[vienna_fold] --shapeConversion: 上游 --shapeConversion，SHAPE 到配对概率的转换方法。")
    vienna_fold_verbose: bool = Field(default=False, description="[vienna_fold] --verbose: 上游 -v，输出详细日志。")
    linearfold_filepath: str = Field(default=None, description="[linearfold] filepath: Path to a workspace file containing RNA sequence (plain or FASTA).")
    linearfold_beam_size: int = Field(default=100, description="[linearfold] beam_size: Beam size for LinearFold (0 = infinite beam).")
    linearfold_use_vienna: bool = Field(default=False, description="[linearfold] use_vienna: If true, request LinearFold-V (Vienna energy parameters).")
    linearfold_dangles: int = Field(default=2, description="[linearfold] dangles: Dangling-end model: 0 or 2 (LinearFold --dangles).")
    linearfold_sharpturn: bool = Field(default=False, description="[linearfold] sharpturn: Enable sharpturn in prediction.")
    linearfold_constraints: Optional[str] = Field(default=None, description="[linearfold] constraints: Optional constraint string (? . ( ) ) for constrained prediction. If provided, length must match the sequence.")
    linearfold_shape_file_path: Optional[str] = Field(default=None, description="[linearfold] shape_file_path: Optional path to SHAPE reactivity data file (mutually exclusive with constraints).")
    linearfold_service_url: str = Field(default='http://127.0.0.1:8015/fold', description="[linearfold] service_url: REST endpoint for the LinearFold microservice.")
    linearfold_fasta: bool = Field(default=False, description="[linearfold] --fasta: 上游 --fasta，声明输入为 FASTA 格式。")
    linearfold_verbose: bool = Field(default=False, description="[linearfold] --verbose: 上游 -v/--verbose，输出每个 loop 的能量。")
    blastn_filepath: str = Field(default=None, description="[blastn] filepath: Query nucleotide sequence file (workspace path or absolute on the server).")
    blastn_subject_fasta_path: Optional[str] = Field(default=None, description="[blastn] subject_fasta_path: Subject multi-FASTA path (server-side). Indexed with makeblastdb at runtime.")
    blastn_subject_db: Optional[str] = Field(default=None, description="[blastn] subject_db: Existing nucleotide BLAST database prefix path (server-side), e.g. /data/nt/ref.")
    blastn_task: str = Field(default='blastn-short', description="[blastn] task: blastn -task: blastn-short | blastn | megablast | dc-megablast.")
    blastn_evalue: float = Field(default=10.0, description="[blastn] evalue: \u671f\u671b\u503c\u9608\u503c\uff0c\u5bf9\u5e94\u4e0a\u6e38 -evalue\u3002")
    blastn_word_size: Optional[int] = Field(default=None, description="[blastn] word_size: Optional blastn -word_size (recommended for manual tuning of short queries).")
    blastn_max_target_seqs: int = Field(default=50, description="[blastn] max_target_seqs: \u6700\u591a\u62a5\u544a\u7684 subject \u5e8f\u5217\u6570\uff0c\u5bf9\u5e94\u4e0a\u6e38 -max_target_seqs\u3002")
    blastn_perc_identity: Optional[float] = Field(default=None, description="[blastn] perc_identity: Optional minimum percent identity filter passed to blastn.")
    blastn_strand: str = Field(default='both', description="[blastn] strand: blastn -strand: both | plus | minus.")
    blastn_outfmt: Optional[str] = Field(default=None, description="[blastn] outfmt: Optional blastn -outfmt argument override (default is tabular format 6).")
    blastn_service_url: str = Field(default='http://127.0.0.1:8019/blastn', description="[blastn] service_url: URL for the blast_service POST /blastn endpoint.")
    blastn_blastn_timeout_sec: int = Field(default=600, description="[blastn] blastn_timeout_sec: \u5fae\u670d\u52a1\u5185\u90e8 blastn \u547d\u4ee4\u8d85\u65f6\u65f6\u95f4\u3002")
    blastn_gapopen: int = Field(default=None, description="[blastn] -gapopen: 上游 -gapopen，打开 gap 的罚分。")
    blastn_gapextend: int = Field(default=None, description="[blastn] -gapextend: 上游 -gapextend，延伸 gap 的罚分。")
    blastn_penalty: int = Field(default=None, description="[blastn] -penalty: 上游 -penalty，错配罚分（≤0）。")
    blastn_reward: int = Field(default=None, description="[blastn] -reward: 上游 -reward，匹配奖励（≥0）。")
    blastn_dust: str = Field(default='20 64 1', description="[blastn] -dust: 上游 -dust，低复杂度过滤。")
    blastn_soft_masking: bool = Field(default=True, description="[blastn] -soft_masking: 上游 -soft_masking，将过滤位置作为软屏蔽。")
    blastn_lcase_masking: bool = Field(default=False, description="[blastn] -lcase_masking: 上游 -lcase_masking，使用大小写作为掩码。")
    blastn_max_hsps: int = Field(default=None, description="[blastn] -max_hsps: 上游 -max_hsps，每个 subject 保存的最大 HSP 数。")
    blastn_qcov_hsp_perc: float = Field(default=0.0, description="[blastn] -qcov_hsp_perc: 上游 -qcov_hsp_perc，HSP 对 query 的最小覆盖百分比。")
    blastn_culling_limit: int = Field(default=0, description="[blastn] -culling_limit: 上游 -culling_limit，若某 hit 被至少多少个更高分 hit 包围则删除。")
    blastn_best_hit_overhang: float = Field(default=None, description="[blastn] -best_hit_overhang: 上游 -best_hit_overhang，Best Hit 算法 overhang 值。")
    blastn_best_hit_score_edge: float = Field(default=None, description="[blastn] -best_hit_score_edge: 上游 -best_hit_score_edge，Best Hit 算法 score edge。")
    blastn_num_threads: int = Field(default=1, description="[blastn] -num_threads: 上游 -num_threads，并行线程数。")
    bowtie2_filepath: str = Field(default=None, description="[bowtie2] filepath: Query nucleotide sequence file (workspace path or absolute on the server).")
    bowtie2_subject_fasta_path: Optional[str] = Field(default=None, description="[bowtie2] subject_fasta_path: Subject multi-FASTA path (server-side). Indexed with bowtie2-build at runtime.")
    bowtie2_subject_index: Optional[str] = Field(default=None, description="[bowtie2] subject_index: Existing bowtie2 index prefix path (server-side).")
    bowtie2_mode: str = Field(default='local', description="[bowtie2] mode: local | end-to-end. 'local' allows soft-clipping and is preferred for short oligos.")
    bowtie2_k: int = Field(default=50, description="[bowtie2] k: Report up to <int> alignments per read.")
    bowtie2_service_url: str = Field(default='http://127.0.0.1:8024/align', description="[bowtie2] service_url: URL for the bowtie2_service POST /align endpoint.")
    bowtie2_bowtie2_timeout_sec: int = Field(default=300, description="[bowtie2] bowtie2_timeout_sec: \u5fae\u670d\u52a1\u5185\u90e8 bowtie2 \u547d\u4ee4\u8d85\u65f6\u65f6\u95f4\u3002")
    bowtie2_N: int = Field(default=0, description="[bowtie2] -N: 上游 -N，seed 中允许的最大错配数（0 或 1）。")
    bowtie2_L: int = Field(default=22, description="[bowtie2] -L: 上游 -L，seed 子串长度。")
    bowtie2_i: str = Field(default='mode-dependent', description="[bowtie2] -i: 上游 -i，seed 子串间隔函数。")
    bowtie2_ma: str = Field(default='mode-dependent', description="[bowtie2] --ma: 上游 --ma，匹配奖励。")
    bowtie2_mp: int = Field(default=6, description="[bowtie2] --mp: 上游 --mp，最大错配罚分。")
    bowtie2_rdg: str = Field(default='5,3', description="[bowtie2] --rdg: 上游 --rdg，read 端 gap 开放/延伸罚分。")
    bowtie2_rfg: str = Field(default='5,3', description="[bowtie2] --rfg: 上游 --rfg，reference 端 gap 开放/延伸罚分。")
    bowtie2_nofw: bool = Field(default=False, description="[bowtie2] --nofw: 上游 --nofw，不对 query 正链进行比对。")
    bowtie2_norc: bool = Field(default=False, description="[bowtie2] --norc: 上游 --norc，不对 query 反义链进行比对。")
    bowtie2_trim5: int = Field(default=0, description="[bowtie2] --trim5: 上游 --trim5，从 5' 端切除的碱基数。")
    bowtie2_trim3: int = Field(default=0, description="[bowtie2] --trim3: 上游 --trim3，从 3' 端切除的碱基数。")
    bowtie2_seed: int = Field(default=0, description="[bowtie2] --seed: 上游 --seed，随机数种子。")
    bowtie2_threads: int = Field(default=1, description="[bowtie2] -p/--threads: 上游 -p，并行线程数。")
    mode: Literal["antiviral", "generic"] = Field(default="antiviral", description="siRNA design mode. 'antiviral' uses Evitar for virus-targeting design; 'generic' uses a sliding-window approach on a plain target sequence.")
    target_sequence: Optional[str] = Field(
        default=None,
        description="Plain RNA/DNA sequence (generic mode primary).",
    )
    target_fasta_path: Optional[str] = Field(
        default=None,
        description="FASTA filepath (antiviral mode primary; generic fallback).",
    )
    candidate_count: int = Field(default=10, ge=1, le=100, description="Number of siRNA candidates to return.")
    off_target_scan: bool = Field(default=True, description="Whether to scan candidates against the transcriptome for off-target hits.")
    transcriptome_fasta_path: Optional[str] = Field(default=None, description="Path to the transcriptome FASTA used for off-target evaluation.")
    p3utr_path: Optional[str] = Field(default=None, description="Path to the 3'UTR FASTA used for miRNA-like off-target evaluation.")
    weight_path: Optional[str] = Field(default=None, description="Path to a tissue-specific gene-weight file for off-target scoring.")
    blast_subject_db: Optional[str] = Field(default=None, description="Existing BLAST nucleotide database prefix for off-target scan (legacy blast mode).")
    species: str = Field(
        default=DEFAULT_REFERENCE_SPECIES_ID,
        description="Species ID for auto-resolving default transcriptome. "
                    f"Supported IDs: {', '.join(REFERENCE_SPECIES_IDS)}. "
                    "See data/references/species/ for available reference files.",
    )
    evitar_mode: Literal["existing", "predesign"] = Field(
        default="existing",
        description="Evitar mode. Only used when mode='antiviral'. "
                    "'existing' for known-virus design; 'predesign' for future-virus pre-design.",
    )
    evitar_predict: Literal["predsi", "rnaxs", "multifapredsi", "CRISPR"] = Field(
        default="predsi",
        description="Evitar prediction algorithm. Only used when mode='antiviral'. "
                    "'CRISPR' is for Cas13 guide design.",
    )
    strains_path: Optional[str] = Field(default=None, description="Path to a multi-strain FASTA for cross-strain coverage in Evitar antiviral mode.")
    ncores: int = Field(default=1, description="Number of CPU threads for Evitar.")
    maxgc: float = Field(default=0.60, ge=0.0, le=1.0, description="Maximum allowed GC-content for siRNA candidates.")
    mingc: float = Field(default=0.25, ge=0.0, le=1.0, description="Minimum allowed GC-content for siRNA candidates.")
    middlegc: float = Field(default=0.45, ge=0.0, le=1.0, description="Midpoint GC-content used for suboptimal-GC scoring.")
    allow_path: Optional[str] = Field(default=None, description="File with allowed siRNA sequences to force-include in Evitar predesign mode.")
    ban_path: Optional[str] = Field(default=None, description="File with banned siRNA sequences to exclude in Evitar predesign mode.")
    blast_perc_identity: float = Field(
        default=90.0,
        ge=70.0,
        le=100.0,
        description="BLAST percent identity threshold for off-target scan.",
    )
    alignment_tool: Literal["blast", "bowtie2"] = Field(
        default="bowtie2",
        description="Alignment engine for off-target scan. 'bowtie2' is faster for short sequences; 'blast' is the legacy option.",
    )
    bowtie2_score_min: str = Field(
        default="G,10,4",
        description="Bowtie2 --score-min function. Default G,10,4 allows ~2 mismatches in 21 nt.",
    )

def compute_sirna_rank_scores(candidates: list[Candidate]) -> None:
    """Rank-based scoring across all candidates.

    For each candidate:
      1. Rank by duplex MFE (ViennaRNA RNAcofold): more negative = better → rank 1
      2. Rank by off-target count: fewer = better → rank 1
      3. total_score = rank_mfe + rank_offtarget (lower = better)
    """
    if not candidates:
        return

    def _duplex_mfe(c: Candidate) -> float:
        mfe = c.metadata.get("metrics_bundle", {}).get("duplex_mfe")
        return float(mfe) if mfe is not None else float("inf")

    def _off_target(c: Candidate) -> int:
        val = c.metadata.get("metrics_bundle", {}).get("off_target_count", 0)
        return int(val) if val is not None else 999999

    # Rank 1 = best (most negative MFE)
    sorted_mfe = sorted(enumerate(candidates), key=lambda x: _duplex_mfe(x[1]))
    mfe_ranks: dict[int, int] = {}
    for rank, (idx, _) in enumerate(sorted_mfe, start=1):
        mfe_ranks[idx] = rank

    # Rank 1 = best (fewest off-target hits)
    sorted_off = sorted(enumerate(candidates), key=lambda x: _off_target(x[1]))
    off_ranks: dict[int, int] = {}
    for rank, (idx, _) in enumerate(sorted_off, start=1):
        off_ranks[idx] = rank

    for i, candidate in enumerate(candidates):
        rank_mfe = mfe_ranks[i]
        rank_off = off_ranks[i]
        total = rank_mfe + rank_off
        mb = candidate.metadata.get("metrics_bundle", {})
        off_target = mb.get("off_target_count", 0)
        # Merge rank diagnostics alongside the per-objective components; the
        # ASF ranking layer consumes the components (ASF audit 2026-08-20).
        candidate.scores.update({
            "rank_mfe": float(rank_mfe),
            "rank_offtarget": float(rank_off),
            "total_rank": float(total),
            "off_target_count": float(off_target) if off_target is not None else 999.0,
        })


def score_sirna_candidate(metrics: dict[str, Any]) -> dict[str, Any]:
    """Legacy per-candidate scoring (kept for API compatibility).

    New workflows should call ``compute_sirna_rank_scores`` on the full
    candidate list for rank-based scoring. An unavailable duplex MFE yields
    ``None`` (ASF pool-worst imputation downstream), not 0.0 — ASF audit
    2026-08-20.
    """
    duplex_mfe = metrics.get("duplex_mfe")
    off_target = metrics.get("off_target_count", 0)

    scores: dict[str, Any] = {}

    # Efficiency: duplex MFE more negative = better; map [-40, 0] -> [0, 1]
    if duplex_mfe is not None:
        scores["efficiency_component"] = min(1.0, max(0.0, -float(duplex_mfe) / 40.0))
    else:
        scores["efficiency_component"] = None

    scores["off_target_count"] = float(off_target)
    scores["specificity_component"] = 1.0 / (1.0 + float(off_target))

    # Thermodynamic end asymmetry (kcal/mol, higher = antisense 5' end less
    # stable = preferential guide loading; Khvorova 2003 / Schwarz 2003).
    # Typical duplex end differences span roughly +/-3 kcal/mol; mapped
    # linearly so -3 -> 0, 0 -> 0.5, +3 -> 1. Absent -> None (the ASF layer
    # drops the dimension pool-wide on older service instances).
    asymmetry = metrics.get("duplex_asymmetry")
    if asymmetry is not None:
        scores["asymmetry_component"] = max(0.0, min(1.0, (float(asymmetry) + 3.0) / 6.0))
    else:
        scores["asymmetry_component"] = None
    # Legacy total_score kept for API compatibility; rank-based scoring
    # via compute_sirna_rank_scores is preferred.
    scores["total_score"] = scores["efficiency_component"]
    return scores


# Workflow — INTERFACE LOCKED (v1.0.0)
#
# Pipeline order: generate → evaluate → score → rank → WorkflowResult
# Do NOT change execution order, remove required_capabilities, or alter
# _state_writeback structure without updating INTERFACE_LOCKS.md §10.


class SirnaDesignWorkflow(BaseDomainWorkflow[SirnaDesignInput, WorkflowResult]):
    """siRNA design: antiviral (Evitar) or generic sliding-window.

    Pipeline: generate candidates → evaluate (GC + duplex + optional structure +
    off-target) → score → rank → WorkflowResult.
    """

    name = "sirna_design"
    task_type = "sirna_design"
    description = (
        "Design siRNA candidates (antiviral via Evitar or generic sliding-window) "
        "with duplex evaluation and off-target safety screening."
    )
    input_model = SirnaDesignInput
    # NOTE: Listed capabilities are runtime-optional; the workflow checks
    # ``capabilities.has()`` before each invocation and degrades gracefully.
    required_capabilities = [
        "design_sirna_with_evitar",          # antiviral mode only
        "compute_rna_sequence_gc_content",   # optional GC evaluation
        "compute_sirna_duplex_binding_vienna",  # optional duplex MFE
        "predict_rna_secondary_structure",   # optional self-structure (fallback)
        "predict_rna_secondary_structure_with_linearfold",  # optional self-structure (primary)
        "run_blastn_similarity_search",      # optional off-target scan (BLAST)
        "run_bowtie2_short_alignment",       # optional off-target scan (Bowtie2, faster)
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._trace_records: list[ToolCallRecord] = []
        self.evaluator = CompositeEvaluator([
            GCContentEvaluator(self.capabilities),
            DuplexBindingEvaluator(self.capabilities),
            SelfStructureEvaluator(self.capabilities),
        ])

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any, *, progress_callback=None) -> WorkflowResult:
        """Accept ``SirnaDesignInput`` or a plain dict.

        Delegates the standard generate → evaluate → score → rank pipeline to
        :meth:`BaseDomainWorkflow.run`, moving siRNA-specific GC filtering and
        rank-based scoring into :meth:`rank_and_format` so future base-class
        logic is inherited automatically.
        """
        if isinstance(inp, dict):
            inp = SirnaDesignInput(**inp)
        self._workflow_state = {"_sirna_input": inp}
        self._trace_records = []

        result = super().run(inp, progress_callback=progress_callback)

        # Attach workflow-level state writeback (base.run() already aggregates
        # per-candidate tool records into result.trace).
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: SirnaDesignInput) -> list[Candidate]:
        if inp.mode == "antiviral":
            return self._generate_antiviral(inp)
        return self._generate_generic(inp)

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        seq = candidate.sequence
        filepath = save_sequence(seq, prefix="sirna")
        candidate.metadata["workspace_filepath"] = filepath

        context = {"workflow_state": self._workflow_state}
        metrics = self.evaluator.evaluate(candidate, context)
        metrics["sequence_length"] = len(seq)

        # ── Off-target scan (domain-specific, kept in workflow) ──
        off_target_count = 0
        if candidate.metadata.get("off_target_scan", True):
            off_target_count = self._evaluate_off_target(candidate, filepath)
        metrics["off_target_count"] = off_target_count
        metrics["specificity_score"] = 1.0 / (1.0 + float(off_target_count))

        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Legacy hook; actual scoring is done in ``run`` via ``compute_sirna_rank_scores``."""
        return score_sirna_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No candidates produced.")

        # Apply the siRNA GC filter using the input cached in workflow state.
        inp = self._workflow_state.get("_sirna_input")
        if inp is not None:
            passing: list[Candidate] = []
            for c in candidates:
                metrics = c.metadata.get("metrics_bundle", {})
                gc_content = metrics.get("gc_content")
                if gc_content is not None and not (inp.mingc <= gc_content <= inp.maxgc):
                    c.status = "gc_rejected"
                    _LOGGER.info(
                        "sirna_gc_rejected seq=%s gc=%.3f range=[%.2f,%.2f]",
                        c.sequence, gc_content, inp.mingc, inp.maxgc,
                    )
                else:
                    c.status = "evaluated"
                    passing.append(c)
            _LOGGER.info(
                "workflow_gc_filter total=%d passing=%d rejected=%d",
                len(candidates), len(passing), len(candidates) - len(passing),
            )
        else:
            # Fallback when rank_and_format is invoked outside of run().
            passing = list(candidates)
            for c in passing:
                c.status = "evaluated"

        if not passing:
            return WorkflowResult(
                success=False,
                task_id="",
                summary="No candidates passed GC filter.",
                errors=["all_candidates_gc_rejected"],
            )

        # Rank-based diagnostics across passing candidates only.
        compute_sirna_rank_scores(passing)
        _LOGGER.info("workflow_evaluation_complete count=%d workflow=%s", len(passing), self.name)

        # ASF reference-point ranking over the three heterogeneous objectives
        # (duplex efficiency, specificity, thermodynamic end asymmetry); the
        # Borda rank diagnostics above are retained but no longer drive the
        # ordering (ASF audit 2026-08-20; asymmetry dimension added the same
        # day via the sirna-duplex end-thermodynamics extension).
        _ASF_OBJECTIVES = ("efficiency_component", "specificity_component", "asymmetry_component")
        for c in passing:
            if c.scores.get("efficiency_component") is None or c.scores.get("specificity_component") is None:
                c.scores.update(score_sirna_candidate(c.metadata.get("metrics_bundle", {})))
        ranking = apply_reference_point_ranking(
            passing, list(_ASF_OBJECTIVES), None,
            maximize={key: True for key in _ASF_OBJECTIVES},
        )
        if ranking.dropped_dims:
            _LOGGER.warning(
                "sirna_asf_ranking_note dropped_dims(unmeasured)=%s", ranking.dropped_dims
            )

        # Rank the FULL passing pool first, then truncate to candidate_count:
        # the returned top-N are the globally best-N candidates (the earlier
        # truncate-then-rank order could drop a window beyond position N in
        # generation order before it was ever ranked — ASF audit follow-up,
        # 2026-08-20).
        ranked = sorted(
            passing, key=lambda c: ranking.asf_map.get(c.id, float("inf"))
        )
        if inp is not None and len(ranked) > inp.candidate_count:
            ranked = ranked[:inp.candidate_count]
        for i, c in enumerate(ranked, start=1):
            c.rank = i
            c.scores["asf_distance"] = ranking.asf_map.get(c.id)
        best = ranked[0] if ranked else None

        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            parts = [
                f"#{i}",
                f"source={c.source}",
                f"len={len(c.sequence)}nt",
                f"GC={mb.get('gc_content'):.3f}" if mb.get("gc_content") is not None else "GC=N/A",
                f"duplexMFE={mb.get('duplex_mfe'):.2f}" if mb.get('duplex_mfe') is not None else "duplexMFE=N/A",
                f"offTarget={mb.get('off_target_count', 0)}",
                f"spec={mb.get('specificity_score', 0):.3f}",
                f"asy={mb['duplex_asymmetry']:+.2f}" if mb.get("duplex_asymmetry") is not None else "asy=N/A",
                f"total_rank={scores.get('total_rank', 0.0):.3f}",
                f"asf={scores['asf_distance']:.4f}" if scores.get("asf_distance") is not None else "asf=N/A",
            ]
            # Generic mode extra info
            if "window_start" in c.metadata:
                parts.insert(2, f"pos={c.metadata['window_start']}-{c.metadata['window_end']}")
            detail_lines.append(" | ".join(parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_asf_distance={best.scores.get('asf_distance') if best else None}",
            "---",
            *detail_lines,
        ]
        result = WorkflowResult(
            success=True,
            task_id=f"sirna_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )
        # Workflow-level trace records come first; base.run() appends per-candidate
        # tool records after rank_and_format returns.
        result.trace.extend(self._trace_records)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Candidate generation — antiviral branch
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_antiviral(self, inp: SirnaDesignInput) -> list[Candidate]:
        # Resolve target FASTA.  Evitar's `predictsiRNA` unconditionally
        # discards the first input line as a FASTA header, so the file must
        # contain a proper `>` header or the whole sequence is lost.
        fasta_path = inp.target_fasta_path
        if not fasta_path and inp.target_sequence:
            seq = "".join(inp.target_sequence.split())
            fasta_path = save_sequence(f">sirna_target\n{seq}\n", prefix="sirna_target")
            _LOGGER.info("sirna_antiviral_sequence_saved path=%s", fasta_path)
        if not fasta_path:
            _LOGGER.error("sirna_antiviral_no_target")
            return []

        if not self.capabilities.has("design_sirna_with_evitar"):
            _LOGGER.error("capability_missing design_sirna_with_evitar")
            return []

        args: dict[str, Any] = {
            "filepath": fasta_path,
            "mode": inp.evitar_mode,
            "predict": inp.evitar_predict,
            "ncores": inp.ncores,
            "off_target": inp.off_target_scan,
            # GC filtering is handled uniformly in evaluate() for both branches;
            # do not pass to Evitar so generate() is filter-free.
        }
        if inp.strains_path:
            args["strains_path"] = inp.strains_path
        if inp.transcriptome_fasta_path:
            args["transcriptome_path"] = inp.transcriptome_fasta_path
        if inp.p3utr_path:
            args["p3utr_path"] = inp.p3utr_path
        if inp.weight_path:
            args["weight_path"] = inp.weight_path
        if inp.allow_path:
            args["allow_path"] = inp.allow_path
        if inp.ban_path:
            args["ban_path"] = inp.ban_path

        try:
            cap = self.capabilities.get("design_sirna_with_evitar")
            cap_result = cap.invoke(args, state=self._workflow_state)

            # Record Evitar tool call in workflow-level trace
            record = ToolCallRecord(
                step_name="generate_antiviral_evitar",
                tool_name="design_sirna_with_evitar",
                input_summary=json.dumps(args, default=str),
                output_summary=json.dumps(cap_result.output, default=str)[:500],
                success=cap_result.success,
                error=cap_result.error,
                elapsed_time=getattr(cap_result, "elapsed_time", 0.0),
                artifacts=dict(cap_result.output) if cap_result.success else {},
                metrics={"top_results_count": len(cap_result.output.get("top_results", []))} if cap_result.success else {},
            )
            self._trace_records.append(record)
        except Exception as exc:
            _LOGGER.error("sirna_evitar_exception err=%s", exc)
            return []

        if not cap_result.success:
            _LOGGER.error("sirna_evitar_failed error=%s", cap_result.error)
            return []

        top_results = cap_result.output.get("top_results", [])
        if not top_results:
            _LOGGER.warning("sirna_evitar_empty_results")
            return []

        candidates: list[Candidate] = []
        seen: set[str] = set()
        for idx, row in enumerate(top_results):
            seq = self._extract_sequence_from_evitar_row(row)
            if not seq or seq in seen:
                continue
            seen.add(seq)
            candidates.append(
                Candidate(
                    sequence=seq,
                    sequence_type="sirna",
                    source=f"evitar:{inp.evitar_predict}",
                    metadata={
                        "evitar_row": row,
                        "evitar_mode": inp.evitar_mode,
                        "evitar_predict": inp.evitar_predict,
                        "off_target_scan": inp.off_target_scan,
                        "target_fasta_path": fasta_path,
                    },
                )
            )
            if len(candidates) >= inp.candidate_count:
                break

        _LOGGER.info("sirna_antiviral_candidates total=%d unique=%d", len(top_results), len(candidates))
        return candidates

    # ─────────────────────────────────────────────────────────────────────────
    # Candidate generation — generic branch
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_generic(self, inp: SirnaDesignInput) -> list[Candidate]:
        # Resolve target sequence
        target_seq: Optional[str] = None
        if inp.target_sequence:
            target_seq = normalize_rna_sequence(inp.target_sequence)
        elif inp.target_fasta_path:
            try:
                raw = read_sequence(inp.target_fasta_path)
                target_seq = normalize_rna_sequence(raw)
            except Exception as exc:
                _LOGGER.error("sirna_generic_read_failed path=%s err=%s", inp.target_fasta_path, exc)
                return []

        if not target_seq:
            _LOGGER.error("sirna_generic_no_target_sequence")
            return []

        if len(target_seq) < 40:
            _LOGGER.warning("sirna_generic_sequence_too_short len=%d", len(target_seq))
            return []

        window = 21
        step = 1
        candidates: list[Candidate] = []

        for i in range(0, len(target_seq) - window + 1, step):
            sense = target_seq[i : i + window]

            # No homopolymer runs > 3
            if _has_consecutive_homopolymer(sense, max_run=3):
                continue

            # Sense should not end with A (antisense 5' should not start with U)
            if sense.endswith("A"):
                continue

            candidates.append(
                Candidate(
                    sequence=sense,
                    sequence_type="sirna",
                    source=f"sliding_window:pos={i}",
                    metadata={
                        "window_start": i,
                        "window_end": i + window,
                        "target_sequence": target_seq,
                        "off_target_scan": inp.off_target_scan,
                    },
                )
            )

        _LOGGER.info(
            "sirna_generic_candidates windows=%d kept=%d",
            len(target_seq) - window + 1,
            len(candidates),
        )
        return candidates

    # ─────────────────────────────────────────────────────────────────────────
    # Off-target evaluation
    # ─────────────────────────────────────────────────────────────────────────

    def _evaluate_off_target(self, candidate: Candidate, sirna_filepath: str) -> int:
        """Return off-target hit count. 0 if no scan performed."""
        # Antiviral mode: check if Evitar row already has off-target info
        evitar_row = candidate.metadata.get("evitar_row")
        if isinstance(evitar_row, dict):
            for key in ("off_target_hits", "offtarget_hits", "pm_hits", "um_hits"):
                val = evitar_row.get(key)
                if val is not None:
                    try:
                        return int(val)
                    except (TypeError, ValueError):
                        pass

        inp = self._workflow_state.get("_sirna_input")
        alignment_tool = getattr(inp, "alignment_tool", "blast") if inp else "blast"

        if alignment_tool == "bowtie2":
            return self._evaluate_off_target_bowtie2(candidate, sirna_filepath)
        return self._evaluate_off_target_blast(candidate, sirna_filepath)

    def _evaluate_off_target_blast(self, candidate: Candidate, sirna_filepath: str) -> int:
        """BLAST-based off-target scan."""
        if not self.capabilities.has("run_blastn_similarity_search"):
            _LOGGER.debug("blast_capability_missing skipping_off_target")
            return 0

        subject = candidate.metadata.get("blast_subject")
        if not subject:
            wf_inp = self._workflow_state.get("_sirna_input")
            if wf_inp:
                subject = getattr(wf_inp, "transcriptome_fasta_path", None) or getattr(
                    wf_inp, "blast_subject_db", None
                )
        if not subject:
            subject = self._resolve_default_transcriptome()
        if not subject:
            _LOGGER.debug("sirna_no_transcriptome_for_blast skipping")
            return 0

        perc_identity = 90.0
        inp = self._workflow_state.get("_sirna_input")
        if inp and hasattr(inp, "blast_perc_identity"):
            perc_identity = float(inp.blast_perc_identity)

        try:
            blast_args: dict[str, Any] = {
                "filepath": sirna_filepath,
                "task": "blastn-short",
                "perc_identity": perc_identity,
                "max_target_seqs": 50,
            }
            if subject.endswith(".fasta") or subject.endswith(".fa"):
                blast_args["subject_fasta_path"] = subject
            else:
                blast_args["subject_db"] = subject

            cap = self.capabilities.get("run_blastn_similarity_search")
            blast_res = cap.invoke(blast_args, state=self._workflow_state)

            blast_record = ToolCallRecord(
                step_name=f"{candidate.id}_blast_off_target",
                tool_name="run_blastn_similarity_search",
                input_summary=json.dumps(blast_args, default=str),
                output_summary=json.dumps(blast_res.output, default=str)[:500],
                success=blast_res.success,
                error=blast_res.error,
                elapsed_time=getattr(blast_res, "elapsed_time", 0.0),
                artifacts=dict(blast_res.output) if blast_res.success else {},
                metrics={"hit_count": blast_res.output.get("hit_count", 0)} if blast_res.success else {},
            )
            candidate.add_tool_record(blast_record)

            if blast_res.success:
                return int(blast_res.output.get("hit_count", 0))
            _LOGGER.warning("sirna_blast_failed error=%s", blast_res.error)
        except Exception as exc:
            _LOGGER.warning("sirna_blast_exception exc=%s", exc)
        return 0

    def _evaluate_off_target_bowtie2(self, candidate: Candidate, sirna_filepath: str) -> int:
        """Bowtie2-based off-target scan (faster for short sequences)."""
        if not self.capabilities.has("run_bowtie2_short_alignment"):
            _LOGGER.debug("bowtie2_capability_missing skipping_off_target")
            return 0

        subject = candidate.metadata.get("blast_subject")
        if not subject:
            wf_inp = self._workflow_state.get("_sirna_input")
            if wf_inp:
                subject = getattr(wf_inp, "transcriptome_fasta_path", None) or getattr(
                    wf_inp, "blast_subject_db", None
                )
        if not subject:
            subject = self._resolve_default_transcriptome()
        if not subject:
            _LOGGER.debug("sirna_no_transcriptome_for_bowtie2 skipping")
            return 0

        score_min = "G,10,4"
        inp = self._workflow_state.get("_sirna_input")
        if inp and hasattr(inp, "bowtie2_score_min"):
            score_min = str(inp.bowtie2_score_min)

        try:
            bt2_args: dict[str, Any] = {
                "filepath": sirna_filepath,
                "mode": "local",
                "k": 50,
                "score_min": score_min,
            }
            if subject.endswith(".fasta") or subject.endswith(".fa"):
                # Check for pre-built bowtie2 index to avoid rebuilding on every call
                index_prefix = subject[:-6] if subject.endswith(".fasta") else subject[:-3]
                index_path = Path(index_prefix)
                has_index = (
                    (index_path.parent / (index_path.name + ".1.bt2")).exists()
                    or (index_path.parent / (index_path.name + ".1.bt2l")).exists()
                )
                if has_index:
                    bt2_args["subject_index"] = str(index_prefix)
                else:
                    bt2_args["subject_fasta_path"] = subject
            else:
                bt2_args["subject_index"] = subject

            cap = self.capabilities.get("run_bowtie2_short_alignment")
            bt2_res = cap.invoke(bt2_args, state=self._workflow_state)

            bt2_record = ToolCallRecord(
                step_name=f"{candidate.id}_bowtie2_off_target",
                tool_name="run_bowtie2_short_alignment",
                input_summary=json.dumps(bt2_args, default=str),
                output_summary=json.dumps(bt2_res.output, default=str)[:500],
                success=bt2_res.success,
                error=bt2_res.error,
                elapsed_time=getattr(bt2_res, "elapsed_time", 0.0),
                artifacts=dict(bt2_res.output) if bt2_res.success else {},
                metrics={"hit_count": bt2_res.output.get("hit_count", 0)} if bt2_res.success else {},
            )
            candidate.add_tool_record(bt2_record)

            if bt2_res.success:
                return int(bt2_res.output.get("hit_count", 0))
            _LOGGER.warning("sirna_bowtie2_failed error=%s", bt2_res.error)
        except Exception as exc:
            _LOGGER.warning("sirna_bowtie2_exception exc=%s", exc)
        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_default_transcriptome(self) -> Optional[str]:
        """Return path to pre-installed reference transcriptome if available.

        Looks under ``data/references/species/<species>/transcripts.fa``
        relative to the project root.
        """
        inp = self._workflow_state.get("_sirna_input")
        species = getattr(inp, "species", DEFAULT_REFERENCE_SPECIES_ID) if inp else DEFAULT_REFERENCE_SPECIES_ID
        # Allow override via environment variable
        import os
        env_species = os.environ.get("RNA_AGENT_DEFAULT_SPECIES", "").strip()
        if env_species:
            species = env_species

        candidate = (
            PROJECT_ROOT
            / "data"
            / "references"
            / "species"
            / species
            / "transcripts.fa"
        )
        if candidate.exists():
            _LOGGER.info("sirna_auto_transcriptome species=%s path=%s", species, candidate)
            return str(candidate)
        _LOGGER.debug("sirna_auto_transcriptome_not_found species=%s path=%s", species, candidate)
        return None

    @staticmethod
    def _extract_sequence_from_evitar_row(row: dict[str, Any]) -> str:
        """Extract siRNA sequence from an Evitar top_results row."""
        for key in ("siRNA", "siRNA_sequence", "guide", "guide_sequence", "GuideSeq", "sequence"):
            val = row.get(key)
            if val:
                seq = normalize_rna_sequence(str(val))
                if seq:
                    return seq
        return ""

