#!/usr/bin/env python3
"""Pilot P2 (2026-08-03): curate the known-aptamer affinity calibration set.

MOTIVATION
----------
Case-B/fig4kav showed the EGARPS scoring chain ranks the *known* anti-VEGF
aptamer pegaptanib at ~5e-7 native_probability while freshly designed
candidates score 0.70 — i.e. the objective used to claim "BMC improves
binding" is unvalidated against known biology. Before any optimization claim
on the aptamer track can be interpreted, the scoring chain must be calibrated:
within a target, does native_probability rank higher-affinity aptamers
higher (Spearman rho), and does it separate binders from non-binders (AUROC)?

This script writes:
  - data/benchmarks/external_anchors/aptamers/calibration_set.json
  - data/benchmarks/external_anchors/aptamers/proteins/<target>.fa
  - appends entries to data/benchmarks/external_anchors/SOURCES.md

CURATION RULES (per the pilot-first protocol, MANUSCRIPT §13.1)
---------------------------------------------------------------
- Only entries with an exact sequence + a primary-literature Kd are admitted
  as quantitative points (role="binder"). Entries with verified sequence but
  no published Kd are role="binder_no_kd" (AUROC only).
- Synthetic negatives (scrambled/random, fixed seed) are role="negative" with
  an assigned Kd lower bound; used for AUROC and sensitivity analyses only.
- DNA aptamers are stored as DNA (T) and converted T->U at scoring time —
  the same convention the benchmark already uses for TBA (known_aptamers.json).
- Structural sanity: HD22 and Toggle-25t sequences were cross-checked against
  RCSB entry sequences (4I7Y chain D, 3DD2 chain B) on 2026-08-03.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/curate_aptamer_calibration.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANCHOR_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers"
PROTEIN_DIR = ANCHOR_DIR / "proteins"

# ── UniProt sequences fetched 2026-08-03 (embedded for reproducibility) ─────
UNIPROT_PDGFB_P01127 = (
    "MNRCWALFLSLCCYLRLVSAEGDPIPEELYEMLSDHSIRSFDDLQRLLHGDPGEEDGAEL"
    "DLNMTRSHSGGELESLARGRRSLGSLTIAEPAMIAECKTRTEVFEISRRLIDRTNANFLV"
    "WPPCVEVQRCSGCCNNRNVQCRPTQVQLRPVQVRKIEIVRKKPIFKKATVTLEDHLACKC"
    "ETVAAARPVTRSPGGSQEQRAKTPQTRVTIRTVRVRRPPKGKHRKFKHTHDKTALKETLG"
    "A"
)
# Mature PDGF-B chain = UniProt P01127 residues 82-190 (1-based, inclusive).
PDGFB_MATURE = UNIPROT_PDGFB_P01127[81:190]

UNIPROT_IGHE_P01854 = (
    "ASTQSPSVFPLTRCCKNIPSNATSVTLGCLATGYFPEPVMVTWDTGSLNGTTMTLPATTL"
    "TLSGHYATISLLTVSGAWAKQMFTCRVAHTPSSTDWVDNKTFSVCSRDFTPPTVKILQSS"
    "CDGGGHFPPTIQLLCLVSGYTPGTINITWLEDGQVMDVDLSTASTTQEGELASTQSELTL"
    "SQKHWLSDRTYTCQVTYQGHTFEDSTKKCADSNPRGVSAYLSRPSPFDLFIRKSPTITCL"
    "WPENGTLLQDSRAACTLPGHPGLVTFQIPKSFCLLLVSDSGVPCYIAIGTSEDGMDVALT"
    "LSQKTKVWLAGRLVTLRARGFGDDKSKCRVGFGLVIGNEAACLTQCAPGTERAHRLQFPR"
    "LGSQERPRSLSQAPRECPPNPPSQPPVQCRHACGPLSQPQGSKAVLGCLVFLATPWIG"
)
# NOTE: P01854 is the IgE heavy-chain constant region (C-epsilon1-4); D17.4
# binding maps to the C-epsilon3 domain. Full constant region used for the
# pilot (ProteinX predicts the complex from sequence).

# ── Fixed-seed synthetic negatives ──────────────────────────────────────────
def _scramble(seq: str, seed: int) -> str:
    rng = random.Random(seed)
    chars = list(seq)
    rng.shuffle(chars)
    return "".join(chars)


def _random_dna(n: int, seed: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("ACGT") for _ in range(n))


TBA_DNA = "GGTTGGTGTGGTTGG"

ENTRIES = [
    # ── Thrombin series (within-target Spearman set) ──
    {
        "id": "hd22_thrombin",
        "name": "HD22 (HTDQ), exosite II DNA aptamer",
        "target": "Thrombin",
        "protein": {"type": "benchmark_pdb", "pdb_id": "1HAO", "chain": "H"},
        "sequence": "AGTCCGTGGTAGGGCAGGTTGGGGTGACT",
        "alphabet": "dna",
        "length_nt": 29,
        "kd_nm": 0.5,
        "kd_method": "nitrocellulose filter binding (Tasset 1997); SPR re-measurement 0.3 nM (Kretz 2015)",
        "role": "binder",
        "reference": "Tasset DM, Kubik MF, Steiner W. J Mol Biol 1997, 272:688-698. doi:10.1006/jmbi.1997.1275; Kretz CA et al. JBC 2015",
        "sequence_verification": "AGGGC variant consistent with RCSB 4I7Y chain D (27-mer truncate, fetched 2026-08-03); full 29-mer = truncate + 5'-A + 3'-T",
    },
    {
        "id": "hd22_t27_thrombin",
        "name": "HD22[27] truncate",
        "target": "Thrombin",
        "protein": {"type": "benchmark_pdb", "pdb_id": "1HAO", "chain": "H"},
        "sequence": "GTCCGTGGTAGGGCAGGTTGGGGTGAC",
        "alphabet": "dna",
        "length_nt": 27,
        "kd_nm": 0.7,
        "kd_method": "SPR (Kretz 2015)",
        "role": "binder",
        "reference": "Kretz CA et al. JBC 2015; co-crystal PDB 4I7Y (Russo Krauss et al.)",
        "sequence_verification": "exact match to RCSB 4I7Y chain D fetched 2026-08-03",
    },
    {
        "id": "toggle25t_thrombin",
        "name": "Toggle-25t (2'-F RNA), exosite II",
        "target": "Thrombin",
        "protein": {"type": "benchmark_pdb", "pdb_id": "1HAO", "chain": "H"},
        "sequence": "GGGAACAAAGCUGAAGUACUUACCC",
        "alphabet": "rna",
        "length_nt": 25,
        "kd_nm": 0.54,
        "kd_method": "double-filter nitrocellulose filter binding, vs human thrombin (White 2001)",
        "role": "binder",
        "reference": "White R et al. Mol Ther 2001, 4:567-573. doi:10.1006/mthe.2001.0500",
        "sequence_verification": "exact match to first 25 nt of RCSB 3DD2 chain B (26-mer incl. 3'-dT) fetched 2026-08-03",
    },
    {
        "id": "tba_thrombin",
        "name": "TBA / HD1 (15-mer), exosite I",
        "target": "Thrombin",
        "protein": {"type": "benchmark_pdb", "pdb_id": "1HAO", "chain": "H"},
        "sequence": TBA_DNA,
        "alphabet": "dna",
        "length_nt": 15,
        "kd_nm": 25.0,
        "kd_method": "filter binding (Bock 1992 / Paborsky 1993, pmid:8318863)",
        "role": "binder",
        "reference": "pmid:8318863 (value as curated in known_aptamers.json)",
        "sequence_verification": "identical to known_aptamers.json entry",
    },
    {
        "id": "nu172_thrombin",
        "name": "NU172 (ARC2172), exosite I, Phase II",
        "target": "Thrombin",
        "protein": {"type": "benchmark_pdb", "pdb_id": "1HAO", "chain": "H"},
        "sequence": "CGCCTAGGTTGGGTAGGGTGGTGGCG",
        "alphabet": "dna",
        "length_nt": 26,
        "kd_nm": None,
        "kd_method": "no primary-literature Kd (Archemix internal); functional IC50 5-10 ug/mL ecarin clotting (secondary: Keefe 2010 NRDD)",
        "role": "binder_no_kd",
        "reference": "Keefe AD, Pai S, Ellington A. Nat Rev Drug Discov 2010, 9:537-550 (secondary)",
        "sequence_verification": "multi-source consistent 26-mer (HAL theses/IJMS review); AUROC use only",
    },
    # ── VEGF165 ──
    {
        "id": "pegaptanib_vegf",
        "name": "pegaptanib (Macugen, NX1838), unmodified base sequence",
        "target": "VEGF",
        "protein": {"type": "benchmark_pdb", "pdb_id": "1VPF", "chain": "A"},
        "sequence": "CGGAAUCAGUGAAUGCUUAUACAUCCG",
        "alphabet": "rna",
        "length_nt": 27,
        "kd_nm": 0.049,
        "kd_method": "Tucker 1999 rhesus plasma assay; FDA review estimate ~0.2 nM; Lee 2005 PNAS ~0.05 nM",
        "role": "binder",
        "reference": "identical to pegaptanib.json anchor (Tucker 1999; Ruckman 1998 JBC 273:20556)",
        "sequence_verification": "identical to pegaptanib.json anchor",
    },
    # ── PDGF-BB ──
    {
        "id": "pdgf36t_pdgfbb",
        "name": "PDGF-B aptamer '36t' (40-mer + 3'-idT in literature)",
        "target": "PDGF-BB",
        "protein": {"type": "uniprot_fasta", "uniprot": "P01127", "range": "82-190", "fasta": "proteins/pdgfbb.fa"},
        "sequence": "CACAGGCTACGGCACGTAGAGCATCACCATGATCCTGTGT",
        "alphabet": "dna",
        "length_nt": 40,
        "kd_nm": 0.094,
        "kd_method": "filter binding (Green 1996)",
        "role": "binder",
        "reference": "Green LS et al. Biochemistry 1996, 35:14413-14424",
        "sequence_verification": "Aptagen entry verbatim (40 nt); 3'-idT cap excluded",
    },
    {
        "id": "pdgf41t_pdgfbb",
        "name": "PDGF-B aptamer '41t' (45-mer, second clone family)",
        "target": "PDGF-BB",
        "protein": {"type": "uniprot_fasta", "uniprot": "P01127", "range": "82-190", "fasta": "proteins/pdgfbb.fa"},
        "sequence": "TACTCAGGGCACTGCAAGCAATTGTGGTCCCAATGGGCTGAGTAT",
        "alphabet": "dna",
        "length_nt": 45,
        "kd_nm": 0.1,
        "kd_method": "filter binding, same order of magnitude as 36t (Green 1996, via thesis citation — MEDIUM confidence)",
        "role": "binder",
        "confidence": "medium",
        "reference": "Green LS et al. Biochemistry 1996, 35:14413-14424 (cited via Auburn thesis)",
        "sequence_verification": "45 nt; secondary-source transcription — flagged medium confidence",
    },
    # ── IgE ──
    {
        "id": "d17_4_ige",
        "name": "D17.4 (anti-IgE, inhibits IgE-Fc-epsilon-RI)",
        "target": "IgE",
        "protein": {"type": "uniprot_fasta", "uniprot": "P01854", "range": "full", "fasta": "proteins/ige_fc.fa"},
        "sequence": "GGGGCACGTTTATCCGTCCCTCCTAGTGGCGTGCCCC",
        "alphabet": "dna",
        "length_nt": 37,
        "kd_nm": 10.0,
        "kd_method": "filter binding, PBS + 1 mM MgCl2 pH 7.4 (Wiegand 1996)",
        "role": "binder",
        "reference": "Wiegand TW et al. J Immunol 1996, 157:221-230",
        "sequence_verification": "37-mer verbatim per Poongavanam 2016 BBA",
    },
    # ── SARS-CoV-2 Nucleocapsid ──
    {
        "id": "sarsn_aptamer",
        "name": "SARS-CoV-2 N RNA aptamer",
        "target": "SARS-CoV-2_Nucleocapsid",
        "protein": {"type": "benchmark_pdb", "pdb_id": "6M3M", "chain": "A"},
        "sequence": "AGGGGAGUGGAGGUUGGUUU",
        "alphabet": "rna",
        "length_nt": 20,
        "kd_nm": 15.2,
        "kd_method": "as curated in known_aptamers.json (doi:10.1101/2020.04.17.046920)",
        "role": "binder",
        "reference": "identical to known_aptamers.json entry",
        "sequence_verification": "identical to known_aptamers.json entry",
    },
    # ── Synthetic negatives (AUROC / sensitivity only) ──
    {
        "id": "scrambled_tba",
        "name": "scrambled TBA (fixed seed 0) — disrupts G-tracts",
        "target": "Thrombin",
        "protein": {"type": "benchmark_pdb", "pdb_id": "1HAO", "chain": "H"},
        "sequence": _scramble(TBA_DNA, 0),
        "alphabet": "dna",
        "length_nt": 15,
        "kd_nm": None,
        "kd_assigned_nm_for_sensitivity": 10000,
        "kd_method": "literature: no detectable binding by SPR at uM detection limit (Bock 1992; HAL hal-01682623)",
        "role": "negative",
        "reference": "Bock LC et al. Nature 1992, 355:564-566; hal-01682623 (qualitative)",
    },
    {
        "id": "random30_a",
        "name": "random 30-mer (fixed seed 1)",
        "target": "Thrombin",
        "protein": {"type": "benchmark_pdb", "pdb_id": "1HAO", "chain": "H"},
        "sequence": _random_dna(30, 1),
        "alphabet": "dna",
        "length_nt": 30,
        "kd_nm": None,
        "kd_assigned_nm_for_sensitivity": 10000,
        "role": "negative",
    },
    {
        "id": "random30_b",
        "name": "random 30-mer (fixed seed 2)",
        "target": "PDGF-BB",
        "protein": {"type": "uniprot_fasta", "uniprot": "P01127", "range": "82-190", "fasta": "proteins/pdgfbb.fa"},
        "sequence": _random_dna(30, 2),
        "alphabet": "dna",
        "length_nt": 30,
        "kd_nm": None,
        "kd_assigned_nm_for_sensitivity": 10000,
        "role": "negative",
    },
    {
        "id": "random45_a",
        "name": "random 45-mer (fixed seed 3, length-matched to pdgf41t)",
        "target": "PDGF-BB",
        "protein": {"type": "uniprot_fasta", "uniprot": "P01127", "range": "82-190", "fasta": "proteins/pdgfbb.fa"},
        "sequence": _random_dna(45, 3),
        "alphabet": "dna",
        "length_nt": 45,
        "kd_nm": None,
        "kd_assigned_nm_for_sensitivity": 10000,
        "role": "negative",
    },
    {
        "id": "random37_a",
        "name": "random 37-mer (fixed seed 4, length-matched to D17.4)",
        "target": "IgE",
        "protein": {"type": "uniprot_fasta", "uniprot": "P01854", "range": "full", "fasta": "proteins/ige_fc.fa"},
        "sequence": _random_dna(37, 4),
        "alphabet": "dna",
        "length_nt": 37,
        "kd_nm": None,
        "kd_assigned_nm_for_sensitivity": 10000,
        "role": "negative",
    },
]

PROTEIN_FASTAS = {
    "pdgfbb.fa": (">PDGFB_HUMAN_mature_chain|UniProt P01127:82-190|fetched 2026-08-03\n", PDGFB_MATURE),
    "ige_fc.fa": (">IGHE_HUMAN_constant_region|UniProt P01854|fetched 2026-08-03\n", UNIPROT_IGHE_P01854),
}

SOURCES_MD = """\n## calibration_set.json (pilot P2, curated 2026-08-03)\n\n- Thrombin series: HD22 (doi:10.1006/jmbi.1997.1275), HD22[27] (PDB 4I7Y sequence; Kretz 2015 JBC), Toggle-25t (doi:10.1006/mthe.2001.0500; PDB 3DD2), TBA (pmid:8318863), NU172 (sequence multi-source; no primary Kd — AUROC only)\n- VEGF: pegaptanib (see pegaptanib.json)\n- PDGF-BB: 36t/41t (Green 1996 Biochemistry 35:14413); protein = UniProt P01127 mature chain 82-190 (https://rest.uniprot.org/uniprotkb/P01127.fasta, fetched 2026-08-03)\n- IgE: D17.4 (Wiegand 1996 J Immunol 157:221); protein = UniProt P01854 constant region (fetched 2026-08-03)\n- SARS-CoV-2 N: see known_aptamers.json\n- Negatives: scrambled TBA (seed 0; literature: no detectable binding, Bock 1992 + hal-01682623) and fixed-seed random sequences (seeds 1-4)\n"""


