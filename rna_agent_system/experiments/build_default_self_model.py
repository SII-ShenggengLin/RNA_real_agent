"""Build the packaged default SelfModel from the frozen profiling campaigns.

Reads the frozen verdict files under ``experiments/results/`` and emits
``agent_core/calibrated/default_self_model.json`` — the evidence base the
platform CalibratedRuntime ships with, so production gating reflects the
published profiling results from the first run.

Sources (all pre-registered, frozen):
- E1  ``e1_capability_summary_v2.json``  aptamer structure oracles (screening/ranking
      per oracle x target; docking cells where per-case data exists)
- E7  ``e7_selfmodel/self_model.json``    GEMORNA 5'UTR MRL (verified on 3 families)
- RNAsmol ``rnasmol_boundary_panel.json`` in-distribution verified / short-aptamer
      OOD failed
- E16/E17/E18 ``e16_e17_e18/verdict.json`` + ``e16_e17_e18/self_model.json``
      IRESfinder (3 families, all screening failed), GerNA-Bind (screening
      failed at chance level), RNASTOP (screening verified, ranking failed)

Run:  PYTHONPATH=. python experiments/build_default_self_model.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "results"
OUT_PATH = ROOT / "agent_core" / "calibrated" / "default_self_model.json"

E1_EVIDENCE = "experiments/results/e1_capability_summary_v2.json"
E7_EVIDENCE = "experiments/results/e7_selfmodel/self_model.json"
RNASMOL_EVIDENCE = "experiments/results/rnasmol_boundary_panel.json"
E16_18_EVIDENCE = "experiments/results/e16_e17_e18/verdict.json"


def _assessment(grade: str, metrics: dict, note: str) -> dict:
    def _num(v):
        return round(float(v), 6) if isinstance(v, (int, float)) else v

    return {
        "grade": grade,
        "confidence": 1.0 if grade == "verified" else 0.9,
        "metrics": {k: _num(v) for k, v in metrics.items()},
        "evidence": [{"kind": "summary_json", "path": note, "note": ""}],
        "profiled_at": "",
        "source_case_id": None,
        "transferred_from_grade": None,
    }


def build() -> dict:
    records: list[dict] = []

    # --- E7 records are already in SelfModel schema; copy verbatim.
    e7 = json.loads((RESULTS / "e7_selfmodel" / "self_model.json").read_text())
    records.extend(e7.get("records", []))

    # --- E1: aptamer structure oracles (18 oracle x target cells).
    e1 = json.loads((RESULTS / "e1_capability_summary_v2.json").read_text())
    docking_by_target: dict[str, list[dict]] = {}
    for case in e1.get("part_b_docking", {}).values():
        docking_by_target.setdefault(case["target"], []).append(case)

    for key, cell in e1["part_a_per_oracle_target"].items():
        oracle, target = key.split(" | ")
        caps: dict[str, dict] = {
            "screening": _assessment(
                "verified" if cell["screening_pass"] else "failed",
                {
                    "auroc": cell["screening_auroc"],
                    "auroc_ci_lo": cell["screening_auroc_ci95"][0],
                    "auroc_ci_hi": cell["screening_auroc_ci95"][1],
                    "n_binder": cell["n_binder"],
                    "n_negative": cell["n_negative"],
                },
                E1_EVIDENCE,
            ),
            "ranking": _assessment(
                "verified" if cell["ranking_pass"] else "failed",
                {"spearman_rho": cell["ranking_spearman_rho"], "n": cell["n_ranking_eligible"]},
                E1_EVIDENCE,
            ),
        }
        # Docking cells only where per-(oracle, target) pose data exists
        # (EGARPS native probability scored the E1 pose sets).
        if oracle == "egarps_native_probability" and target in docking_by_target:
            cases = docking_by_target[target]
            caps["docking"] = _assessment(
                "verified" if all(c["top1"] for c in cases) else "failed",
                {
                    "n_cases": len(cases),
                    "native_top1_count": sum(1 for c in cases if c["top1"]),
                    "worst_native_rank_fraction": max(
                        c["native_rank"] / c["n_poses_scored"] for c in cases
                    ),
                },
                E1_EVIDENCE,
            )
        records.append(
            {
                "oracle": oracle,
                "task_type": "rna_aptamer_design",
                "target_family": target,
                "capabilities": caps,
            }
        )

    # --- RNAsmol two-sided boundary.
    panel = json.loads((RESULTS / "rnasmol_boundary_panel.json").read_text())
    for family, cell in (
        ("robin_molperturbation_test", panel["robin_test"]),
        ("pdb_molperturbation_test", panel["pdb_test"]),
    ):
        records.append(
            {
                "oracle": "rnasmol",
                "task_type": "rna_small_molecule",
                "target_family": family,
                "capabilities": {
                    "screening": _assessment(
                        "verified" if cell["auroc_gate_0.8_pass"] else "failed",
                        {
                            "auroc": cell["auroc"],
                            "auroc_ci_lo": cell["auroc_ci95"][0],
                            "auroc_ci_hi": cell["auroc_ci95"][1],
                            "n": cell["n"],
                        },
                        RNASMOL_EVIDENCE,
                    )
                },
            }
        )
    ood = panel["ood_aptamer"]
    records.append(
        {
            "oracle": "rnasmol",
            "task_type": "rna_small_molecule",
            "target_family": "short_aptamer_ood",
            "capabilities": {
                "screening": _assessment(
                    "failed",
                    {
                        "auroc_vs_random_chem": ood["auroc_vs_random_chem"],
                        "auroc_ci_lo": ood["auroc_vs_random_chem_ci95"][0],
                        "auroc_ci_hi": ood["auroc_vs_random_chem_ci95"][1],
                        "chance_consistent": float(ood["chance_consistent"]),
                    },
                    RNASMOL_EVIDENCE,
                )
            },
        }
    )

    # --- E16/E17/E18: the pending-oracle campaigns (2026-08-18).  The
    # campaign SelfModel is already in schema; copy verbatim (evidence
    # pointers reference the per-campaign scoring caches + verdict).
    e16_18 = json.loads((RESULTS / "e16_e17_e18" / "self_model.json").read_text())
    records.extend(e16_18.get("records", []))

    return {"schema_version": "calibrated_v1", "records": records}


def main() -> None:
    payload = build()
    OUT_PATH.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    n = len(payload["records"])
    verified = sum(
        1
        for r in payload["records"]
        for c in r["capabilities"].values()
        if c["grade"] == "verified"
    )
    failed = sum(
        1
        for r in payload["records"]
        for c in r["capabilities"].values()
        if c["grade"] == "failed"
    )
    print(f"wrote {OUT_PATH} records={n} cells_verified={verified} cells_failed={failed}")


if __name__ == "__main__":
    main()
