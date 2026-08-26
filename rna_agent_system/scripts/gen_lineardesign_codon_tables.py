#!/usr/bin/env python3
"""Generate LinearDesign-format codon-usage CSVs from the built-in Kazusa tables.

Single source of truth: ``agent_core/data/codon_usage_kazusa.json`` (the same
tables the platform's CAI evaluator uses). One CSV per species is written to
``agent_core/data/codon_usage_lineardesign/`` in the format the LinearDesign
binary expects (header ``#,``; rows ``<RNA codon>,<aa>,<fraction>`` with
8-decimal fractions, stop codons included, codons in string order).

The ``mrna_cds_design`` workflow resolves ``cai_species`` to these CSVs so the
generator and the CAI evaluator always design and score against the same
species table (2026-08-25 species-wiring fix; previously LinearDesign always
used its bundled human table regardless of ``cai_species``).

Usage (from ``rna_agent_system/``):

    python scripts/gen_lineardesign_codon_tables.py [--check]

``--check`` verifies the on-disk CSVs match the Kazusa source and exits
non-zero on drift (used by the test suite).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KAZUSA_JSON = PROJECT_ROOT / "agent_core" / "data" / "codon_usage_kazusa.json"
OUT_DIR = PROJECT_ROOT / "agent_core" / "data" / "codon_usage_lineardesign"


def csv_path_for_species(canonical_name: str) -> Path:
    return OUT_DIR / f"{canonical_name.replace(' ', '_')}.csv"


def render_species_table(codons: dict[str, dict]) -> str:
    lines = ["#,,"]
    for codon in sorted(codons):
        entry = codons[codon]
        lines.append(f"{codon},{entry['aa']},{float(entry['fraction']):.8f}")
    return "\n".join(lines) + "\n"


def generate() -> int:
    kazusa = json.loads(KAZUSA_JSON.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for species, codons in sorted(kazusa.items()):
        out = csv_path_for_species(species)
        out.write_text(render_species_table(codons), encoding="utf-8")
        print(f"wrote {out} ({len(codons)} codons)")
    return 0


def check() -> int:
    kazusa = json.loads(KAZUSA_JSON.read_text(encoding="utf-8"))
    drift = []
    for species, codons in sorted(kazusa.items()):
        out = csv_path_for_species(species)
        if not out.exists():
            drift.append(f"missing: {out.name}")
            continue
        if out.read_text(encoding="utf-8") != render_species_table(codons):
            drift.append(f"stale: {out.name}")
    for path in sorted(OUT_DIR.glob("*.csv")):
        if csv_path_for_species(path.name.removesuffix(".csv").replace("_", " ")) != path:
            drift.append(f"orphan: {path.name}")
    if drift:
        print("codon-table CSV drift detected:")
        for d in drift:
            print(f"  {d}")
        print("re-run scripts/gen_lineardesign_codon_tables.py")
        return 1
    print(f"all {len(kazusa)} LinearDesign codon tables match the Kazusa source")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="verify on-disk CSVs match the Kazusa source")
    args = parser.parse_args()
    return check() if args.check else generate()


if __name__ == "__main__":
    sys.exit(main())