def main() -> None:
    PROTEIN_DIR.mkdir(parents=True, exist_ok=True)
    for fname, (header, seq) in PROTEIN_FASTAS.items():
        wrapped = "\n".join(seq[i : i + 60] for i in range(0, len(seq), 60))
        (PROTEIN_DIR / fname).write_text(header + wrapped + "\n")

    # Curation-time validation: claimed length must equal actual length.
    problems = []
    for e in ENTRIES:
        actual = len(e["sequence"])
        if actual != e["length_nt"]:
            problems.append(f"{e['id']}: claimed {e['length_nt']} != actual {actual}")
    if problems:
        raise SystemExit("LENGTH MISMATCH:\n" + "\n".join(problems))

    doc = {
        "description": "Known-aptamer affinity calibration set for the EGARPS scoring chain (pilot P2). Primary analysis: within-target Spearman(native_probability, -log Kd) on role=binder entries with kd_nm; secondary: binder vs negative AUROC per target.",
        "curated": "2026-08-03",
        "convention": "DNA aptamers scored as RNA via T->U (same convention as known_aptamers.json/TBA).",
        "n_entries": len(ENTRIES),
        "entries": ENTRIES,
    }
    out = ANCHOR_DIR / "calibration_set.json"
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    sources = ANCHOR_DIR.parent / "SOURCES.md"
    with sources.open("a", encoding="utf-8") as fh:
        fh.write(SOURCES_MD)

    n_q = sum(1 for e in ENTRIES if e["role"] == "binder" and e.get("kd_nm") is not None)
    print(f"wrote {out} ({len(ENTRIES)} entries, {n_q} quantitative binders)")
    for t in sorted({e['target'] for e in ENTRIES}):
        pts = [(e['id'], e.get('kd_nm')) for e in ENTRIES if e['target'] == t]
        print(f"  {t}: {pts}")


if __name__ == "__main__":
    main()
