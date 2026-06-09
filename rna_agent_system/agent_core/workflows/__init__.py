"""Reusable workflow orchestration (mRNA ranking and future UTR/circRNA variants).

╔═══════════════════════════════════════════════════════════════════════════════╗
║  FullLengthMrnaDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件导出了 full_length_mrna_design workflow 的公开 API。                   ║
║  增删导出项必须同步更新全部关联文件并重新跑通端到端测试。                       ║
║  关联文件清单见 agent_core/workflows/full_length_mrna_design.py 顶部的         ║
║  INTERFACE LOCK 注释。                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

# Evaluator and scoring framework
from agent_core.workflows.base import SubWorkflowEvaluator
from agent_core.workflows.evaluators import (
    BaseEvaluator,
    CAIEvaluator,
    CompositeEvaluator,
    CRGPTEvaluator,
    CRISOTEvaluator,
    DuplexBindingEvaluator,
    GCContentEvaluator,
    IRESEvaluator,
    RNASTOPEvaluator,
    SecondaryStructureEvaluator,
    SelfStructureEvaluator,
    UTR3StabilityEvaluator,
    UTR5MrlEvaluator,
    UnpairedFractionEvaluator,
)
from agent_core.workflows.scoring import (
    FullLengthMrnaScoringFunction,
    MrnaCdsScoringFunction,
    ScoringFunction,
    SgRnaScoringFunction,
    SirnaRankScoringFunction,
    normalize_score,
    safe_divide,
)

# AsoTargetScreeningWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/workflows/aso_target_screening.py 顶部的
# INTERFACE LOCK 注释。增删导出项必须同步更新全部关联文件。
from agent_core.workflows.aso_target_screening import (
    AsoScreeningCritic,
    AsoScreeningInput,
    AsoTargetScreeningWorkflow,
)
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.ires_prediction import (
    IresPredictionInput,
    IresPredictionWorkflow,
)
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignInput,
    FullLengthMrnaDesignWorkflow,
    score_full_length_mrna_candidate,
)
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput, MrnaCdsDesignWorkflow
# RnaAptamerDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/workflows/rna_aptamer_design.py 顶部的
# INTERFACE LOCK 注释。增删导出项必须同步更新全部关联文件。
from agent_core.workflows.rna_aptamer_design import (
    RnaAptamerDesignInput,
    RnaAptamerDesignWorkflow,
    score_aptamer_candidate,
)
# RnaSecondaryStructureDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/workflows/rna_secondary_structure_design.py 顶部的
# INTERFACE LOCK 注释。增删导出项必须同步更新全部关联文件。
from agent_core.workflows.rna_secondary_structure_design import (
    RnaSecondaryStructureDesignInput,
    RnaSecondaryStructureDesignWorkflow,
    score_secondary_structure_design_candidate,
)
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignInput,
    RnaTertiaryStructureDesignWorkflow,
    score_tertiary_structure_design_candidate,
)
# RnaSmallMoleculeInteractionWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/workflows/rna_small_molecule_interaction.py 顶部的
# INTERFACE LOCK 注释。增删导出项必须同步更新全部关联文件。
from agent_core.workflows.rna_small_molecule_interaction import (
    RnaSmallMoleculeInteractionInput,
    RnaSmallMoleculeInteractionWorkflow,
    score_rna_ligand_candidate,
)
from agent_core.workflows.sgrna_design import (
    SgRnaDesignInput,
    SgRnaDesignWorkflow,
    score_sgrna_candidate,
)
from agent_core.workflows.sirna_design import (
    SirnaDesignInput,
    SirnaDesignWorkflow,
    score_sirna_candidate,
)
# MrnaSequenceScoringWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/workflows/mrna_sequence_scoring.py 顶部的
# INTERFACE LOCK 注释。增删导出项必须同步更新全部关联文件。
from .mrna_sequence_scoring import (
    MrnaSequenceScoringInput,
    MrnaSequenceScoringWorkflow,
    run_mrna_sequence_scoring,
)

__all__ = [
    # Evaluators
    "BaseEvaluator",
    "CAIEvaluator",
    "CompositeEvaluator",
    "CRGPTEvaluator",
    "CRISOTEvaluator",
    "DuplexBindingEvaluator",
    "GCContentEvaluator",
    "IRESEvaluator",
    "RNASTOPEvaluator",
    "SecondaryStructureEvaluator",
    "SelfStructureEvaluator",
    "SubWorkflowEvaluator",
    "UTR3StabilityEvaluator",
    "UTR5MrlEvaluator",
    "UnpairedFractionEvaluator",
    # Scoring
    "FullLengthMrnaScoringFunction",
    "MrnaCdsScoringFunction",
    "ScoringFunction",
    "SgRnaScoringFunction",
    "SirnaRankScoringFunction",
    "normalize_score",
    "safe_divide",
    # Workflows
    "AsoScreeningCritic",
    "AsoScreeningInput",
    "AsoTargetScreeningWorkflow",
    "BaseDomainWorkflow",
    "IresPredictionInput",
    "IresPredictionWorkflow",
    "FullLengthMrnaDesignInput",
    "FullLengthMrnaDesignWorkflow",
    "MrnaCdsDesignInput",
    "MrnaCdsDesignWorkflow",
    "MrnaSequenceScoringInput",
    "MrnaSequenceScoringWorkflow",
    "RnaAptamerDesignInput",
    "RnaAptamerDesignWorkflow",
    "RnaSecondaryStructureDesignInput",
    "RnaSecondaryStructureDesignWorkflow",
    "RnaTertiaryStructureDesignInput",
    "RnaTertiaryStructureDesignWorkflow",
    "SgRnaDesignInput",
    "SgRnaDesignWorkflow",
    "SirnaDesignInput",
    "SirnaDesignWorkflow",
    "run_mrna_sequence_scoring",
    "score_aptamer_candidate",
    "score_full_length_mrna_candidate",
    "score_rna_ligand_candidate",
    "score_sgrna_candidate",
    "score_sirna_candidate",
    "score_secondary_structure_design_candidate",
    "score_tertiary_structure_design_candidate",
]
