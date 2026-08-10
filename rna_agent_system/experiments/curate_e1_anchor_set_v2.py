#!/usr/bin/env python3
"""Curate the E1 EXTENSION anchor set v2 (2026-08-04, W3-4 milestone).

Extends the pilot e1_anchor_set.json (29 entries, 3 targets) to 6 Part-A
targets + 5 docking anchors, per the E1 EXTENSION PRE-REGISTRATION in
run_e1_capability_profiling.py docstring (2026-08-04).

Pilot entries (Thrombin/VEGF/PDGF-BB) are carried over VERBATIM (asserted).

New Part-A targets (all sequence + Kd evidence verified 2026-08-04 against
Europe PMC full texts / publisher PDFs cached in experiments/lit_cache/;
figure-only sequences excluded per project discipline, PIVOT §3.13):

  IL-17A (7 binders / 4 negatives)
    - Parvez, Sully & Baum 2026 RSC Adv (doi:10.1039/d6ra00178e): SI Table S7
      sequences + Table S8 FP Kd (same-assay ranking subset, n=6); 10CZ1
      (IL-20 aptamer) text-confirmed non-interfering with IL-17 binding.
    - Solovieva et al. 2026 Pharmaceuticals (PMC12943235) Table 1: Apt21-2
      (48.5 pM SPR, transcribed citation via Nakamura 2012 review of
      Ishiguro 2011 — flag ranking_eligible=False) and Scr control.
    - Adachi et al. 2011 Biochimie (PMID 21524680): AptAF42 binds IL-17A/F
      (72.2 nM) but NOT IL-17A/A (1.92 uM, text) — role=negative for the
      IL-17A homodimer target. Sequence DERIVED from the printed doped-
      library template (parental positions = template; derived length 69 nt
      == '69 nucleotide long' text; dope1 68 nt == text after C19del). The
      printed doped region is 31 nt vs the '30 nucleotides' text (registered). dope1
      derivative (C19del/A31C/U37G/G47U, applied programmatically, asserted)
      included as a 4th negative (2-4x AptAF42 on IL-17A/A, text).

  Angiopoietin-2 (5 kd-binders + 3 binder_no_kd / 3 negatives)
    - Shakeran et al. 2015 PLoS ONE (PMC4383501): Table 1 aptamer sequences
      (Seq1/Seq15/Seq16), Table 2 SPR constructs (biotin-AAAAA linker
      stripped), Table 3 SPR kinetics (Kd = kd/ka computed from printed
      ka/kd). Seq15_12_35 / Seq15_15_38 are two-point mutants of Seq15
      (positions in the name; derived programmatically, asserted against the
      Table 2 printout). Seq2_12_35 EXCLUDED: pdftotext layout of Table 2
      cannot be reconciled with Seq2 at constant length (registered).
    - Cho et al. 2014 Anal Chem SI (ac504076k): ABA1 (Kd 20.5 nM, Fig S1
      text), ABA65/92/109 (Kd range 37.6-57 nM text, individual values
      figure-only -> binder_no_kd), SC scrambled control ("negligible Ang2
      binding", Fig S5 text).
    - White et al. 2003 PNAS (PMID 12692304): 11-1.41 (= Seq1, Kd 2.2 nM
      filter binding via Shakeran text) / 11-1 (3.1 nM). 11-1 variable
      region == Seq1 (duplicate) -> not double-counted (registered).
    - Seq16 = Ang1-specific T40.14 truncate: Shakeran SPR Kd ~3 uM (same
      assay as the ranking subset) + text "no specificity for Ang2 (Kd > 1
      uM)" — literature-validated negative.

  SARS-CoV-2 nucleocapsid (12 binders / 3 negatives)
    - Poolsup et al. 2023 Mol Ther Nucleic Acids (PMC9927813): Table 1
      tNSP1/2/3 (BLI, streptavidin orientation), SI Table S1 full-length
      NSP1/2/3 (BLI Kd text), SI Table S2 tNSP5/9/10/12 + A48/A58 (BLI,
      Ni-NTA orientation — the ranking_eligible subset, n=6, span
      3.02-22.2 nM). Truncate<->parent nesting asserted; tNSP9 derives from
      the NSP7 row and tNSP10 from the NSP9 row of Table S1 (paper-internal
      naming offset, registered).
    - NEGATIVES ARE ALL IN SILICO (registered limitation): the paper's
      scrambled-DNA control (Sc80) sequence is NOT printed anywhere; 3
      fixed-seed generated negatives (pilot precedent).

REJECTED candidates (registered, not in the set):
  - SARS-CoV-2 spike RBD (Valero 2021 PMC8685691): only 2 single-sequence
    kd-binders (PB6, PB6a); di/trimer are multivalent scaffold constructs
    (avidity confound, not single scoreable sequences). Fails >=4 binders.
  - HIV-1 RT Part A: only ONE sequence-verified binder (T1.1 pseudoknot via
    1HVU SEQRES + Kensch 2000 printed 33-mer); Li 2008 12.01/12.01-S/M302
    and Kissel 2007 RT1t49 sequences are figure-only. Docking-only (1HVU).
  - Factor IXa Part A: a single aptamer family exists (9.3 lineage);
    9.3/9.3t sequences figure-only (Rusconi 2002). Docking-only (8EPK).
  - Tenascin-C: Hicke 2001 clone sequences + Kd all figure-only (Fig 5/10).
  - EGFR: E03/E04/E07 individual Kd figure-only (text gives range 2-3 nM).

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/curate_e1_anchor_set_v2.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT  # noqa: E402

APTAMER_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers"
PILOT_SET = APTAMER_DIR / "e1_anchor_set.json"
OUT = APTAMER_DIR / "e1_anchor_set_v2.json"
PROT_DIR = APTAMER_DIR / "proteins"

IL17A_PROTEIN = {"type": "uniprot_fasta", "uniprot": "Q16552", "range": "24-155",
                 "fasta": "proteins/il17a.fa"}
ANG2_PROTEIN = {"type": "uniprot_fasta", "uniprot": "O15123", "range": "20-496",
                "fasta": "proteins/ang2.fa"}
SARS2N_PROTEIN = {"type": "uniprot_fasta", "uniprot": "P0DTC9", "range": "1-419",
                  "fasta": "proteins/sars2n.fa"}

PARVEZ_REF = ("Parvez R, Sully E, Baum DA. RSC Advances 2026. doi:10.1039/d6ra00178e "
              "(SI Table S7 sequences, Table S8 FP Kd; main text: 'Low nanomolar Kd values "
              "were found for six of our tested IL-17 aptamers')")
SOLOVIEVA_REF = ("Solovieva et al. 2026 Pharmaceuticals (PMC12943235) Table 1; Apt21-2 Kd "
                 "48.5 pM SPR transcribed via Nakamura 2012 Genes Cells (PMC3444689) review "
                 "of Ishiguro 2011 (paywalled)")
ADACHI_REF = ("Adachi/Nakamura et al. 2011 Biochimie (PMID 21524680): AptAF42 KD(IL-17A/F)="
              "72.2 nM, KD(IL-17A/A)=1.92 uM, KD(IL-17F/F)=37.5 uM (text, Fig 2A)")
SHAKERAN_REF = ("Shakeran Z et al. 2015 PLoS ONE (PMC4383501): Table 1 sequences, Table 2 "
                "SPR constructs, Table 3 kinetics (Kd = kd/ka from printed ka, kd)")
CHO_REF = ("Cho M et al. 2014 Anal Chem (ac504076k) SI: Table S2 sequences; Fig S1 text "
           "'Kd = 20.5 ± 7.3 nM'; Fig S5 text 'a scrambled aptamer sequence showed "
           "negligible Ang2 binding'")
POOLSUP_REF = ("Poolsup S et al. 2023 Mol Ther Nucleic Acids (PMC9927813): Table 1 "
               "(tNSP1/2/3, BLI streptavidin orientation), SI Table S1 (full-length NSP "
               "sequences), SI Table S2 (tNSP5/9/10/12 + A48/A58, BLI Ni-NTA orientation)")

# ── IL-17A sequences (DNA, Parvez SELEX arms GAACTAGATCGCAGC...GGATCGAGGTAATCC) ──
IL17_ARM5 = "GAACTAGATCGCAGC"
IL17_ARM3 = "GGATCGAGGTAATCC"
IL17_FP = [  # (id, variable region, kd_nm) — Table S7/S8, same FP assay
    ("il17_9cs2", "CCAACCGGTGACGCACAGTTAGCAACGAATCCCCTAGCCTCGATATGACAGTCATACCCGTCGCATGTGG", 4.2),
    ("il17_9ct19", "CCACCGACACACACCGTATATCCCCTAGCCCCACATGAGGCCATCTCGCAACTGGACGTTCGCTTCTGGG", 5.3),
    ("il17_9cs3", "CTAATGCCCGTACATAGCCACGCATACTGTTTTTCTAATAAAGCTCCTTGAGGTGAACCGTCGCTGGGTG", 9.9),
    ("il17_9ct6", "CCCAGGGACGAGTATGGCGACATGGGATGGCACTAGTCGGTTGTCCAAACACGTTGATTTGTCCCCGGTG", 12.5),
]
IL17_SHOBEIRI_FULL = "GCTGTGTGACTCCTGCAATTAACTGTTTTCTTTTGTTTTTATGTTGTTGGCTTTTTCTTTTGCAGCTGTATCTTGTCTCC"
IL17_SHOBEIRI_TRUNC = "CGACTAACTGTTTTCTTTTGTTTTTAGTCG"
IL17_APT21_2 = "GGUCUAGCCGGAGGAGUCAGUAAUCGGUAGACC"  # 33-nt, 2'-F stripped (Solovieva Table 1)
IL17_SCR = "ACUGGUAUGUCGAGCCAACAAUCGAUACCAAGACUAAGA"  # 37-nt scrambled control (Solovieva Table 1)
IL17_10CZ1_VAR = "GGCAGCACACGTCCAGTGTAGGCGTCATCCCTCTATCCAATCGTCGTTCACAGCATTATCATGGGTTGTG"
# AptAF42: derive from the printed doped-library template (Adachi 2011 §2.2)
ADACHI_TEMPLATE = ("TAATACGACTCACTATA" "GGGCTAGCTGATCGTACC"
                   "cagtagcgtggcatggggtgcctagtcgggc"
                   "GATACTAACAGCTAACACCC")
T7_PROMOTER = "TAATACGACTCACTATA"

# ── Ang2 sequences (Shakeran Table 1/2, Cho SI Table S2) ──
ANG2_SEQ1 = "ACUAGCCUCAUCAGCUCAUGUGCCCCUCCGCCUGGAUCAC"   # = 11-1.41 truncate (40 nt)
ANG2_SEQ15 = "GAGGACGAUGCGGACUAGCCUCAUCAGCUCAUGUGCCCCUC"  # parent of the two mutants (41 nt)
ANG2_SEQ16 = "ACUCGAACAUUUCCACUAACCAACCAUACUAAAGCACCGC"   # Ang1-specific control (40 nt)
ANG2_ABA1 = "ACTTGTAGGGTTCGGCTGGTCAGGGTGTCCAAGTCTGTGG"    # DNA (40 nt)
ANG2_ABA65 = "TTTGGGGTGGTTGGGGGTTGTTGTTTTGGGGGTGGAGGGT"
ANG2_ABA92 = "GGTGCCATTGGGGACTGCTCGGGATTGCGGACTTGGCATC"
ANG2_ABA109 = "GGGTGCCATTGGGGACTGCTCGGGATTGCGGACTTGGCAT"
ANG2_SC = "GGGTTTGCGAAAGGGAAAGGGTTTGTGTTTTTTGGGTTTT"       # Cho scrambled control (DNA)


def _mutate(seq: str, muts: list[tuple[int, str]]) -> str:
    """Apply 1-based point mutations; assert the position is in range."""
    s = list(seq)
    for pos, base in muts:
        assert 1 <= pos <= len(s), f"mutation pos {pos} out of range"
        s[pos - 1] = base
    return "".join(s)


# ── SARS-CoV-2 N sequences (Poolspu Table 1 / SI Table S1/S2) ──
NSP_FULL = {
    "NSP1": "CTCCTCTGACTGTAACCACGGCGCAAGCCGGGGTGTACGTGTTATACGTGCGTGTATCGAGCATAGGTAGTCCAGAAGCC",
    "NSP2": "CTCCTCTGACTGTAACCACGTATTGCGTTCCAGTCCCTATGACCAACGTCACAATAAGTCGCATAGGTAGTCCAGAAGCC",
    "NSP3": "CTCCTCTGACTGTAACCACGCAGCGTCACGTGTTGTTCCCCATTGTACTGATTCGTCGTGGCATAGGTAGTCCAGAAGCC",
    "NSP5": "CTCCTCTGACTGTAACCACGATTCATGCGCCAATAGTGGTTTGGAAATGTCTCCCCATACGCATAGGTAGTCCAGAAGCC",
    "NSP7": "CTCCTCTGACTGTAACCACGTGCTAGATTACGTAACTGGTTGCTACGGGTTTCATCCTCGGCATAGGTAGTCCAGAAGCC",
    "NSP9": "CTCCTCTGACTGTAACCACGCTTATGCACCAGGGGCCCGGTTCGGGCAGGCGCAAACACGGCATAGGTAGTCCAGAAGCC",
    "NSP12": "CTCCTCTGACTGTAACCACGTGGTTCGCCCAGTTCCGTTCAATACACTCAACCCTGCACGGCATAGGTAGTCCAGAAGCC",
}
# (id, truncate, parent row in Table S1, kd_nm, assay orientation)
N_TRUNC = [
    ("n_tnsp1", "TAACCACGGCGCAAGCCGGGGTGTACGTGTTATACGTGCGTGTATCGAG", "NSP1", 4.83, "BLI streptavidin (aptamer immobilized)"),
    ("n_tnsp2", "CTGACTGTAACCACGTATTGCGTTCCAGTCCCTATGACCAACGTCACAATAAGTCGCATAGGTA", "NSP2", 4.51, "BLI streptavidin (aptamer immobilized)"),
    ("n_tnsp3", "CAGCGTCACGTGTTGTTCCCCATTGTACTGATTCGTCGTGGCAT", "NSP3", 2.91, "BLI streptavidin (aptamer immobilized)"),
    ("n_tnsp5", "ATTCATGCGCCAATAGTGGTTTGGAAATGTCTCCCCATACGCATAG", "NSP5", 12.6, "BLI Ni-NTA (N immobilized)"),
    ("n_tnsp9", "TGTAACCACGTGCTAGATTACGTAACTGGTTGCTACGGGTTTCATCCTCGGCATAGGTA", "NSP7", 22.2, "BLI Ni-NTA (N immobilized)"),
    ("n_tnsp10", "CTTATGCACCAGGGGCCCGGTTCGGGCAGGCGCAAACACGGCATAGG", "NSP9", 8.60, "BLI Ni-NTA (N immobilized)"),
    ("n_tnsp12", "TGTAACCACGTGGTTCGCCCAGTTCCGTTCAATACACTCAACCCTGCACGGCATAGGTA", "NSP12", 6.05, "BLI Ni-NTA (N immobilized)"),
]
N_A48 = "GCTGGATGTCGCTTACGACAATATTCCTTAGGGGCACCGCTACATTGACACATCCAGC"  # 58 nt, Table S2
N_A58 = "GCTGGATGTCACCGGATTGTCGGACATCGGATTGTCTGAGTCATATGACACATCCAGC"  # 58 nt, Table S2
N_FULL_KD = {"NSP1": 7.86, "NSP2": 4.38, "NSP3": 8.60}

# ── 1HVU / Kensch cross-check (HIV-1 RT docking anchor) ──
HVU_SEQRES_C = "AGAUUCCGUUUUCAGUCGGGAAAAACUGAA"        # 30 nt (1HVU chain C)
KENSCH_T1_1 = "GGGAGAUUCCGUUUUCAGUCGGGAAAAACUGAA"      # 33 nt (Kensch 2000 text)


def _random_seq(seed: int, length: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("ACGT") for _ in range(length))


def _entry(eid, name, target, protein, seq, kd, role, reference, alphabet="dna",
           kd_method=None, verify=None, ranking_eligible=None) -> dict:
    e = {"id": eid, "name": name, "target": target, "protein": protein,
         "sequence": seq, "alphabet": alphabet, "length_nt": len(seq),
         "kd_nm": kd, "role": role, "reference": reference}
    if kd_method:
        e["kd_method"] = kd_method
    if verify:
        e["sequence_verification"] = verify
    if ranking_eligible is not None:
        e["ranking_eligible"] = ranking_eligible
    return e


def _write_protein_fastas() -> None:
    """Mature-chain fastas from the fetched UniProt full-length files (asserted)."""
    def read_full(name: str) -> str:
        fa = (PROT_DIR / name).read_text().splitlines()
        return "".join(l for l in fa if not l.startswith(">"))
    specs = [
        ("il17a_full.fa", "il17a.fa", "IL17A_HUMAN_mature_chain|UniProt Q16552:24-155|fetched 2026-08-04", 24, 155),
        ("ang2_full.fa", "ang2.fa", "ANGP2_HUMAN_mature_chain|UniProt O15123:20-496|fetched 2026-08-04", 20, 496),
        ("sars2n_full.fa", "sars2n.fa", "NCAP_SARS2_full|UniProt P0DTC9:1-419|fetched 2026-08-04", 1, 419),
    ]
    for src, dst, header, a, b in specs:
        full = read_full(src)
        mat = full[a - 1:b]
        assert len(mat) == b - a + 1 and mat in full
        (PROT_DIR / dst).write_text(f">{header}\n" + "\n".join(
            mat[i:i + 60] for i in range(0, len(mat), 60)) + "\n")
        print(f"  wrote proteins/{dst} ({len(mat)} aa)")


def main() -> int:
    pilot = json.loads(PILOT_SET.read_text())
    entries: list[dict] = list(pilot["entries"])

    # ── Internal-consistency assertions (literature transcription checks) ──
    # IL-17A: FP binder arms + Shobeiri truncate core + AptAF42 derivation
    for eid, var, kd in IL17_FP:
        assert len(var) > 0 and set(var) <= set("ACGT")
    assert "AACTGTTTTCTTTTGTTTTTA" in IL17_SHOBEIRI_FULL and \
           "AACTGTTTTCTTTTGTTTTTA" in IL17_SHOBEIRI_TRUNC, "Shobeiri truncate core lost"
    assert ADACHI_TEMPLATE.startswith(T7_PROMOTER)
    aptaf42_dna = ADACHI_TEMPLATE[len(T7_PROMOTER):]
    APTAF42 = aptaf42_dna.upper().replace("T", "U")
    assert len(APTAF42) == 69, f"AptAF42 derived length {len(APTAF42)} != 69 (text: '69 nucleotide long')"
    APTAF42_DOPE1 = _mutate(APTAF42, [(31, "C"), (37, "G"), (47, "U")])
    APTAF42_DOPE1 = APTAF42_DOPE1[:18] + APTAF42_DOPE1[19:]  # C19 deletion (1-based)
    assert APTAF42[18] == "C" and len(APTAF42_DOPE1) == 68  # text: 'AptAF42dope1 (68 nts long)'
    # Ang2: mutants derived from Seq15 must match the Table 2 printouts (linker stripped)
    SEQ15_12_35 = _mutate(ANG2_SEQ15, [(12, "C"), (35, "C")])
    assert SEQ15_12_35 == "GAGGACGAUGCCGACUAGCCUCAUCAGCUCAUGUCCCCCUC"
    SEQ15_15_38 = _mutate(ANG2_SEQ15, [(15, "U"), (38, "G")])
    assert SEQ15_15_38 == "GAGGACGAUGCGGAUUAGCCUCAUCAGCUCAUGUGCCGCUC"
    # SARS-CoV-2 N: truncate<->parent nesting
    for eid, trunc, parent, kd, orient in N_TRUNC:
        assert trunc in NSP_FULL[parent], f"{eid} not a substring of {parent}"
    assert N_A48[:10] == "GCTGGATGTC" and N_A58[:10] == "GCTGGATGTC"
    assert N_A48[-12:] == "GACACATCCAGC" and N_A58[-12:] == "GACACATCCAGC"
    # 1HVU docking anchor cross-check
    assert HVU_SEQRES_C in KENSCH_T1_1, "1HVU chain C != Kensch T1.1 minus 5'-GGG"

    # ── IL-17A ──
    for eid, var, kd in IL17_FP:
        entries.append(_entry(
            eid, f"IL-17A aptamer {eid.split('_')[1].upper()} (Parvez FP, full 100-mer incl. arms)",
            "IL-17A", IL17A_PROTEIN, IL17_ARM5 + var + IL17_ARM3, kd, "binder", PARVEZ_REF,
            kd_method="fluorescence polarization (Parvez 2026 SI Table S8)",
            verify="sequence == SI Table S7 printout (arms GAACTAGATCGCAGC/GGATCGAGGTAATCC)",
            ranking_eligible=True))
    entries.append(_entry(
        "il17_shobeiri_apt2", "Shobeiri Aptamer 2 full-length (80-mer, Parvez FP re-measurement)",
        "IL-17A", IL17A_PROTEIN, IL17_SHOBEIRI_FULL, 3.1, "binder", PARVEZ_REF,
        kd_method="fluorescence polarization re-measurement (Parvez 2026 SI Table S8)",
        verify="sequence == SI Table S7; original: Shobeiri 2022 Int Immunopharmacol 110:108963",
        ranking_eligible=True))
    entries.append(_entry(
        "il17_shobeiri_apt2_trunc", "Shobeiri Truncated Aptamer 2 (30-mer, Parvez FP re-measurement)",
        "IL-17A", IL17A_PROTEIN, IL17_SHOBEIRI_TRUNC, 2.5, "binder", PARVEZ_REF,
        kd_method="fluorescence polarization re-measurement (Parvez 2026 SI Table S8)",
        verify="shares core AACTGTTTTCTTTTGTTTTTA with the full-length (asserted); re-ended truncate",
        ranking_eligible=True))
    entries.append(_entry(
        "il17_apt21_2", "Apt21-2 anti-IL-17A 2'-F RNA aptamer (scored unmodified, 3'-invT cap removed)",
        "IL-17A", IL17A_PROTEIN, IL17_APT21_2, 0.0485, "binder", SOLOVIEVA_REF, alphabet="rna",
        kd_method="SPR 48.5 pM vs IL-17A/A homodimer (transcribed citation: Nakamura 2012 review of Ishiguro 2011)",
        verify="decoded from Solovieva 2026 Table 1 2'-F notation (CF->C, UF->U)",
        ranking_eligible=False))
    entries.append(_entry(
        "il17_aptaf42", "AptAF42 — binds IL-17A/F but NOT IL-17A/A (KD 1.92 uM, 27x impaired)",
        "IL-17A", IL17A_PROTEIN, APTAF42, 1920.0, "negative", ADACHI_REF, alphabet="rna",
        kd_method="SPR KD(IL-17A/A) = 1.92 uM vs KD(IL-17A/F) = 72.2 nM (Adachi 2011 text)",
        verify="DERIVED from the printed doped-library template (parental = template); "
               "69 nt == '69 nucleotide long' text; doped region printed as 31 nt vs '30' text"))
    entries.append(_entry(
        "il17_aptaf42dope1", "AptAF42dope1 (C19del/A31C/U37G/G47U) — still 2-4x weaker on IL-17A/A than A/F",
        "IL-17A", IL17A_PROTEIN, APTAF42_DOPE1, None, "negative", ADACHI_REF, alphabet="rna",
        kd_method="SPR: 2-4x stronger than AptAF42 on IL-17A/A (text; no single value) — remains uM-range",
        verify="DERIVED by applying C19del/A31C/U37G/G47U to the template-derived AptAF42 (asserted)"))
    entries.append(_entry(
        "il17_10cz1", "10CZ1 anti-IL-20 aptamer — does not interfere with IL-17 binding (functional)",
        "IL-17A", IL17A_PROTEIN, IL17_ARM5 + IL17_10CZ1_VAR + IL17_ARM3, None, "negative", PARVEZ_REF,
        kd_method="TR-FRET: 'does not produce any decrease in FRET' (Parvez 2026 main text)",
        verify="sequence == SI Table S7 printout"))
    entries.append(_entry(
        "il17_scr", "Scr scrambled control for Apt21-2 (functional non-inhibitor)",
        "IL-17A", IL17A_PROTEIN, IL17_SCR, None, "negative", SOLOVIEVA_REF, alphabet="rna",
        kd_method="cell assays: 'did not demonstrate any significant effect' (Solovieva 2026)",
        verify="decoded from Solovieva 2026 Table 1 2'-F notation"))

    # ── Angiopoietin-2 ──
    spr = "SPR (Shakeran 2015 Table 3; Kd = kd/ka from printed ka/kd)"
    entries.append(_entry(
        "ang2_seq1_11_1_41", "Ang2 aptamer 11-1.41 truncate (= Shakeran Seq1)",
        "Angiopoietin-2", ANG2_PROTEIN, ANG2_SEQ1, 138.7, "binder", SHAKERAN_REF, alphabet="rna",
        kd_method=f"{spr}: ka 10.02e3, kd 1.39e-3 -> Kd 138.7 nM; White 2003 filter binding 2.2 nM (cross-assay, registered)",
        verify="Shakeran Table 1 == White 2003 Table 1 11-1 variable region; 40-nt printout vs '41-nt' text registered",
        ranking_eligible=True))
    entries.append(_entry(
        "ang2_seq15_12_35", "Ang2 aptamer Seq15 mutant (G12C, G35C; Shakeran SPR)",
        "Angiopoietin-2", ANG2_PROTEIN, SEQ15_12_35, 101.2, "binder", SHAKERAN_REF, alphabet="rna",
        kd_method=f"{spr}: ka 6.03e3, kd 0.61e-3 -> Kd 101.2 nM",
        verify="derived from Seq15 by name-encoded mutations; asserted == Table 2 printout (biotin-AAAAA stripped)",
        ranking_eligible=True))
    entries.append(_entry(
        "ang2_seq15_15_38", "Ang2 aptamer Seq15 mutant (C15U, C38G; Shakeran SPR)",
        "Angiopoietin-2", ANG2_PROTEIN, SEQ15_15_38, 118.0, "binder", SHAKERAN_REF, alphabet="rna",
        kd_method=f"{spr}: ka 8.22e3, kd 0.97e-3 -> Kd 118.0 nM",
        verify="derived from Seq15 by name-encoded mutations; asserted == Table 2 printout (biotin-AAAAA stripped)",
        ranking_eligible=True))
    entries.append(_entry(
        "ang2_seq15", "Ang2 aptamer Seq15 (parent of the Shakeran mutants; literature-validated binder)",
        "Angiopoietin-2", ANG2_PROTEIN, ANG2_SEQ15, None, "binder_no_kd", SHAKERAN_REF, alphabet="rna",
        kd_method="no individual Kd printed (mutant panel only); Tie2 phosphorylation inhibition (text)",
        verify="Shakeran Table 1 printout"))
    entries.append(_entry(
        "ang2_aba1", "ABA1 anti-Ang2 DNA aptamer (Cho array)",
        "Angiopoietin-2", ANG2_PROTEIN, ANG2_ABA1, 20.5, "binder", CHO_REF,
        kd_method="microarray equilibrium binding, Kd = 20.5 ± 7.3 nM (Cho SI Fig S1 text)",
        verify="Cho SI Table S2 printout", ranking_eligible=False))
    for eid, seq in [("ang2_aba65", ANG2_ABA65), ("ang2_aba92", ANG2_ABA92), ("ang2_aba109", ANG2_ABA109)]:
        entries.append(_entry(
            eid, f"{eid.split('_')[1].upper()} anti-Ang2 DNA aptamer (pair screen)",
            "Angiopoietin-2", ANG2_PROTEIN, seq, None, "binder_no_kd", CHO_REF,
            kd_method="Kd range 37.6-57 nM printed (main text); individual values figure-only",
            verify="Cho SI Table S2 printout"))
    entries.append(_entry(
        "ang2_seq16_ang1", "Seq16 (Ang1-specific T40.14 truncate) — no specificity for Ang2",
        "Angiopoietin-2", ANG2_PROTEIN, ANG2_SEQ16, 3006.0, "negative", SHAKERAN_REF, alphabet="rna",
        kd_method=f"{spr}: ka 1.66e3, kd 4.99e-3 -> Kd ~3 uM; text 'Kd > 1 uM'",
        verify="Shakeran Table 1 printout"))
    entries.append(_entry(
        "ang2_sc_cho", "SC scrambled aptamer — negligible Ang2 binding (Cho)",
        "Angiopoietin-2", ANG2_PROTEIN, ANG2_SC, None, "negative", CHO_REF,
        kd_method="bead fluorescence assay: 'negligible Ang2 binding' (Cho SI Fig S5 text)",
        verify="Cho SI Table S1 printout"))
    entries.append(_entry(
        "random40_ang2", "random 40-mer (fixed seed 21)", "Angiopoietin-2", ANG2_PROTEIN,
        _random_seq(21, 40), None, "negative", "generated in silico (seed 21)"))

    # ── SARS-CoV-2 nucleocapsid ──
    for eid, trunc, parent, kd, orient in N_TRUNC:
        ninta = "Ni-NTA" in orient
        entries.append(_entry(
            eid, f"{eid.split('_')[1].upper()} anti-N truncate (parent {parent})",
            "SARS-CoV-2 N", SARS2N_PROTEIN, trunc, kd, "binder", POOLSUP_REF,
            kd_method=f"BLI Kd {kd} nM, {orient} (Poolsup 2023 Table 1 / SI Table S2)",
            verify=f"substring of Table S1 {parent} row (asserted); paper-internal naming offset registered",
            ranking_eligible=ninta))
    for nsp, kd in N_FULL_KD.items():
        entries.append(_entry(
            f"n_{nsp.lower()}_full", f"{nsp} full-length anti-N aptamer (80-mer incl. primer arms)",
            "SARS-CoV-2 N", SARS2N_PROTEIN, NSP_FULL[nsp], kd, "binder", POOLSUP_REF,
            kd_method=f"BLI Kd {kd} nM (Poolsup 2023 main text; orientation as printed)",
            verify="SI Table S1 printout", ranking_eligible=False))
    for eid, seq, kd in [("n_a48", N_A48, 6.46), ("n_a58", N_A58, 3.02)]:
        entries.append(_entry(
            eid, f"{eid.split('_')[1].upper()} anti-N aptamer (re-measured, Poolsup SI Table S2)",
            "SARS-CoV-2 N", SARS2N_PROTEIN, seq, kd, "binder", POOLSUP_REF,
            kd_method=f"BLI Kd {kd} nM, Ni-NTA orientation (Poolsup 2023 SI Table S2; originally Zhang et al., ref 30)",
            verify="SI Table S2 printout", ranking_eligible=True))
    for eid, seed, ln in [("random49_sars2n", 22, 49), ("random58_sars2n", 23, 58), ("random80_sars2n", 24, 80)]:
        entries.append(_entry(
            eid, f"random {ln}-mer (fixed seed {seed})", "SARS-CoV-2 N", SARS2N_PROTEIN,
            _random_seq(seed, ln), None, "negative", f"generated in silico (seed {seed})"))

    # ── Docking anchors: pilot 3 + 1HVU (HIV-1 RT) + 8EPK (FIXa), docking-only targets ──
    docking_anchors = [dict(a, target="Thrombin") for a in pilot["docking_anchors"]]
    docking_anchors.append({
        "aptamer_entry": "t1p1_hiv1rt", "target": "HIV-1 RT", "pdb_id": "1HVU",
        "aptamer_chain": "C", "protein_chains": ["A", "B"], "method": "X-ray 4.75 A",
        "reference": "Jaeger, Restle, Steitz. EMBO J 1998, 17:4535 (PMC1170784)",
        "notes": "LOW RESOLUTION (4.75 A) — registered caveat. 1HVU chain C SEQRES (30-mer) == "
                 "Kensch 2000 printed T1.1 33-mer minus 5'-GGG (asserted in curation). "
                 "First asymmetric-unit complex (chains A=p66, B=p51, C=RNA).",
    })
    docking_anchors.append({
        "aptamer_entry": "dtri177_fixa", "target": "Factor IXa", "pdb_id": "8EPK",
        "aptamer_chain": "E", "protein_chains": ["A", "B"], "method": "X-ray 2.65 A",
        "reference": "Kolyadko et al. PNAS 2024, 121:e2401136121 (PMC11260126)",
        "notes": "DTRI-177 == RB006/pegnivacogin RNA chain; SEQRES == WHO INN pegnivacogin "
                 "(literature-verified). 2'-OMe/2'-F residues converted to standard RNA via "
                 "NUC_MAP (A2M/ATD/CFZ/OMC/OMG/OMU/UFT; CM'/CM2 atoms dropped). C11/C12/U16 "
                 "missing from density (Kolyadko Fig 3A) — scored as-is. Docking-only target: "
                 "a single FIXa aptamer family exists (Part A N/A).",
    })
    docking_na = dict(pilot["docking_not_available"])
    docking_na.update({
        "IL-17A": "no experimental aptamer-IL-17A complex in RCSB (verified 2026-08-04); docking N/A",
        "Angiopoietin-2": "no experimental aptamer-Ang2 complex in RCSB (verified 2026-08-04); docking N/A",
        "SARS-CoV-2 N": "no experimental aptamer-N complex in RCSB (verified 2026-08-04); docking N/A",
    })

    out = {
        "description": "E1 oracle capability-profiling anchor set v2 (extension, 6 Part-A targets "
                       "+ 5 docking anchors). Pilot entries carried over verbatim; new targets "
                       "IL-17A / Angiopoietin-2 / SARS-CoV-2 N. Adds ranking_eligible flags, "
                       "docking anchor target fields, and registered rejected candidates.",
        "curated": "2026-08-04",
        "convention": pilot["convention"],
        "preregistration": "run_e1_capability_profiling.py docstring, E1 EXTENSION PRE-REGISTRATION (2026-08-04)",
        "extends": "e1_anchor_set.json (pilot, carried over verbatim)",
        "rejected_candidates": {
            "SARS-CoV-2 spike RBD": "only 2 single-sequence kd-binders (PB6, PB6a); di/trimer are "
                                    "multivalent scaffold constructs (avidity confound)",
            "HIV-1 RT (Part A)": "only 1 sequence-verified binder (T1.1 via 1HVU SEQRES + Kensch 2000); "
                                 "12.01/12.01-S/M302/RT1t49 sequences figure-only. Docking-only (1HVU)",
            "Factor IXa (Part A)": "single aptamer family (9.3 lineage); 9.3/9.3t sequences figure-only. "
                                   "Docking-only (8EPK)",
            "Tenascin-C": "Hicke 2001 clone sequences + Kd all figure-only (Fig 5/10)",
            "EGFR": "E03/E04/E07 individual Kd figure-only (text range 2-3 nM); only CL4sc literature negative",
            "Ang2 Seq2_12_35": "Table 2 printout layout cannot be reconciled with Seq2 at constant length",
            "Ang2 11-1 (full)": "variable region identical to the 11-1.41 truncate (Seq1) — not double-counted",
        },
        "n_entries": len(entries),
        "docking_anchors": docking_anchors,
        "docking_not_available": docking_na,
        "known_limitations": pilot["known_limitations"] + [
            "IL-17A: Apt21-2 Kd (48.5 pM SPR) is a transcribed citation (Nakamura 2012 review of "
            "paywalled Ishiguro 2011) and is excluded from ranking; the FP subset (n=6) is the "
            "ranking-eligible set. AptAF42/dope1 sequences are template-DERIVED (lengths asserted "
            "== text: 69/68 nt; the doped region prints as 31 nt vs '30' text). Parvez immobilization likely presented monomeric IL-17 "
            "(main-text caveat); target protein = UniProt Q16552 mature chain 24-155.",
            "Ang2: same-assay SPR ranking subset spans only 101-139 nM (0.14 order) — ranking "
            "decorative, screening is the contribution. Cross-assay Kd spread is large (White "
            "filter 2.2-3.1 nM vs Cho array 20.5 nM vs Shakeran SPR ~100-200 nM) — itself an "
            "illustration of assay-dependence. Seq1 printed as 40 nt vs '41-nt' text registered.",
            "SARS-CoV-2 N: negatives are ALL in silico (the Sc80 scrambled control sequence is "
            "not printed anywhere). Ranking-eligible subset = the 6 Ni-NTA-orientation BLI "
            "binders (span 3.02-22.2 nM, 0.87 order); streptavidin-orientation and full-length "
            "Kd are excluded from ranking (orientation uncertain). tNSP9/tNSP10 parent rows "
            "differ from their names (NSP7/NSP9) — paper-internal offset registered.",
            "Docking anchors: 1HVU is 4.75 A (low resolution, registered); 8EPK is docking-only "
            "for FIXa (single aptamer family). Docking pass criterion applied over all 5 anchors "
            "with per-target breakdown (pre-registered).",
        ],
        "entries": entries,
    }

    # ── Per-target pre-registered coverage check ──
    for target in ["Thrombin", "VEGF", "PDGF-BB", "IL-17A", "Angiopoietin-2", "SARS-CoV-2 N"]:
        te = [e for e in entries if e["target"] == target]
        n_kd = len([e for e in te if e["role"] == "binder" and e.get("kd_nm") is not None])
        n_neg = len([e for e in te if e["role"] == "negative"])
        assert n_kd >= 4, f"{target}: {n_kd} kd-binders < 4"
        assert n_neg >= 3, f"{target}: {n_neg} negatives < 3"
        print(f"{target}: {n_kd} kd-binders, {n_neg} negatives, {len(te)} total")

    # guard against the known WRONG 'RB006' sequence (PSMA A9 crosstalk, lit-verification 2026-08-04)
    for e in entries:
        assert "GGGAGGACGAUGCGGACCGAAAAGGUUCCUCCC" not in e["sequence"], "wrong RB006 sequence crept in"

    _write_protein_fastas()
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} ({len(entries)} entries, {len(docking_anchors)} docking anchors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
