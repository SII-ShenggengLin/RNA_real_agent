"""Workflow–Critic registry.

Each entry is a ``(workflow_class, critic_class)`` pair so that
``ExecutionController`` can look up the correct critic automatically.

NOTE: The following workflows intentionally have NO critic paired and are
therefore omitted from WORKFLOW_CRITIC_PAIRS:

- ``mrna_sequence_scoring`` — deterministic ranking from fixed inputs.
  MrnaSequenceScoringWorkflow INTERFACE LOCK (v1.0.0):
  关联文件清单见 agent_core/workflows/mrna_sequence_scoring.py 顶部的
  INTERFACE LOCK 注释。
- ``aso_target_screening`` — deterministic evaluation-only pipeline
  (RNAplfold + RNAup/RNAcofold on the same transcript always yields the
  same result); retry would only waste compute.
  AsoTargetScreeningWorkflow INTERFACE LOCK (v1.0.0):
  关联文件清单见 agent_core/workflows/aso_target_screening.py 顶部的
  INTERFACE LOCK 注释。
- ``rna_small_molecule_interaction`` — prediction/scoring task with fixed
  inputs (RNA + SMILES); re-running produces identical results.

``mrna_cds_design`` IS registered with ``MrnaCdsDesignLLMCritic``.
The critic evaluates candidate diversity and parameter tuning opportunities
(e.g., adjusting LinearDesign λ or switching tools).

``full_length_mrna_design`` IS registered with ``FullLengthMrnaDesignLLMCritic``.
The critic focuses on whether candidate UTR combinations and overall metrics
match user-specified constraints (UTR length mode, CAI/MFE preferences, IRES
tolerance). CDS-level concerns are propagated to the nested CDS sub-workflow
via parameter overrides (design_tool, lambda_value, etc.).

╔═══════════════════════════════════════════════════════════════════════════════╗
║  RnaSmallMoleculeInteractionWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  rna_small_molecule_interaction 在 WORKFLOW_CRITIC_PAIRS 中被故意省略（无     ║
║  critic）。增删/更换 critic 配对必须同步更新：                                ║
║                                                                               ║
║    - agent_core/workflows/rna_small_molecule_interaction.py                   ║
║    - agent_core/workflows/registry.py  ← 本文件                               ║
║    - agent_core/runner.py                                                     ║
║    - 相关测试文件                                                               ║
║                                                                               ║
║  关联文件清单见 agent_core/workflows/rna_small_molecule_interaction.py 顶部的 ║
║  INTERFACE LOCK 注释。                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════════════╗
║  FullLengthMrnaDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件中的 WORKFLOW_CRITIC_PAIRS 注册了 full_length_mrna_design 的 critic  ║
║  配对。任何修改（增删配对、更换 critic 类）必须同步更新：                     ║
║                                                                               ║
║    - agent_core/workflows/full_length_mrna_design.py                          ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/workflows/__init__.py                                         ║
║    - 相关测试文件                                                               ║
║                                                                               ║
║  关联文件清单见 agent_core/workflows/full_length_mrna_design.py 顶部的        ║
║  INTERFACE LOCK 注释。                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import Any, Dict, Tuple, Type

from agent_core.planning.base import Critic
# WorkflowResult not used directly; only class types are referenced
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignLLMCritic,
    FullLengthMrnaDesignWorkflow,
)
from agent_core.workflows.ires_prediction import (
    IresPredictionLLMCritic,
    IresPredictionWorkflow,
)
from agent_core.workflows.mrna_cds_design import (
    MrnaCdsDesignLLMCritic,
    MrnaCdsDesignWorkflow,
)
from agent_core.workflows.rna_aptamer_design import (
    RnaAptamerDesignLLMCritic,
    RnaAptamerDesignWorkflow,
)
from agent_core.workflows.rna_secondary_structure_design import (
    RnaSecondaryStructureDesignLLMCritic,
    RnaSecondaryStructureDesignWorkflow,
)
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignLLMCritic,
    RnaTertiaryStructureDesignWorkflow,
)
from agent_core.workflows.sgrna_design import SgRnaDesignWorkflow, SgRnaDesignLLMCritic
from agent_core.workflows.sirna_design import SirnaDesignWorkflow, SirnaDesignLLMCritic

#: Mapping of workflow step target → (workflow_class, critic_class).
#: Workflows without a critic are omitted; ExecutionController treats
#: missing entries as "no critic → no retry".
#:
#: NOTE: ``mrna_sequence_scoring`` intentionally has NO critic (deterministic
#: scoring from fixed inputs).  Its INTERFACE LOCK is documented in
#: agent_core/workflows/mrna_sequence_scoring.py.
WORKFLOW_CRITIC_PAIRS: Dict[str, Tuple[Type[Any], Type[Critic]]] = {
    "mrna_cds_design": (MrnaCdsDesignWorkflow, MrnaCdsDesignLLMCritic),
    "sirna_design": (SirnaDesignWorkflow, SirnaDesignLLMCritic),
    "sgrna_design": (SgRnaDesignWorkflow, SgRnaDesignLLMCritic),
    # RnaAptamerDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更
    # 关联文件清单见 agent_core/workflows/rna_aptamer_design.py 顶部的
    # INTERFACE LOCK 注释。增删/更换 critic 必须同步更新全部关联文件。
    "rna_aptamer_design": (RnaAptamerDesignWorkflow, RnaAptamerDesignLLMCritic),
    "ires_prediction": (IresPredictionWorkflow, IresPredictionLLMCritic),
    # RnaSecondaryStructureDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更
    # 关联文件清单见 agent_core/workflows/rna_secondary_structure_design.py 顶部的
    # INTERFACE LOCK 注释。增删/更换 critic 必须同步更新全部关联文件。
    "rna_secondary_structure_design": (RnaSecondaryStructureDesignWorkflow, RnaSecondaryStructureDesignLLMCritic),
    # RnaTertiaryStructureDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更
    # 关联文件清单见 agent_core/workflows/rna_tertiary_structure_design.py 顶部的
    # INTERFACE LOCK 注释。增删/更换 critic 必须同步更新全部关联文件。
    "rna_tertiary_structure_design": (RnaTertiaryStructureDesignWorkflow, RnaTertiaryStructureDesignLLMCritic),
    "full_length_mrna_design": (FullLengthMrnaDesignWorkflow, FullLengthMrnaDesignLLMCritic),
}


def get_critic_for_workflow(workflow_name: str) -> Critic | None:
    """Instantiate the critic registered for *workflow_name*, if any."""
    pair = WORKFLOW_CRITIC_PAIRS.get(workflow_name)
    if pair is None:
        return None
    return pair[1]()
