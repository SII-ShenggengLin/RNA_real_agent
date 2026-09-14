#!/usr/bin/env python3
"""Build the v2 public data package for the Zenodo draft deposit (batch 10).

Re-curation per the user's 2026-09-14 direction:
  KEEP   benchmarks/ (five suites + external_anchors), pa_benchmarks.json,
         self_model/, MODEL_API_USAGE.md, README, MANIFEST.sha256
  ADD    external_anchors/wt_cds/random_synonymous_controls.fa (200 seeded
         synonymous resamples, the registered exp2 generator verbatim),
         deployment_cohorts/ (the five mRNA deployment targets + a pointer
         register for the six aptamer deployment targets),
         claim_audit_tasks/ (the 45-task aptamer and 20-task mRNA audit sets)
  DROP   campaigns/ (frozen per-campaign evidence) and supplementary/ —
         withdrawn from the public deposit by user direction; the frozen
         records remain in the project repository.

Usage: python3 build_package_v2.py
"""

import random
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / "rna_agent_system"
V1 = ROOT / "RNADesignAgent_paper_data_v1"
V2 = ROOT / "RNADesignAgent_paper_data_v2"

# ── the registered exp2 generator, verbatim ─────────────────────────────────
_BASES = "AUGC"
_AAS = "".join([
    "KNKN", "IIMI", "RSRS", "TTTT", "*Y*Y", "LFLF", "*CWC", "SSSS",
    "EDED", "VVVV", "GGGG", "AAAA", "QHQH", "LLLL", "RRRR", "PPPP",
])
CODON_TABLE = {
    b1 + b2 + b3: _AAS[i]
    for i, (b1, b2, b3) in enumerate(
        (x, y, z) for x in _BASES for y in _BASES for z in _BASES
    )
}
SYNONYMOUS_CODONS: dict[str, list[str]] = {}
for _codon, _aa in CODON_TABLE.items():
    if _aa == "*":
        continue
    SYNONYMOUS_CODONS.setdefault(_aa, []).append(_codon)
STOPS = {"UAA", "UAG", "UGA"}


def random_synonymous(wt_cds: str, target_id: str, draw: int) -> str:
    rng = random.Random(f"exp2:{target_id}:{draw}")
    out = []
    for i in range(0, len(wt_cds), 3):
        codon = wt_cds[i:i + 3]
        out.append(rng.choice(SYNONYMOUS_CODONS[CODON_TABLE[codon]]))
    return "".join(out)


def read_fasta(path: Path) -> str:
    return "".join(
        line.strip() for line in path.read_text().splitlines()
        if not line.startswith(">")
    ).upper().replace("T", "U")


