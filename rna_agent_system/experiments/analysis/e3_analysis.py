"""E3 pilot analysis: FP rate, TP retention, decision-layer overreach.

Reads the adjudicated claims JSONL plus the raw runs JSONL (overreach events)
and writes the pre-registered summary (driver docstring): per-arm FP rate,
relative reduction, TP retention, overreach counts, go/no-go bits.

Usage:
    PYTHONPATH=. python experiments/analysis/e3_analysis.py \
        --runs experiments/results/e3_runs_pilot.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

FP_REDUCTION_GO = 0.50
TP_RETENTION_GO = 0.90


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--adjudicated", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    adj_path = args.adjudicated or args.runs.with_name(args.runs.stem + "_adjudicated.jsonl")
    out_path = args.output or args.runs.with_name(args.runs.stem + "_summary.json")

    claims = [
        json.loads(line)
        for line in adj_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    runs = [
        json.loads(line)
        for line in args.runs.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    per_arm: dict[str, dict] = {}
    for arm in ("ungated", "gated"):
        arm_claims = [c for c in claims if c["arm"] == arm]
        tp = sum(1 for c in arm_claims if c["verdict"] == "TP")
        fp = sum(1 for c in arm_claims if c["verdict"] == "FP")
        suppressed = sum(1 for c in arm_claims if c["verdict"] == "suppressed")
        borderline = sum(1 for c in arm_claims if c["verdict"] == "borderline")
        fp_rate = fp / (fp + tp) if (fp + tp) else None
        overreach = sum(
            len(r["result"].get("overreach_events") or [])
            for r in runs if r["arm"] == arm
        )
        per_arm[arm] = {
            "n_claims": len(arm_claims),
            "TP": tp,
            "FP": fp,
            "suppressed": suppressed,
            "borderline": borderline,
            "fp_rate": fp_rate,
            "overreach_events": overreach,
            "per_category": {
                cat: {
                    "TP": sum(1 for c in arm_claims if c["category"] == cat and c["verdict"] == "TP"),
                    "FP": sum(1 for c in arm_claims if c["category"] == cat and c["verdict"] == "FP"),
                }
                for cat in ("trusted_deterministic", "untrusted_oracle")
            },
        }

    cu, cg = per_arm["ungated"], per_arm["gated"]
    rel_reduction = (
        1 - cg["fp_rate"] / cu["fp_rate"]
        if cu["fp_rate"] and cg["fp_rate"] is not None else None
    )
    tp_retention = cg["TP"] / cu["TP"] if cu["TP"] else None
    # Pilot discriminability bit (pre-registered go/no-go for scaling up).
    control_fp_untrusted = cu["per_category"]["untrusted_oracle"]["FP"]
    summary = {
        "preregistration": "experiments/run_e3_gated_vs_ungated.py docstring; REDESIGN §3 E3",
        "runs": (str(args.runs.relative_to(PROJECT_ROOT))
                 if args.runs.is_relative_to(PROJECT_ROOT) else str(args.runs)),
        "thresholds": {"fp_relative_reduction_go": FP_REDUCTION_GO,
                       "tp_retention_go": TP_RETENTION_GO},
        "per_arm": per_arm,
        "fp_rate_relative_reduction": rel_reduction,
        "tp_retention": tp_retention,
        "pilot_discriminability": {
            "control_fp_on_untrusted_oracle": control_fp_untrusted,
            "task_set_discriminates": control_fp_untrusted > 0,
        },
        "go_bits": {
            "fp_reduction_met": rel_reduction is not None and rel_reduction >= FP_REDUCTION_GO,
            "tp_retention_met": tp_retention is not None and tp_retention >= TP_RETENTION_GO,
            "overreach_gated_zero": cg["overreach_events"] == 0,
        },
    }
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"summary -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
