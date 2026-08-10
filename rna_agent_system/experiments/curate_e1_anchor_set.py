#!/usr/bin/env python3
"""Curate the E1 oracle-capability-profiling anchor set (2026-08-04).

Extends the P2 calibration_set.json (15 entries, 5 targets) into the E1 pilot
anchor set per REDESIGN_2026-08-03_CALIBRATED_AGENT.md §3 E1:
  3 targets (Thrombin / VEGF / PDGF-BB), per target:
    - >= 4 binders with a Kd affinity gradient (ranking power)
    - >= 3 fixed-seed negatives (screening power)
    - native/decoy conformation pairs where an experimental complex structure
      exists (docking power) — Thrombin only (4DII/4I7Y/3DD2); VEGF and
      PDGF-BB have NO experimental aptamer complex (RCSB-verified 2026-08-04)
      so docking power is N/A for them (honest pilot limitation).

New literature entries were verified by an independent literature pass
(2026-08-04): sequences printed in paper text/tables only (figure-only
sequences excluded per project discipline, PIVOT §3.13):
  - VEGF series: Kaur & Yung 2012 PLoS ONE 7(2):e31196 (Table 1, SPR vs
    VEGF165; SL2-B/SL12/SL2-A/SL2/VEa5 + SL1 "No Binding") and
    Nonaka, Sode & Ikebukuro 2010 Molecules 15:215-225 (Tables 1-3; V7t1,
    Vap7).
  - PDGF-BB series: Ahmad et al. 2011 PLoS ONE 6(11):e27051 (M-SELEX,
    Table 1 60-nt variable regions; Kd measured on the 100-mer construct
    with primer arms AGCAGCACAGAGGTCAGATG-[60N]-CCTATGCGTGCTACCGTGAA).

Internal-consistency checks asserted below:
  - VEa5 nested family: SL12 = VEa5[1-38], SL2-B = VEa5[14-39],
    SL2-A = VEa5[21-39], SL2 = VEa5[22-38] (1-based, per Kaur Fig. 2)
  - V7t1 core is a substring of Vap7 (same library, Nonaka 2010)
  - hd22_t27 == RCSB 4I7Y chain D sequence; tba == 1HUT/4DII sequence;
    toggle25t == RCSB 3DD2 sequence minus the 3'-terminal dT
Convention: DNA aptamers scored as RNA via T->U (same as calibration_set).

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/curate_e1_anchor_set.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT  # noqa: E402

APTAMER_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers"
P2_SET = APTAMER_DIR / "calibration_set.json"
OUT = APTAMER_DIR / "e1_anchor_set.json"

THROMBIN_PROTEIN = {"type": "benchmark_pdb", "pdb_id": "1HAO", "chain": "H"}
VEGF_PROTEIN = {"type": "benchmark_pdb", "pdb_id": "1VPF", "chain": "A"}
PDGF_PROTEIN = {
    "type": "uniprot_fasta",
    "uniprot": "P01127",
    "range": "82-190",
    "fasta": "proteins/pdgfbb.fa",
}

KAUR_REF = ("Kaur G, Yung LYL. PLoS ONE 2012, 7(2):e31196. doi:10.1371/journal.pone.0031196 "
            "(Table 1; SPR BIAcore, VEGF165 on CM5, PBS+0.005% Tween-20, 1:1 Langmuir)")
NONAKA_REF = ("Nonaka Y, Sode K, Ikebukuro K. Molecules 2010, 15(1):215-225. "
              "doi:10.3390/molecules15010215 (Tables 1-3; SPR, TBSE+50mM KCl)")
AHMAD_REF = ("Ahmad KM, Oh SS, Kim S, McClellen FM, Xiao Y, Soh HT. PLoS ONE 2011, "
             "6(11):e27051. doi:10.1371/journal.pone.0027051 (M-SELEX, Table 1 60-nt "
             "variable region; Kd bead fluorescence assay on 100-mer with primer arms "
             "AGCAGCACAGAGGTCAGATG-[60N]-CCTATGCGTGCTACCGTGAA, PBS+1mM MgCl2+0.025% Tween-20)")

# ── New VEGF binders (Kaur 2012 + Nonaka 2010), DNA, Kd vs VEGF165 ─────────
VEA5 = "ATACCAGTCTATTCAATTGGGCCCGTCCGTATGGTGGGTGTGCTGGCCAGATAGTATGTGCAATCA"
VAP7 = "ATACCAGTCTATTCAATTGCACTCTGTGGGGGTGGACGGGCCGGGTAGATAGTATGTGCAATC"
V7T1 = "TGTGGGGGTGGACGGGCCGGGTAGA"

NEW_VEGF = [
    dict(id="sl2b_vegf", name="SL(2)-B truncated VEGF165 aptamer", seq="CAATTGGGCCCGTCCGTATGGTGGGT",
         kd=0.5, kd_method="SPR 0.50±0.32 nM (Kaur 2012 Table 1)", ref=KAUR_REF,
         verify="nested truncate of VEa5 (positions 14-39); asserted below"),
    dict(id="v7t1_vegf", name="V7t1 VEGF aptamer (random region of Vap7)", seq=V7T1,
         kd=1.4, kd_method="SPR 1.4 nM vs VEGF165, 1.1 nM vs VEGF121 (Nonaka 2010 Table 3)", ref=NONAKA_REF,
         verify="printed in abstract + Table 2; core substring of Vap7 asserted below"),
    dict(id="sl12_vegf", name="SL12 truncated VEGF165 aptamer", seq="ATACCAGTCTATTCAATTGGGCCCGTCCGTATGGTGGG",
         kd=5.0, kd_method="SPR 5±0.45 nM (Kaur 2012 Table 1)", ref=KAUR_REF,
         verify="nested truncate of VEa5 (positions 1-38); asserted below"),
    dict(id="sl2a_vegf", name="SL(2)-A truncated VEGF165 aptamer", seq="GCCCGTCCGTATGGTGGGT",
         kd=10.0, kd_method="SPR 10±1.1 nM (Kaur 2012 Table 1)", ref=KAUR_REF,
         verify="nested truncate of VEa5 (positions 21-39); asserted below"),
    dict(id="vap7_vegf", name="Vap7 full-length VEGF aptamer (with primer arms)", seq=VAP7,
         kd=20.0, kd_method="SPR 20 nM vs VEGF165, 1.0 nM vs VEGF121 (Nonaka 2010 Table 3)", ref=NONAKA_REF,
         verify="Kd measured on 63-mer incl. primer arms (Table 1/2)"),
    dict(id="sl2_vegf", name="SL(2) minimal VEGF165 aptamer", seq="CCCGTCCGTATGGTGGG",
         kd=49.0, kd_method="SPR 49±2.4 nM (Kaur 2012 Table 1)", ref=KAUR_REF,
         verify="nested truncate of VEa5 (positions 22-38); asserted below"),
    dict(id="vea5_vegf", name="VEa5 full-length VEGF165 aptamer (Hasegawa 2008 clone)", seq=VEA5,
         kd=120.0, kd_method="SPR 120±1.8 nM re-measurement (Kaur 2012 Table 1; original 130 nM Hasegawa 2008)",
         ref=KAUR_REF + "; Hasegawa H et al. 2008 (original clone)",
         verify="parent sequence of the SL12/SL2-B/SL2-A/SL2 nested truncates"),
]

# ── New PDGF-BB binders (Ahmad 2011 M-SELEX, Table 1 variable regions) ─────
# Sequences re-verified 2026-08-04 against the Europe PMC full text of
# PMC3215713 (Table 1). NOTE: PDGF-08 is printed as a 58-nt clone (the table
# header calls the class "60-mer"); we store the printed sequence as-is.
# Same paper, thrombin clones (Kd vs thrombin, bead assay, 100-mer incl. arms):
#   Thr-02 0.65 nM, Thr-08 0.33 nM — added to the Thrombin gradient below.
NEW_PDGF = [
    dict(id="mselex09_pdgfbb", name="M-SELEX clone PDGF-09 (60-nt variable region)", seq="GAATCATGATCCCCCATGACCTGGGGGCGTTACTGGCGAGCATCATGAGAGATCGTGCGA",
         kd=0.028, kd_method="bead fluorescence assay, Kd on 100-mer incl. primer arms (Ahmad 2011 Table 1)", ref=AHMAD_REF),
    dict(id="mselex01_pdgfbb", name="M-SELEX clone PDGF-01 (60-nt variable region)", seq="CACGCGTACAAGTTGGGTGGAAGCATAGGCAATGAGCTCTCATTGGGTTACCTTTAAGGT",
         kd=0.10, kd_method="bead fluorescence assay, Kd on 100-mer incl. primer arms (Ahmad 2011 Table 1)", ref=AHMAD_REF),
    dict(id="mselex08_pdgfbb", name="M-SELEX clone PDGF-08 (58-nt printed variable region)", seq="GTTGCATATTGAGCATCGTGTAATGATCCTGCAAAGGCATTATGCATCGGGTCTTCCT",
         kd=0.30, kd_method="bead fluorescence assay, Kd on 100-mer incl. primer arms (Ahmad 2011 Table 1; printed clone is 58 nt despite the '60-mer' table header)", ref=AHMAD_REF),
]

# ── New Thrombin binders (Ahmad 2011 M-SELEX, Table 1, verified 2026-08-04)
NEW_THROMBIN = [
    dict(id="mselex_thr08_thrombin", name="M-SELEX clone Thr-08 (60-nt variable region)", seq="CAGCGCTAGGGCTTTTAGCGTAATGGGTAGGGTGGTGCGGTGCAGATATCGGAATTGGTG",
         kd=0.33, kd_method="bead fluorescence assay, Kd on 100-mer incl. primer arms (Ahmad 2011 Table 1)", ref=AHMAD_REF),
    dict(id="mselex_thr02_thrombin", name="M-SELEX clone Thr-02 (60-nt variable region)", seq="TTGAAGTAATTTTATAGGTCTTTTATTGGGTAGGGTGGTTTTAATTGGTGTGACAAATTG",
         kd=0.65, kd_method="bead fluorescence assay, Kd on 100-mer incl. primer arms (Ahmad 2011 Table 1)", ref=AHMAD_REF),
]

# ── Docking-power native anchors (RCSB-verified 2026-08-04) ────────────────
DOCKING_ANCHORS = [
    {"aptamer_entry": "tba_thrombin", "pdb_id": "4DII", "aptamer_chain": "D",
     "protein_chains": ["H", "L"], "method": "X-ray 2.05 A (K+)",
     "reference": "Russo Krauss et al. NAR 2012 gks512",
     "notes": "PDB sequence == literature TBA15 exactly; preferred over 1HUT (2.9 A, high clashscore)"},
    {"aptamer_entry": "hd22_t27_thrombin", "pdb_id": "4I7Y", "aptamer_chain": "D",
     "protein_chains": ["H", "L"], "method": "X-ray 2.40 A",
     "reference": "Russo Krauss et al. Acta Cryst D 2013, doi:10.1107/S0907444913022269",
     "notes": "HD22-27mer truncate (29mer minus 5'-A/3'-T); exosite II; thrombin gamma-autolysis "
              "loop 146A-146H + res 247 missing — exclude from pose RMSD"},
    {"aptamer_entry": "toggle25t_thrombin", "pdb_id": "3DD2", "aptamer_chain": "B",
     "protein_chains": ["H", "L"], "method": "X-ray 1.90 A",
     "reference": "Long, Long, White, Sullenger. RNA 2008, PMID 18971322",
     "notes": "PDB adds a 3'-dT vs the 25-nt literature sequence; 10 pyrimidines are 2'-F "
              "(score as unmodified RNA per project convention)"},
]
DOCKING_NA = {
    "VEGF": "no experimental aptamer-VEGF complex in RCSB (verified 2026-08-04); docking power N/A",
    "PDGF-BB": "only SOMAmer SL5/SL4 complexes (4HQU/4HQX, 13/24 modified bases, different "
               "aptamer family) — not usable for the classic 36t/41t/M-SELEX entries; docking power N/A",
}


def _entry(eid: str, name: str, target: str, protein: dict, seq: str, kd, role: str,
           reference: str, kd_method: str | None = None, verify: str | None = None) -> dict:
    e = {
        "id": eid,
        "name": name,
        "target": target,
        "protein": protein,
        "sequence": seq,
        "alphabet": "dna",
        "length_nt": len(seq),
        "kd_nm": kd,
        "role": role,
        "reference": reference,
    }
    if kd_method:
        e["kd_method"] = kd_method
    if verify:
        e["sequence_verification"] = verify
    return e


def _random_seq(seed: int, length: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("ACGT") for _ in range(length))


def _scramble(seed: int, seq: str) -> str:
    rng = random.Random(seed)
    chars = list(seq)
    rng.shuffle(chars)
    return "".join(chars)


def main() -> int:
    p2 = json.loads(P2_SET.read_text())
    p2_by_id = {e["id"]: e for e in p2["entries"]}

    # ── Internal-consistency assertions (literature transcription checks) ──
    assert VEA5[:38] == "ATACCAGTCTATTCAATTGGGCCCGTCCGTATGGTGGG", "SL12 != VEa5[1-38]"
    assert VEA5[13:39] == "CAATTGGGCCCGTCCGTATGGTGGGT", "SL2-B != VEa5[14-39]"
    assert VEA5[20:39] == "GCCCGTCCGTATGGTGGGT", "SL2-A != VEa5[21-39]"
    assert VEA5[21:38] == "CCCGTCCGTATGGTGGG", "SL2 != VEa5[22-38]"
    assert V7T1 in VAP7, "V7t1 core not a substring of Vap7"
    assert p2_by_id["hd22_t27_thrombin"]["sequence"] == "GTCCGTGGTAGGGCAGGTTGGGGTGAC", "hd22_t27 != 4I7Y chain D"
    assert p2_by_id["tba_thrombin"]["sequence"] == "GGTTGGTGTGGTTGG", "tba != 4DII sequence"
    assert p2_by_id["toggle25t_thrombin"]["sequence"].upper().replace("T", "U") == "GGGAACAAAGCUGAAGUACUUACCC", "toggle25t != 3DD2 minus 3'-dT"
    # Ahmad 2011 Table 1 re-verified verbatim against Europe PMC PMC3215713 full
    # text (2026-08-04); PDGF-08 is printed as a 58-nt clone, stored as-is.
    assert [len(e["seq"]) for e in NEW_PDGF] == [60, 60, 58]
    assert [len(e["seq"]) for e in NEW_THROMBIN] == [60, 60]

    entries: list[dict] = []

    # ── Thrombin: reuse the 5 verified P2 binders + 2 negatives, add 2 M-SELEX
    #    binders (Kd gradient 0.33-25 nM over 6 points) + 1 negative
    for eid in ["hd22_thrombin", "hd22_t27_thrombin", "toggle25t_thrombin", "tba_thrombin",
                "nu172_thrombin", "scrambled_tba", "random30_a"]:
        entries.append(p2_by_id[eid])
    for e in NEW_THROMBIN:
        entries.append(_entry(e["id"], e["name"], "Thrombin", THROMBIN_PROTEIN, e["seq"], e["kd"],
                              "binder", e["ref"], e["kd_method"]))
    entries.append(_entry(
        "scrambled_hd22", "scrambled HD22 (fixed seed 10) — preserves base composition",
        "Thrombin", THROMBIN_PROTEIN, _scramble(10, p2_by_id["hd22_thrombin"]["sequence"]),
        None, "negative",
        "generated in silico (seed 10); composition-matched scramble of hd22_thrombin",
    ))

    # ── VEGF: pegaptanib + 7 new binders + 3 negatives (1 literature non-binder)
    entries.append(p2_by_id["pegaptanib_vegf"])
    for e in NEW_VEGF:
        entries.append(_entry(e["id"], e["name"], "VEGF", VEGF_PROTEIN, e["seq"], e["kd"],
                              "binder", e["ref"], e["kd_method"], e["verify"]))
    entries.append(_entry(
        "sl1_vegf_no_binding", "SL1 VEGF aptamer fragment — experimentally No Binding",
        "VEGF", VEGF_PROTEIN, "ATACCAGTCTATTCAATTGG", None, "negative",
        KAUR_REF, "SPR: 'No Binding' annotation in Kaur 2012 Table 1",
        "literature-validated non-binder (not in silico)"))
    entries.append(_entry(
        "random26_vegf", "random 26-mer (fixed seed 11)", "VEGF", VEGF_PROTEIN,
        _random_seq(11, 26), None, "negative", "generated in silico (seed 11)"))
    entries.append(_entry(
        "random38_vegf", "random 38-mer (fixed seed 12)", "VEGF", VEGF_PROTEIN,
        _random_seq(12, 38), None, "negative", "generated in silico (seed 12)"))

    # ── PDGF-BB: 2 P2 binders + 3 M-SELEX binders + 2 P2 negatives + 1 new
    for eid in ["pdgf36t_pdgfbb", "pdgf41t_pdgfbb", "random30_b", "random45_a"]:
        entries.append(p2_by_id[eid])
    for e in NEW_PDGF:
        entries.append(_entry(e["id"], e["name"], "PDGF-BB", PDGF_PROTEIN, e["seq"], e["kd"],
                              "binder", e["ref"], e["kd_method"]))
    entries.append(_entry(
        "random60_pdgfbb", "random 60-mer (fixed seed 13) — matches M-SELEX variable-region length",
        "PDGF-BB", PDGF_PROTEIN, _random_seq(13, 60), None, "negative",
        "generated in silico (seed 13)"))

    out = {
        "description": "E1 oracle capability-profiling anchor set (pilot, 3 targets). "
                       "CASF four-capability protocol: ranking (within-target Spearman on "
                       "role=binder with kd_nm), screening (binder vs negative AUROC per "
                       "target), docking (native vs decoy poses, Thrombin only), scoring "
                       "(reported, no threshold). Extends calibration_set.json (P2).",
        "curated": "2026-08-04",
        "convention": p2["convention"],
        "preregistration": "REDESIGN_2026-08-03_CALIBRATED_AGENT.md §3 E1 (approved 2026-08-04)",
        "n_entries": len(entries),
        "docking_anchors": DOCKING_ANCHORS,
        "docking_not_available": DOCKING_NA,
        "known_limitations": [
            "PDGF-BB Kd gradient spans only 0.028-0.3 nM (1 order) — within-target ranking "
            "analysis is underpowered; Soontornworajit 2010 mutants (25/220 nM) excluded "
            "because sequences are figure-only (PIVOT §3.13 discipline).",
            "Ahmad 2011 Kd values were measured on 100-mer constructs including primer arms; "
            "entries store the variable region only (PDGF-08 printed as 58 nt).",
            "Thrombin series mixes Kd assay methods (filter binding / SPR / bead assay); "
            "within-target ranking treats Kd as ordinal only (Spearman), cross-method "
            "comparability caveat carried over from P2.",
            "Docking power testable on Thrombin only (VEGF/PDGF-BB lack experimental complexes).",
        ],
        "entries": entries,
    }

    # ── Per-target pre-registered coverage check ──
    for target in ["Thrombin", "VEGF", "PDGF-BB"]:
        te = [e for e in entries if e["target"] == target]
        n_kd = len([e for e in te if e["role"] == "binder" and e.get("kd_nm") is not None])
        n_neg = len([e for e in te if e["role"] == "negative"])
        assert n_kd >= 4, f"{target}: {n_kd} kd-binders < 4"
        assert n_neg >= 3, f"{target}: {n_neg} negatives < 3"
        print(f"{target}: {n_kd} kd-binders, {n_neg} negatives, {len(te)} total")

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
