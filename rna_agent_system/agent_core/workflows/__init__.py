"""Reusable workflow orchestration (mRNA ranking and future UTR/circRNA variants).

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
from agent_core.workflows.scoring import FullLengthScoringFunction

from agent_core.workflows.aso_target_screening import (
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
from agent_core.workflows.rna_aptamer_design import (
    RnaAptamerDesignInput,
    RnaAptamerDesignWorkflow,
    score_aptamer_candidate,
)
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
    "FullLengthScoringFunction",
    # Workflows
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
