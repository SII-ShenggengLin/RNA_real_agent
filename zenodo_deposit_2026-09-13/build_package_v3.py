#!/usr/bin/env python3
"""Build the v3 public data package for the Zenodo draft deposit.

v3 (2026-09-14, user direction "打一个 v3 包加入这些目录"): the v2 scope
PLUS the external-baseline campaign evidence behind the paper's new
section 2.6 / Fig. 6 — the frozen records of the bare-LLM baseline
(exp42), the same-tool ReAct baseline (exp43) and the three-arm
comparison (exp42_43_comparison). All other frozen per-campaign evidence
stays out of the public deposit exactly as registered for v2; the
baseline campaigns are added because the new Results section presents
them directly and reviewers need the underlying records.

  KEEP   everything in v2 (benchmarks + external anchors + 200-controls
         FASTA + deployment cohorts + claim-audit task sets + self_model +
         MODEL_API_USAGE.md + README + MANIFEST.sha256)
  ADD    baseline_evidence/ — the three frozen record directories
         (minus their regenerable adjudication scratch/ fastas, excluded
         under the v2 operational-debris convention and disclosed here)
         + a README mapping every file to the paper's panels and numbers.

Usage: python3 build_package_v3.py
"""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / "rna_agent_system"
V2 = ROOT / "RNADesignAgent_paper_data_v2"
V3 = ROOT / "RNADesignAgent_paper_data_v3"

CAMPAIGNS = [
    "exp42_bare_llm_baseline",
    "exp43_react_baseline",
    "exp42_43_comparison",
]

README_V3_ADDENDUM = """
## v3.0 (2026-09-14): baseline-campaign evidence added

This v3.0 deposit adds `baseline_evidence/` — the frozen records of the
external-baseline comparison presented in the paper's section 6 of the
Results (Fig. 6):

- `exp42_bare_llm_baseline/` — the bare-LLM condition: `runs.jsonl` (one
  record per turn x prompting regime, the verbatim model responses),
  `adjudicated.jsonl` (the deterministic validity checks + claim verdicts
  per turn), `summary.json` (the per-workflow delivery and claim rates).
- `exp43_react_baseline/` — the same-tool ReAct condition at three
  model-call budget tiers: `runs.jsonl` (per-turn tool logs, budgets,
  submitted answers), `adjudicated.jsonl`, `summary.json`.
- `exp42_43_comparison/` — the three-arm comparison over the frozen
  platform records: `comparison.json` (per-workflow x condition delivery,
  failure-mode decomposition, paired exact-McNemar tests, claim blocks,
  cost ledger) and `table.md` (the rendered tables).

Each campaign directory is byte-identical to the project repository's
frozen record except that the regenerable adjudication scratch FASTAs
(`scratch/`) are excluded. Every number in the paper's baseline section
recomputes from these files; the comparison summary recomputation is
verified byte-identical by its driver (`--verify`).
"""

def campaign_readme() -> str:
    return """# Baseline-campaign evidence (paper Results "language-model baselines", Fig. 6)

Three frozen record directories backing the three-condition comparison on
the 31-session process-aware suite (96 user turns, all eleven workflows):

| Directory | Condition | Key files |
|---|---|---|
| `exp42_bare_llm_baseline/` | Bare model, zero- and few-shot, no tools (one call per turn per regime) | `runs.jsonl` (192 turn records, verbatim model responses), `adjudicated.jsonl` (validity checks + claim verdicts), `summary.json` |
| `exp43_react_baseline/` | Same-tool ReAct loop, three budget tiers (matched / 3x / 10x) | `runs.jsonl` (288 turn records: budgets, tool logs, submitted answers), `adjudicated.jsonl`, `summary.json` |
| `exp42_43_comparison/` | Three-arm comparison vs the frozen platform records | `comparison.json` (delivery by workflow x condition, failure-mode decomposition, paired exact-McNemar tests, claim adjudication, cost ledger), `table.md` |

Notes:

- The platform condition is NOT re-run: it reuses the frozen production
  records (per-session success, model-call counts and evaluated-candidate
  counts extracted from them; the symmetric validity rules re-applied to
  the frozen candidate pools).
- The `scratch/` subdirectories of the two campaign records (intermediate
  FASTAs written during deterministic adjudication) are regenerable
  operational debris and are excluded; every published number recomputes
  from the JSONL records without them.
- Budget tiers: "matched" = the platform's own measured per-session
  model-call count (zero on the eight deterministic-workflow sessions -
  recorded as the measured floor); "3x"/"10x" = three and ten times
  max(platform count, two calls per turn).
"""


def build_v2_if_missing() -> None:
    if not V2.is_dir():
        raise SystemExit(
            "v2 staging tree missing — run build_package_v2.py first "
            "(the v3 package builds on the v2 tree)"
        )


def main() -> None:
    build_v2_if_missing()
    if V3.exists():
        shutil.rmtree(V3)
    shutil.copytree(V2, V3)

    # 1. baseline_evidence/
    be = V3 / "baseline_evidence"
    be.mkdir()
    for camp in CAMPAIGNS:
        src = REPO / "experiments" / "results" / camp
        assert src.is_dir(), src
        shutil.copytree(src, be / camp, ignore=shutil.ignore_patterns("scratch", "__pycache__"))
    (be / "README.md").write_text(campaign_readme())

    # 2. package README: bump to v3 and append the addendum
    readme = (V3 / "README.md").read_text()
    readme = readme.replace(
        "# RNADesignAgent — Research Data Deposit (v2.0)",
        "# RNADesignAgent — Research Data Deposit (v3.0)",
    )
    readme = readme.replace(
        "`MANIFEST.sha256` lists the SHA-256 checksum of every file.",
        "`MANIFEST.sha256` lists the SHA-256 checksum of every file.",
    )
    # contents table gains the baseline_evidence row
    marker = "| `MODEL_API_USAGE.md` |"
    i = readme.find(marker)
    assert i > 0
    j = readme.find("\n", i)
    row = (
        "\n| `baseline_evidence/` | The frozen records of the external-baseline "
        "comparison (Results, Fig. 6): the bare-model and same-tool-ReAct campaign "
        "records and the three-arm comparison output — per-turn runs, deterministic "
        "adjudications, summaries, and the comparison tables (the platform condition "
        "reuses its frozen production records; see `baseline_evidence/README.md`). |"
    )
    readme = readme[:j] + row + readme[j:]
    readme += README_V3_ADDENDUM
    (V3 / "README.md").write_text(readme)

    # 3. MANIFEST
    manifest = []
    for p in sorted(V3.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.sha256":
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            manifest.append(f"{digest}  {p.relative_to(V3)}")
    (V3 / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n")

    # 4. tarball
    tar = ROOT / "RNADesignAgent_paper_data_v3.tar.gz"
    if tar.exists():
        tar.unlink()
    with tarfile.open(tar, "w:gz") as tf:
        tf.add(V3, arcname=V3.name)
    n_new = sum(
        1 for c in CAMPAIGNS for p in (be / c).rglob("*") if p.is_file()
    )
    print("files:", len(manifest), f"(baseline_evidence files: {n_new})")
    print("tar bytes:", tar.stat().st_size)
    print("tar sha256:", hashlib.sha256(tar.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
