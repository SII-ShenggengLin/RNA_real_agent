#!/usr/bin/env python3
"""Build the v5 public data package (2026-10-09, user-directed rebuild).

v5 is a reference-metadata refresh of v4.  The v4 upload window predates the
2026-10-09 repository corrections, so the v4 tree (and the tarball on Zenodo)
still carried the eleven tertiary-structure task JSONs' wrong reference names
(the figS1 RCSB corrections) and the Yang & Sarnow 1997 old journal citation
(J Virol 71:2840) in external_anchors/SOURCES.md and
external_anchors/ires/ires_positive.fa.  v5 copies the v4 tree and overwrites
exactly those thirteen files from the corrected live repository (verified by
a full subtree diff: every other carried file is byte-identical between the
v4 tree and the repository):

    - benchmarks/01_RNADesign-210/tasks/07_rna_tertiary_structure/
      {003,004,005,006,008,011,012,013,014,016,019}_*.json   (11 files)
    - benchmarks/external_anchors/SOURCES.md
    - benchmarks/external_anchors/ires/ires_positive.fa

plus the README bumped to v5.0 with the refresh note and MANIFEST.sha256
regenerated.  The legitimate "theophylline aptamer" strings of the
small-molecule anchor set (PDB 1O15) are unrelated to the retired wrong
names and stay verbatim.

Uploaded to Zenodo draft 22736194 the same day (v4 deleted by file id, v5
direct PUT, read-back md5 verified); see upload_status.md.
"""

import hashlib
import shutil
import tarfile
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "RNADesignAgent_paper_data_v4"
DST = HERE / "RNADesignAgent_paper_data_v5"
TARBALL = HERE / "RNADesignAgent_paper_data_v5.tar.gz"
REPO = HERE.parent / "rna_agent_system"

TASK_IDS = ["003_ribodiffusion_only", "004_rhodesign_high_temp",
            "005_rhodesign_low_temp", "006_dual_equal", "008_rhofold_heavy",
            "011_rhodesign_2d_assisted", "012_ribodiffusion_defaults",
            "013_ribodiffusion_large_ckpt", "014_rhodesign_default_temp",
            "016_max_samples", "019_full_group_i_intron"]

SYNC = [(REPO / f"data/benchmarks/RNA-BioBench-Platform/tasks/07_rna_tertiary_structure/07_rna_tertiary_structure_{t}.json",
         DST / f"benchmarks/01_RNADesign-210/tasks/07_rna_tertiary_structure/07_rna_tertiary_structure_{t}.json")
        for t in TASK_IDS]
SYNC += [
    (REPO / "data/benchmarks/external_anchors/SOURCES.md",
     DST / "benchmarks/external_anchors/SOURCES.md"),
    (REPO / "data/benchmarks/external_anchors/ires/ires_positive.fa",
     DST / "benchmarks/external_anchors/ires/ires_positive.fa"),
]


def build() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)

    for src, dst in SYNC:
        assert src.is_file(), f"repo source missing: {src}"
        assert dst.is_file(), f"package target missing: {dst}"
        shutil.copy2(src, dst)

    readme = (DST / "README.md").read_text()
    assert readme.startswith("# RNADesignAgent — Research Data Deposit (v4.0)\n"), \
        "v4 README header drifted; revisit the bump below"
    readme = readme.replace(
        "# RNADesignAgent — Research Data Deposit (v4.0)\n",
        "# RNADesignAgent — Research Data Deposit (v5.0)\n", 1)
    readme = readme.replace(
        "v4.0 reorganizes the deposit around the eight final-form benchmark datasets of "
        "the\npaper's Methods",
        "v4.0 reorganized the deposit around the eight final-form benchmark datasets of "
        "the\npaper's Methods", 1)
    readme += (
        "\n## v5.0 note\n\n"
        "v5.0 refreshes reference metadata from the corrected repository records: the\n"
        "tertiary-structure task source fields now carry the verified RCSB reference\n"
        "names, and the BiP IRES anchor citation reads Nucleic Acids Res 25:2800\n"
        "(Yang & Sarnow 1997). All dataset contents are otherwise identical to v4.0.\n")
    (DST / "README.md").write_text(readme)

    (DST / "MANIFEST.sha256").unlink()
    files = sorted(p for p in DST.rglob("*")
                   if p.is_file() and p.name != "MANIFEST.sha256")
    with open(DST / "MANIFEST.sha256", "w") as f:
        for p in files:
            f.write(hashlib.sha256(open(p, "rb").read()).hexdigest()
                    + "  " + str(p.relative_to(DST)) + "\n")

    if TARBALL.exists():
        TARBALL.unlink()
    with tarfile.open(TARBALL, "w:gz") as t:
        t.add(DST, arcname=DST.name)   # one recursive add — no duplicate members
    print(f"v5 built: {len(files) + 1} files under {DST}")
    print(f"tarball: {TARBALL} {TARBALL.stat().st_size} B")


if __name__ == "__main__":
    build()
