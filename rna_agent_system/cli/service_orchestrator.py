"""Microservice orchestration for CLI workflow selection.

Derives the microservices each workflow requires from its ``required_capabilities``
(via ``agent_core.services.service_manager``), provides health polling, and can
launch missing services.

The low-level health/start primitives live in
``agent_core.services.service_manager`` so that workflow classes can reuse the
same logic during their own pre-flight checks.
"""

from __future__ import annotations

import logging
from pathlib import Path

from agent_core.services.service_manager import ToolServiceSpec, ensure_services_ready, get_services_for_capabilities
from agent_core.workflows import (
    AsoTargetScreeningWorkflow,
    FullLengthMrnaDesignWorkflow,
    IresPredictionWorkflow,
    MrnaCdsDesignWorkflow,
    MrnaSequenceScoringWorkflow,
    RnaAptamerDesignWorkflow,
    RnaSecondaryStructureDesignWorkflow,
    RnaSmallMoleculeInteractionWorkflow,
    RnaTertiaryStructureDesignWorkflow,
    SgRnaDesignWorkflow,
    SirnaDesignWorkflow,
)

_LOGGER = logging.getLogger("cli.service_orchestrator")

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

_WORKFLOW_CLASSES = {
    "aso_target_screening": AsoTargetScreeningWorkflow,
    "mrna_cds_design": MrnaCdsDesignWorkflow,
    "mrna_sequence_scoring": MrnaSequenceScoringWorkflow,
    "full_length_mrna_design": FullLengthMrnaDesignWorkflow,
    "rna_aptamer_design": RnaAptamerDesignWorkflow,
    "rna_secondary_structure_design": RnaSecondaryStructureDesignWorkflow,
    "rna_small_molecule_interaction": RnaSmallMoleculeInteractionWorkflow,
    "rna_tertiary_structure_design": RnaTertiaryStructureDesignWorkflow,
    "sgrna_design": SgRnaDesignWorkflow,
    "sirna_design": SirnaDesignWorkflow,
    "ires_prediction": IresPredictionWorkflow,
}


def _services_from_workflow_names(workflows: list[str]) -> list[ToolServiceSpec]:
    """Build a deduplicated list of ToolServiceSpecs from CLI workflow names.

    Services are derived from each workflow's ``required_capabilities`` so the
    CLI only starts tools the workflow actually uses.
    """
    seen: set[str] = set()
    services: list[ToolServiceSpec] = []
    for wf_name in workflows:
        wf_cls = _WORKFLOW_CLASSES.get(wf_name)
        if wf_cls is None:
            _LOGGER.warning("unknown_workflow name=%s", wf_name)
            continue
        capabilities: list[str] = getattr(wf_cls, "required_capabilities", [])
        for svc in get_services_for_capabilities(capabilities):
            if svc.service_key in seen:
                continue
            seen.add(svc.service_key)
            services.append(svc)
    return services


def ensure_multi_workflow_services_ready(
    workflows: list[str],
    timeout: int = 300,
    poll_interval: int = 5,
) -> tuple[bool, list[str]]:
    """Ensure all microservices for multiple workflows are healthy (deduplicated).

    Services shared across workflows (e.g. ViennaRNA) are started only once.

    Returns
    -------
    (all_ready, error_list)
    """
    services = _services_from_workflow_names(workflows)
    return ensure_services_ready(
        services,
        timeout=timeout,
        poll_interval=poll_interval,
        project_root=_PROJECT_ROOT,
    )


# Keep aliases of the shared primitives so existing CLI imports keep working.
__all__ = [
    "check_service_health",
    "ensure_multi_workflow_services_ready",
    "start_service",
]