def build_controls() -> Path:
    """Export the 200 random synonymous controls (10 draws x 20 WT targets)."""
    wt_dir = REPO / "data" / "benchmarks" / "external_anchors" / "wt_cds"
    suite_targets = sorted(
        p.stem for p in
        (REPO / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets").glob("*.json")
    )
    assert len(suite_targets) == 20, suite_targets
    out = V2 / "benchmarks" / "external_anchors" / "wt_cds" / "random_synonymous_controls.fa"
    lines = []
    n = 0
    for tid in suite_targets:
        seq = read_fasta(wt_dir / f"{tid}.fa")
        codons = [seq[i:i + 3] for i in range(0, len(seq), 3)]
        if codons and codons[-1] in STOPS:
            seq = "".join(codons[:-1])
        for draw in range(10):  # draws 0–9, the registered exp2 numbering
            resample = random_synonymous(seq, tid, draw)
            assert len(resample) == len(seq)
            lines.append(f">exp2:{tid}:{draw} {tid} random synonymous resample {draw + 1}/10")
            for i in range(0, len(resample), 60):
                lines.append(resample[i:i + 60])
            n += 1
    assert n == 200, n
    out.write_text("\n".join(lines) + "\n")
    return out


README = """# RNADesignAgent — Research Data Deposit (v2.0)

Data supporting the manuscript *"A multi-agent system for RNA design with capability-gated
prediction and constraint-navigated generation"* (system name **RNADesignAgent**; benchmark
name **RNADesign-210**).

v2.0 (2026-09-14) re-scopes the deposit to the benchmark and anchor assets, the packaged
capability self-model and the model-usage register. The v1.0 frozen per-campaign evidence
and the supplementary-information copies were withdrawn from the public deposit (they
remain in the project repository); the wild-type-CDS random synonymous controls, the
deployment-cohort target registers and the two claim-audit task sets were added.
`MANIFEST.sha256` lists the SHA-256 checksum of every file.

## Contents

| Path | Contents |
|------|----------|
| `benchmarks/` | The five registered benchmark suites — `RNA-BioBench-Platform` (the 210-task RNADesign-210 suite spanning all eleven workflows), `RNA-BioBench-ProcessAware` (31 multi-turn form-entry regression sessions), `RNA-BioBench-FullLength-mRNA` (20-target full-length mRNA suite), `RNA-BioBench-Aptamer` (20-target aptamer suite) and `RNA-BioBench-Aptamer-Expanded` (19 additional targets; combined with the 20-target suite these form the 39-target budget-sweep pool) — plus `external_anchors/` (the assertion-curated anchor sets used for capability profiling and biological-validity controls: aptamer binder/negative panels with measured Kd values, the measured-MRL 5′UTR anchor families, the IRES literature panel, small-molecule binder/non-binder pairs, the vaccine-mRNA assemblies, the mRNA-stability panel, and the wild-type CDS collection with its 200 seeded random synonymous controls in `wt_cds/random_synonymous_controls.fa`). |
| `benchmarks/deployment_cohorts/` | The five-protein mRNA deployment cohort register (PTH, leptin, G-CSF, thrombopoietin, PLAT; UniProt accessions and sequences, selection rule and rationale) and the pointer register for the six-protein aptamer deployment cohort (six expanded-pool target entries). These cohorts pool with the registered suites into the paper's 25-/26-target analyses. |
| `benchmarks/claim_audit_tasks/` | The two derived claim-audit task sets: the 45-task aptamer set (24 trusted-deterministic + 21 untrusted-predictor tasks over the nine-target anchor set) and the 20-task full-length mRNA set (10 + 10). |
| `pa_benchmarks.json` | Configuration of the 31 process-aware benchmark sessions (task inputs as entered through the user form). |
| `self_model/` | The packaged default capability SelfModel (`default_self_model.json`) that ships with the platform and its generator (`build_default_self_model.py`), built from the frozen profiling verdict files — production gating enforces exactly these grades. |
| `MODEL_API_USAGE.md` | The authoritative per-experiment LLM-usage register (written in Chinese; the LLM-usage numbers appear in English in the paper). |

## Notes on provenance and integrity

- **Random synonymous controls are deterministic.** The 200 controls are uniform
  synonymous resamples of the wild-type CDSs under the standard genetic code, one per
  `>exp2:<target>:<draw>` header, generated by the registered seeded procedure (seed
  string `exp2:<target>:<draw>`, draw = 1…10) — identical to the null condition of the
  paper's codon-usage analysis.
- **Third-party reference databases are not redistributed.** External references used for
  scoring (for example the human GENCODE v46 transcriptome for siRNA off-target scanning
  and the codon-usage tables derived from Kazusa) are not part of this deposit; the
  manuscript names them and their accessions. The anchor sets under
  `benchmarks/external_anchors/` are our curation (sequence, role label, measured value
  and per-entry source citation) of published measurements — chiefly the massively
  parallel translation assay of Sample et al. (GEO accession GSE114002), literature
  aptamer–target binding affinities and RNA–protein complexes from the RCSB Protein Data
  Bank — assembled under the assertion-checked curation protocol described in the
  manuscript (Methods).
- **Local model weights and external codes are not included.** All structure/sequence
  predictors ran as local microservices with local weights; their vendored upstream codes
  and weights are covered by the manuscript's code-availability statement, not this deposit.

## Licence

Creative Commons Attribution 4.0 International (CC-BY-4.0), to the extent the deposit's
contents are protectable; curated anchor entries remain subject to their original sources'
terms, which are cited per entry.
"""

COHORTS_README = """# Deployment cohorts

The paper's pooled constraint-navigation analyses (25 mRNA targets, 26 aptamer targets)
combine each registered 20-target suite with a deployment cohort that entered through the
production user-form entry:

- `mrna_targets.json` — the five mRNA deployment targets (PTH, leptin, G-CSF,
  thrombopoietin, PLAT), registered before any run: single UniProt isoform per target,
  accession and length asserted, sequences included, with the selection rule and
  per-target rationale.
- `aptamer_targets.json` — the six aptamer deployment targets (FGF2, Angiopoietin-2,
  IFN-gamma, IL-17A, PDGF-BB, Influenza H3N2 HA). Each is an expanded-pool target entry;
  the definitive records (sequence, provenance, structure path) live in
`../RNA-BioBench-Aptamer-Expanded/targets/` — this register lists the target ids and
  points there.

The cohorts' comparison conditions were completed under the identical budget-matched
protocols and the pooled statistics are reported with cohort splits disclosed (Methods,
Statistics).
"""

AUDIT_README = """# Claim-audit task sets

The two derived task sets behind the paper's claim-gating experiments:

- `e5_audit_tasks.json` — the 45-task aptamer claim-overreach audit set: 24
  trusted-deterministic tasks with exactly recomputable ground truth and 21
  untrusted-predictor ranking/screening tasks spanning the nine-target anchor set. Built
  from an earlier registered 20-task set carried byte-verbatim plus pre-registered,
  assertion-checked extension rules (the legacy reference is retained alongside as
  `e5_legacy_audit_tasks_reference.json`).
- `e18_audit_tasks_mrna.json` — the 20-task full-length mRNA audit set: ten
  trusted-deterministic and ten untrusted-predictor tasks built from the 20-target
  full-length suite's real design assets (production CDS deliveries, top-ranked
  full-length constructs, live predictor scores).

Both are consumed by the ungated-control and gated-treatment conditions of the paper's
gating experiments (Supplementary Methods).
"""


def main() -> None:
    if V2.exists():
        shutil.rmtree(V2)
    (V2 / "benchmarks").mkdir(parents=True)

    # 1. benchmark suites + external anchors (repo = source of truth)
    src = REPO / "data" / "benchmarks"
    for item in src.iterdir():
        if item.name == "README.md":
            continue
        dst = V2 / "benchmarks" / item.name
        shutil.copytree(item, dst) if item.is_dir() else shutil.copy2(item, dst)

    # 2. new: random synonymous controls
    controls = build_controls()
    print("controls:", controls, sum(1 for l in controls.read_text().splitlines() if l.startswith(">")))

    # 3. new: deployment cohorts
    coh = V2 / "benchmarks" / "deployment_cohorts"
    coh.mkdir()
    shutil.copy2(
        REPO / "experiments" / "results" / "exp30_production_navigation_live" / "curated_mrna_targets.json",
        coh / "mrna_targets.json",
    )
    import json
    apt_ids = ["FGF2", "Angiopoietin_2", "IFN_gamma", "IL_17A", "PDGF_BB", "Influenza_H3N2_HA"]
    apt = {
        "purpose": "Aptamer-side deployment cohort register (form-entry navigation campaigns)",
        "note": ("Each deployment target is an expanded-pool entry; the definitive records "
                 "live in ../RNA-BioBench-Aptamer-Expanded/targets/. This register lists ids "
                 "and display names only."),
        "targets": [
            {"target_id": t,
             "display": t.replace("_", " ").replace("IFN gamma", "IFN-γ").replace("H3N2 HA", "H3N2 HA")}
            for t in apt_ids
        ],
    }
    (coh / "aptamer_targets.json").write_text(json.dumps(apt, indent=1) + "\n")
    (coh / "README.md").write_text(COHORTS_README)

    # 4. new: claim-audit task sets
    cat = V2 / "benchmarks" / "claim_audit_tasks"
    cat.mkdir()
    shutil.copy2(REPO / "experiments" / "e5_audit_tasks.json", cat / "e5_audit_tasks.json")
    shutil.copy2(REPO / "experiments" / "e5_legacy_audit_tasks_reference.json", cat / "e5_legacy_audit_tasks_reference.json")
    shutil.copy2(REPO / "experiments" / "e18_audit_tasks_mrna.json", cat / "e18_audit_tasks_mrna.json")
    (cat / "README.md").write_text(AUDIT_README)

    # 5. kept: pa_benchmarks.json, self_model, model-usage register
    shutil.copy2(REPO / "pa_benchmarks.json", V2 / "pa_benchmarks.json")
    shutil.copytree(V1 / "self_model", V2 / "self_model")
    shutil.copy2(V1 / "campaigns" / "MODEL_API_USAGE.md", V2 / "MODEL_API_USAGE.md")

    # 6. README + MANIFEST
    (V2 / "README.md").write_text(README)
    import hashlib
    manifest = []
    for p in sorted(V2.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.sha256":
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            manifest.append(f"{digest}  {p.relative_to(V2)}")
    (V2 / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n")

    # 7. tarball
    tar = ROOT / "RNADesignAgent_paper_data_v2.tar.gz"
    if tar.exists():
        tar.unlink()
    with tarfile.open(tar, "w:gz") as tf:
        tf.add(V2, arcname=V2.name)
    print("files:", len(manifest), "| tar bytes:", tar.stat().st_size)
    print("tar sha256:", hashlib.sha256(tar.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
