#!/usr/bin/env python3
"""Fig 1e: export the BMC issue → module → bounded-action rule map to JSON.

Statically consolidates the coordination rules implemented by
`ReferencePointCoordinator` (Type-I, full-length mRNA) and `AptamerCoordinator`
(Type-II, aptamer) in `agent_core/workflows/coordinator.py`, plus the bounded
clamps applied at adjustment-application time in the two workflow classes.
Each rule is written out as explicit data with the source line that evidences
it; `--check` re-verifies the data against the live source (dimension lists,
dimension→module maps, issue-type constants, clamp numbers) so the map cannot
silently drift from the code.

Output: `experiments/results/fig1_rule_map.json` with a Sankey-ready shape:
    {"nodes": [{"id", "kind", "label"}], "links": [{"source", "target", "rule"}]}
plus a machine-readable "rules" list with full detail.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/export_bmc_rule_map.py [--check]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig1_rule_map.json"
COORDINATOR = PROJECT_ROOT / "agent_core" / "workflows" / "coordinator.py"
FL_WORKFLOW = PROJECT_ROOT / "agent_core" / "workflows" / "full_length_mrna_design.py"
APT_WORKFLOW = PROJECT_ROOT / "agent_core" / "workflows" / "rna_aptamer_design.py"

# ---------------------------------------------------------------------------
# Rule data (each entry cites its source evidence; kept honest by --check)
# ---------------------------------------------------------------------------

CONVERGENCE_RULES = [
    "stop when round_num >= bmc_max_rounds (bounded)",
    "stop when round improvement < bmc_improvement_threshold",
    "stop when the best score degrades",
]

RULES = {
    "type1_full_length_mrna": {
        "coordinator": "ReferencePointCoordinator",
        "workflow": "full_length_mrna_design",
        "diagnosis": (
            "Per BMC round, the diagnosed candidate's normalized objective "
            "vector is compared against the reference point; every dimension "
            "with a positive gap emits a {DIM}_BELOW_REFERENCE issue whose "
            "violation equals the gap (coordinator.py:199-222). Hard boolean "
            "issues (AUG/Kozak burial, full_length_mrna_design.py:799/813) "
            "are appended verbatim."
        ),
        "dimensions": {
            # dim -> (modules, evidence)
            "cds_component": (["CDS"], "coordinator.py DIMENSION_TO_MODULES"),
            "utr5_mrl": (["5UTR"], "coordinator.py DIMENSION_TO_MODULES"),
            "utr3_stability": (["3UTR"], "coordinator.py DIMENSION_TO_MODULES"),
            "full_mfe_score": (["5UTR", "CDS", "3UTR"], "coordinator.py DIMENSION_TO_MODULES"),
            "junction_5utr_cds_score": (["5UTR", "CDS"], "coordinator.py DIMENSION_TO_MODULES"),
            "junction_cds_3utr_score": (["CDS", "3UTR"], "coordinator.py DIMENSION_TO_MODULES"),
        },
        "rules": [
            {
                "issue": "CDS_COMPONENT_BELOW_REFERENCE",
                "modules": ["CDS"],
                "action": "lambda_value += +2.0 if only CAI is weak; -2.0 if only MFE "
                          "is weak, if both are weak, or by default (stability first)",
                "bounded_by": "lambda_value clamped to [0, 20] at application "
                              "(full_length_mrna_design.py:1164)",
                "evidence": "coordinator.py _cds_lambda_adjustments",
            },
            {
                "issue": "FULL_MFE_SCORE_BELOW_REFERENCE",
                "modules": ["CDS"],
                "action": "same lambda_value rule as CDS_COMPONENT_BELOW_REFERENCE "
                          "(5UTR/3UTR members of this dimension receive no adjustments)",
                "bounded_by": "lambda_value clamped to [0, 20] (full_length_mrna_design.py:1164)",
                "evidence": "coordinator.py _cds_adjustments:280-284",
            },
            {
                "issue": "JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE",
                "modules": ["5UTR", "CDS"],
                "action": "no lambda change; resolved workflow-side by junction codon "
                          "shuffling (shuffle_cds_junction_codons) — UTR presets are "
                          "pinned by the user's utr_mode",
                "bounded_by": "shuffle is local to junction codons; CDS elsewhere unchanged",
                "evidence": "coordinator.py _cds_adjustments:288-294 + _module_adjustments:263-266",
            },
            {
                "issue": "JUNCTION_5UTR_CDS_AUG_BURIED",
                "modules": ["5UTR", "CDS"],
                "action": "hard burial flag; same junction codon shuffling path",
                "bounded_by": "shuffle is local to junction codons",
                "evidence": "full_length_mrna_design.py:799; coordinator.py:288-294",
            },
            {
                "issue": "JUNCTION_5UTR_CDS_KOZAK_BURIED",
                "modules": ["5UTR", "CDS"],
                "action": "hard burial flag; same junction codon shuffling path",
                "bounded_by": "shuffle is local to junction codons",
                "evidence": "full_length_mrna_design.py:813; coordinator.py:288-294",
            },
            {
                "issue": "JUNCTION_CDS_3UTR_SCORE_BELOW_REFERENCE",
                "modules": ["CDS", "3UTR"],
                "action": "no lambda change; junction codon shuffling (CDS side)",
                "bounded_by": "shuffle is local to junction codons",
                "evidence": "coordinator.py:288-294",
            },
            {
                "issue": "UTR5_MRL_BELOW_REFERENCE / UTR3_STABILITY_BELOW_REFERENCE",
                "modules": ["5UTR", "3UTR"],
                "action": "no coordinator parameter adjustments — UTR presets come "
                          "from the user's explicit utr_mode and are never overridden",
                "bounded_by": "n/a (no action issued)",
                "evidence": "coordinator.py _module_adjustments:263-266",
            },
        ],
    },
    "type2_aptamer": {
        "coordinator": "AptamerCoordinator",
        "workflow": "rna_aptamer_design",
        "diagnosis": (
            "Same reference-point gap diagnosis over the 3 aptamer objectives "
            "(coordinator.py:472-495). Feedback metrics are source-aware "
            "(worst-violation candidate) by default; APTAMER_FEEDBACK_MODE="
            "pool_average (Fig 5b) substitutes candidate-pool mean metrics."
        ),
        "dimensions": {
            "egarps_component": (["Target", "Aptamer"], "coordinator.py DIMENSION_TO_MODULES"),
            "rhofold_component": (["Aptamer"], "coordinator.py DIMENSION_TO_MODULES"),
            "iptm_component": (["Target", "Aptamer"], "coordinator.py DIMENSION_TO_MODULES"),
        },
        "rules": [
            {
                "issue": "EGARPS_COMPONENT_BELOW_REFERENCE",
                "modules": ["Target"],
                "action": "hotspot_expansion +2 (expand binding-surface window)",
                "bounded_by": "hotspot window clamped to [3, 10] (rna_aptamer_design.py:983)",
                "evidence": "coordinator.py _target_adjustments:552-565",
            },
            {
                "issue": "IPTM_COMPONENT_BELOW_REFERENCE",
                "modules": ["Target"],
                "action": "hotspot_expansion +2",
                "bounded_by": "hotspot window clamped to [3, 10] (rna_aptamer_design.py:983)",
                "evidence": "coordinator.py _target_adjustments:552-565",
            },
            {
                "issue": "RHOFOLD_COMPONENT_BELOW_REFERENCE",
                "modules": ["Aptamer"],
                "action": "aptamer_length_delta +10 if source pLDDT < 60 else +5; "
                          "plus seed_change (explore new sequence space)",
                "bounded_by": "aptamer length override capped at 200 nt (rna_aptamer_design.py:1019)",
                "evidence": "coordinator.py _aptamer_adjustments:573-592",
            },
            {
                "issue": "EGARPS_COMPONENT_BELOW_REFERENCE",
                "modules": ["Aptamer"],
                "action": "n_samples_delta +5 (more candidates); plus seed_change",
                "bounded_by": "n_odesign_samples override capped at 20 (rna_aptamer_design.py:1024)",
                "evidence": "coordinator.py _aptamer_adjustments:593-608",
            },
            {
                "issue": "IPTM_COMPONENT_BELOW_REFERENCE",
                "modules": ["Aptamer"],
                "action": "n_samples_delta +5; plus seed_change",
                "bounded_by": "n_odesign_samples override capped at 20 (rna_aptamer_design.py:1024)",
                "evidence": "coordinator.py _aptamer_adjustments:593-608",
            },
        ],
    },
}


def build_rule_map() -> dict:
    """Assemble the Sankey-ready nodes/links structure from RULES."""
    nodes: dict[str, dict] = {}
    links: list[dict] = []

    def node(nid: str, kind: str, label: str) -> None:
        nodes.setdefault(nid, {"id": nid, "kind": kind, "label": label})

    for system_id, system in RULES.items():
        node(system_id, "system", f"{system['coordinator']} ({system['workflow']})")
        for rule in system["rules"]:
            issue_id = f"{system_id}:issue:{rule['issue']}"
            node(issue_id, "issue", rule["issue"])
            links.append({"source": system_id, "target": issue_id,
                          "rule": "diagnoses (reference-point gap or hard flag)"})
            for module in rule["modules"]:
                module_id = f"{system_id}:module:{module}"
                node(module_id, "module", module)
                links.append({"source": issue_id, "target": module_id,
                              "rule": "affects"})
                action_id = f"{system_id}:action:{rule['issue']}:{module}"
                node(action_id, "action", f"{rule['action']}  [{rule['bounded_by']}]")
                links.append({"source": module_id, "target": action_id,
                              "rule": "bounded adjustment"})
    return {
        "generated_by": "experiments/export_bmc_rule_map.py",
        "source_files": [str(COORDINATOR.relative_to(PROJECT_ROOT)),
                         str(FL_WORKFLOW.relative_to(PROJECT_ROOT)),
                         str(APT_WORKFLOW.relative_to(PROJECT_ROOT))],
        "convergence_rules": CONVERGENCE_RULES,
        "nodes": list(nodes.values()),
        "links": links,
        "rules": RULES,
    }


def check_against_source() -> list[str]:
    """Verify the exported data against the live source; return a list of drifts."""
    problems: list[str] = []
    from agent_core.workflows.coordinator import AptamerCoordinator, ReferencePointCoordinator

    t1 = RULES["type1_full_length_mrna"]
    if list(ReferencePointCoordinator.OBJECTIVES) != list(t1["dimensions"].keys()):
        problems.append("Type-I OBJECTIVES drifted from the rule map dimensions")
    for dim, modules in ReferencePointCoordinator.DIMENSION_TO_MODULES.items():
        if t1["dimensions"].get(dim, ([], ""))[0] != list(modules):
            problems.append(f"Type-I dimension {dim} modules drifted: {modules}")

    t2 = RULES["type2_aptamer"]
    if list(AptamerCoordinator.OBJECTIVES) != list(t2["dimensions"].keys()):
        problems.append("Type-II OBJECTIVES drifted from the rule map dimensions")
    for dim, modules in AptamerCoordinator.DIMENSION_TO_MODULES.items():
        if t2["dimensions"].get(dim, ([], ""))[0] != list(modules):
            problems.append(f"Type-II dimension {dim} modules drifted: {modules}")

    coord_src = COORDINATOR.read_text()
    for issue in ("CDS_COMPONENT_BELOW_REFERENCE", "FULL_MFE_SCORE_BELOW_REFERENCE",
                  "JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE", "JUNCTION_5UTR_CDS_AUG_BURIED",
                  "JUNCTION_5UTR_CDS_KOZAK_BURIED", "JUNCTION_CDS_3UTR_SCORE_BELOW_REFERENCE",
                  "EGARPS_COMPONENT_BELOW_REFERENCE", "RHOFOLD_COMPONENT_BELOW_REFERENCE",
                  "IPTM_COMPONENT_BELOW_REFERENCE"):
        if issue not in coord_src:
            problems.append(f"issue constant {issue} not found in coordinator.py")
    for delta in ("delta=+2.0", "delta=-2.0", "delta=2.0", "delta = 10.0", "delta = 5.0"):
        if delta not in coord_src:
            problems.append(f"adjustment magnitude {delta!r} not found in coordinator.py")

    fl_src = FL_WORKFLOW.read_text()
    if not re.search(r"min\(20\.0,\s*new_lambda", fl_src) or "max(0.0, min(20.0" not in fl_src:
        problems.append("lambda [0, 20] clamp not found in full_length_mrna_design.py")
    apt_src = APT_WORKFLOW.read_text()
    if "max(3, min(current_window, 10))" not in apt_src:
        problems.append("hotspot window [3, 10] clamp not found in rna_aptamer_design.py")
    if "min(200, inp.aptamer_length" not in apt_src:
        problems.append("aptamer length 200 cap not found in rna_aptamer_design.py")
    if "min(20, inp.n_odesign_samples" not in apt_src:
        problems.append("n_odesign_samples 20 cap not found in rna_aptamer_design.py")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify rule data against live source")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    if args.check:
        problems = check_against_source()
        if problems:
            for p in problems:
                print(f"DRIFT: {p}")
            return 1
        print("check OK: rule map matches live coordinator/workflow source")
        return 0

    rule_map = build_rule_map()
    # Structural sanity: every link endpoint must be a declared node.
    node_ids = {n["id"] for n in rule_map["nodes"]}
    for link in rule_map["links"]:
        assert link["source"] in node_ids, f"dangling link source {link['source']}"
        assert link["target"] in node_ids, f"dangling link target {link['target']}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rule_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(rule_map['nodes'])} nodes, {len(rule_map['links'])} links, "
          f"{sum(len(s['rules']) for s in RULES.values())} rules -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
