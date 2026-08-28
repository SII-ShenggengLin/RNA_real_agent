#!/usr/bin/env python3
"""Curate ``e1_anchor_set_v3.json`` — the docking-power extension of the E1 v2
aptamer anchor set (Part A carried verbatim; 14 new docking anchors).

CURATION PRE-REGISTRATION (2026-08-27, user-approved scope)
-----------------------------------------------------------
* Scope: extend the anchor set's ``docking_anchors`` (the Fig. 3d instrument)
  with every experimentally determined aptamer-protein complex that passes the
  registered admission discipline.  Part A (66 sequence entries, 6 targets) is
  carried over VERBATIM from v2 — this generator asserts byte-equality of the
  entries list against ``e1_anchor_set_v2.json``.  The five Part-A targets
  cleared by the 2026-08-27 literature survey (FGF2, influenza H3N2 HA,
  HIV-1 RT FANA table, SARS-CoV-2 RBD, IFN-gamma) are NOT added here; they
  enter the same v3 set in a second curation pass AFTER the Fig. 3d run
  (user-sequenced), so the docking panel measured below is independent of them.
* Survey backbone: Troisi et al. 2023 Int J Mol Sci 24:16318 (144 protein-
  aptamer PDB entries; PMC10671752) cross-checked entry-by-entry against the
  RCSB Data API, PLUS a full-text RCSB sweep of every post-2024 deposition
  whose title contains "aptamer" (53 hits screened 2026-08-27).  All facts
  (method, resolution, chain composition, aptamer chemistry, modified-residue
  identities) verified against RCSB; primary citations pulled from the
  entries' rcsb_primary_citation.
* Admission discipline (registered):
  (a) full-protein target (peptide targets excluded: Rev/Rex/P16);
  (b) the aptamer was selected against that protein (fluorogenic-Fab
      chaperone systems, riboswitch/RBP natural-recognition complexes
      excluded);
  (c) nucleotide chemistry mappable to standard RNA under the set's
      conventions — DNA via T->U (set convention), sugar modifications
      (2'-OMe / 2'-F / FANA) via NUC_MAP following the 8EPK precedent;
  (d) mirror-image (L-chemistry spiegelmer) complexes REJECTED — chirality-
      level out-of-distribution for D-RNA oracles (4WB2/4WB3 C5a NOX-D20,
      4R8I CCL2);
  (e) non-natural protein-binding bases REJECTED per the registered PDGF-BB
      SOMAmer precedent (4HQU/4HQX): SOMAmer-class hydrophobic base
      modifications verified by RCSB chemcomp identity — 4NI7/4NI9 (IL-6
      SL1025), 7JTN/7JTQ (factor B), 5UC6 (IL-1alpha naphthyl-modified),
      4ZBN (NGF triplex, DUZ = 5-benzylcarbamoyl-dU), 8J1Q (SARS-CoV-2 RBD
      bivalent, 85Y = 5-naphthylmethylcarbamoyl-dU), 7YQ3 (insulin receptor
      A43, 85Y), 9SA8 (insulin receptor HIR-6, A1J boronate x9/19),
      6TXR (PvLDH cubane-modified);
  (f) within-protein redundancy: additional complexes of an already-anchored
      protein are admitted only as genuinely new aptamer families (hence
      M08s-1 for thrombin, C8N5t/pL1 for LDH species, BT-100 + ARC1172 for
      vWF); rejected as same-family variants or drug-bound ternaries:
      HIV-1 RT 38-mer-hairpin family re-depositions (5D3G/5HLF/5HRO/5I3U/
      5I42/6VUG/7OZW/7P15/7Z24-series), thrombin TBA-family variants
      (6Z8V/4LZ4/6EO6/9U3I), bivalent two-aptamer ternaries (5EW1/5EW2/
      7NTU), same-complex alternate depositions (3HXQ, 5VOF, 5HTO, 7YQ4,
      8J26);
  (g) weak-relevance model systems (IgG 3AGV, TetR 6SY4/6SY6, lysozyme
      4M4O, DUX4 6U81, DasR 9I0V) rejected for target-domain focus.
* The 14 admitted anchors (5 retained + 14 new = 19 docking anchors, 14
  independent protein targets):
    8ZBF  SARS-CoV-2 N-NTD  x DNA A58-T10 lineage   2.80 A X-ray  (Chen et al., to be published)
    3HXO  vWF A1            x DNA ARC1172           2.40 A X-ray  Huang 2009 Structure doi:10.1016/j.str.2009.09.011
    7F49  vWF A1            x RNA BT-100 (2'-OMe)   2.09 A X-ray  Zhu 2020 JTH doi:10.1111/jth.14755
    5VOE  Factor Xa         x RNA 11F7t (2'-F/FANA) 2.00 A X-ray  Gunaratne 2018 NBT doi:10.1038/nbt.4153
    5HRT  autotaxin (mouse) x DNA/2'-OMe mixed      2.00 A X-ray  Kato 2016 NSMB doi:10.1038/nsmb.3200
    6RTI  PSMA/GCPII (hu)   x RNA A9g               2.20 A X-ray  Ptacek 2020 NAR doi:10.1093/nar/gkaa494
    1OOA  NF-kB p50 (2)     x RNA aptamer (2 copies)2.45 A X-ray  Huang 2003 PNAS doi:10.1073/pnas.1632011100
    3ZH2  P. falciparum LDH x DNA aptamer           2.10 A X-ray  Cheung 2013 PNAS doi:10.1073/PNAS.1309538110
    5HRU  P. vivax LDH      x DNA pL1               1.71 A X-ray  Choi 2016 SciRep doi:10.1038/srep34998
    9RTD  P. falciparum LDH x DNA C8N5t             2.10 A X-ray  Kunrade 2026 MTNA doi:10.1016/j.omtn.2026.102977
    8BW5  Thrombin          x DNA M08s-1            2.80 A X-ray  Troisi 2023 NAR doi:10.1093/nar/gkad634
    3UZT  GRK2              x RNA C13.18 (7-nt core)3.51 A X-ray  Tesmer 2012 Structure doi:10.1016/j.str.2012.05.002
    7ZQS  TfR1 (hu)         x DNA aptamer           2.54 A cryoEM Cheng 2022 JACS doi:10.1021/jacs.2c05349
    9T74  SARS-CoV-2 RBD    x 2'-F RNA (FY)         3.46 A cryoEM (Kristoffersen et al., to be published)
* NUC_MAP (verified against RCSB chemcomp; parent-base mapping, modification
  atoms dropped at pose construction — the 8EPK precedent):
    A2M 2'-OMe-A -> A | OMC 2'-OMe-C -> C | OMG 2'-OMe-G -> G | OMU 2'-OMe-U -> U
    CFZ 2'-F-C   -> C | UFT 2'-F-U   -> U | CFL 2'-F-arabino-C -> C (FANA)
    ATD thymidine-3'-P -> U | DT -> U | DA -> A | DC -> C | DG -> G
  (DNA->RNA residue renaming follows the set convention "DNA aptamers scored
  as RNA via T->U"; the deoxyribose-sugar caveat is registered below.)
* Pose-chain assignments (verified by parsing each file with gemmi; asserted
  at generation time): one protomer/aptamer copy per crystallographic
  multiply-deposited complex (8ZBF A+E, 3ZH2 A+E, 5HRU A+C, 9RTD A+G, 7ZQS
  B+A); the full asymmetric unit where the assembly is intrinsically
  multi-chain (1OOA A+B+C+D); serine-protease light+heavy chains kept
  (5VOE H+L+A, 8BW5 H+L+F).
* Registered caveats (also in ``known_limitations``):
  - 8ZBF / 9T74: primary citation "to be published" — provenance is the RCSB
    deposition; re-verify when the paper appears.
  - 5VOE: desGla (gamma-carboxylation removed) + S195A catalytic-site mutant
    construct; 11F7t carries FANA arabino chemistry (CFL) mapped to C.
  - 5HRT: mouse autotaxin (species caveat); aptamer is a DNA/2'-OMe chimera.
  - 3UZT: only a 7-nt core of C13.18 is modeled — minimal interface.
  - 9T74: 2'-F-modified RNA (CFZ/UFT), cryoEM 3.46 A.
  - 1OOA: two identical aptamer copies in the AU, perturbed as one rigid body.
  - DNA aptamers: residues renamed to RNA letters without adding O2' atoms
    (atom-level deoxyribose remains) — the registered convention for the
    sequence-level T->U rule at structure level.
* Determinism: no network at generation time beyond the (cached) RCSB
  metadata fetches under ``experiments/lit_cache/docking_v3/``; re-running
  reproduces the JSON byte-for-byte.

PART-A EXTENSION PRE-REGISTRATION (second curation pass, 2026-08-28,
user-sequenced after the Fig. 3d run; survey 2026-08-27 + table-level
verification 2026-08-28)
---------------------------------------------------------------------------
* Survey verdicts vs curation outcomes (the assertion gate is the arbiter):
  - **FGF2 — ADMITTED** (10 binders).  Sequences+Kd from Jellinek et al.
    1993 PNAS 90:11227 (PMC47955); the primary PDF is bot-walled from this
    environment, so sequences/Kd are taken from the Ribocentre-aptamer
    database transcription (aptamer.ribocentre.org/_posts/bFGF-aptamer,
    printed twice on that page — table + Structure section, 7A/26A
    cross-checked identical) and verified by family-motif nesting assertions
    (family A: all contain CGACA; family B: all start CUGUCGAGCAUGCU;
    22B/28B share the 26-nt prefix).  Biphasic binders store Kd1 (registered:
    two-site fit; ranking uses Kd1).  Deviation registered in
    known_limitations.
  - **Influenza H3N2 HA (swine) — ADMITTED** (4 binders + 1 literature
    negative).  Wongphatcharachai et al. 2013 J Clin Microbiol 51:46
    (PMC3536225): Kd in abstract + Results text (dot blot, one assay);
    sequences Table 4 (40-mers); HA1c = the paper's printed non-binder
    ("did not bind to any proteins").  Protein: the selection strain
    A/swine/Minnesota/SG-00235/2007 is GISAID-restricted — surrogate =
    full-length contemporaneous midwest swine H3N2 HA0
    A/swine/Illinois/03040/2010 (GenBank CY…, id 303305451; 95.1% aa
    identity to the MN/2008 partial; mature slice 17-549, signal peptide
    removed, C-terminal 17 aa absent from the record — all registered).
  - **IFN-gamma — ADMITTED** (6 binders + 1 printed negative).  Zhao et al.
    2022 Molecules 27:5725 (PMC9457990): Kd in Results §2.2 text (Octet
    BLI, one assay); B1-4 sequence in Methods; M-series mutant sequences in
    SI Table S1 (zip mirrored at pub.mdpi-res.com, cached under
    lit_cache/part_a_v3/zhao_si/); M-mutants DERIVED programmatically from
    B1-4 by the registered point-mutation lists and asserted equal to the
    SI prints; M5-5 cross-checked between SI Tables S1 and S5 (identical).
    The printed positive-delta-G docking-negative mutant (Methods) enters as
    a negative with its computational-evidence caveat registered.  Cao 2014
    measured B1-4 at 74.5 nM vs Zhao's 913.9 nM — cross-paper divergence
    registered in kd_method; the ranking subset uses only Zhao's
    same-assay values.
  - **SARS-CoV-2 RBD — REJECTED at curation** (survey verdict overturned):
    Shekar et al. 2025 Biomolecules 15:805 Table 3 prints the five BLI KD
    values, but the sequences sit in an 83-sequence supplementary zip
    WITHOUT any printed mapping to the aptamer IDs (Table S1 enumerates
    per-variant subsets with restarting S.No; two orderings are internally
    consistent) — sequence identity is not assertion-verifiable.
  - **HIV-1 RT FANA — REJECTED at curation** (survey verdict overturned):
    Ferreira-Bravo et al. 2015 NAR 43:9587 Table 1 prints >=9 family Kd
    values, but the sequences are figure-only (Fig 3A / SI Fig S1 images);
    the PDF and SI are bot-walled from this environment and a vision
    extraction of the figure misread the two primer-flank regions against
    the paper's own text-printed template/primer sequences — the central
    variable region therefore lacks an independent verification anchor.
  - Streptavidin stays unadmitted (paywalled table, unverified).
* Admission bar held: per new target >=4 table/text-printed Kd binders
  (all same-assay per paper) + >=3 negatives (literature where they exist:
  HA1c, the printed IFN-gamma negative mutant; fixed-seed in-silico randoms
  otherwise, seeds registered in the entry reference — the SARS-CoV-2 N
  convention).  Protein fastas generator-sliced + asserted.  DNA aptamers
  scored as RNA via T->U (set convention; FGF2 entries are RNA as printed).
* Assembly guarantees: Part-A v2 entries carried verbatim (asserted);
  docking anchors byte-identical to the first-pass v3 (asserted against
  the on-disk file before overwrite); n_entries == 66 + 29 == 95; 9 targets.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/curate_e1_anchor_set_v3.py
"""

from __future__ import annotations

import copy
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ANCHOR_DIR = os.path.join(
    HERE, "..", "data", "benchmarks", "external_anchors", "aptamers"
)
V2_PATH = os.path.join(ANCHOR_DIR, "e1_anchor_set_v2.json")
V3_PATH = os.path.join(ANCHOR_DIR, "e1_anchor_set_v3.json")
STRUCT_DIR = os.path.join(ANCHOR_DIR, "structures")
CACHE_DIR = os.path.join(HERE, "lit_cache", "docking_v3")

# residue-name -> canonical RNA base letter (parent scaffold kept, mod atoms dropped)
NUC_MAP = {
    "A2M": "A", "OMC": "C", "OMG": "G", "OMU": "U",
    "CFZ": "C", "UFT": "U", "CFL": "C",
    "ATD": "U", "DT": "U", "DA": "A", "DC": "C", "DG": "G",
}
STD_RNA = {"A", "U", "G", "C"}
STD_DNA = {"DA", "DT", "DG", "DC"}
# small-molecule / ion entries that may appear inside NA chain records and are
# stripped at pose construction (not nucleotides)
NON_NUCLEOTIDE_OK = {
    "MG", "CA", "NA", "K", "GOL", "EPE", "SO4", "ZN", "MN", "HOH",
    "MPD", "EDO", "ACT", "PEG", "DMS", "IPA", "NO3", "PO4", "CL", "BR", "FMT",
    "MES", "TRS", "BME", "CO3", "OXY", "NAG", "BMA", "FLC", "ATP",
}

# the 14 new anchors.  chains: (protein_chains, aptamer_chains) — asserted
# against the parsed files.  mods: expected modified residue names (subset of
# NUC_MAP) on the aptamer chains.
NEW_ANCHORS = [
    dict(
        aptamer_entry="a58t10_sars2n", target="SARS-CoV-2 N", pdb_id="8ZBF",
        chains=(["A"], ["E"]), mods=set(),
        method="X-ray 2.80 A",
        reference="Chen et al., RCSB 8ZBF (to be published, deposited 2024)",
        notes=(
            "DNA aptamer (A58-T10 lineage) vs N-NTD construct; asymmetric unit "
            "holds four protomers (A-D) each with one aptamer copy (E-H) — "
            "pose = first pair A+E. No modified residues. Primary citation "
            "pending (registered caveat)."
        ),
    ),
    dict(
        aptamer_entry="arc1172_vwf", target="Von Willebrand factor", pdb_id="3HXO",
        chains=(["A"], ["B"]), mods=set(),
        method="X-ray 2.40 A",
        reference="Huang RH, Fremont DH, Diener JL, Schaub RG, Sadler JE. Structure 2009;17:1476-1484. doi:10.1016/j.str.2009.09.011",
        notes=(
            "ARC1172 (ARC1779 clinical lineage) vs vWF A1 domain; alternate "
            "deposition 3HXQ (2.69 A) rejected as same complex."
        ),
    ),
    dict(
        aptamer_entry="bt100_vwf", target="Von Willebrand factor", pdb_id="7F49",
        chains=(["A"], ["B"]),
        mods={"OMG", "OMC", "A2M", "OMU", "DT"},
        method="X-ray 2.09 A",
        reference="Zhu S, et al. J Thromb Haemost 2020;18:930-936. doi:10.1111/jth.14755",
        notes=(
            "BT-100 RNA aptamer, 2'-OMe modified (A2M/OMC/OMG/OMU + one dT "
            "overhang) — 8EPK NUC_MAP class; maps to standard RNA."
        ),
    ),
    dict(
        aptamer_entry="11f7t_fx", target="Factor Xa", pdb_id="5VOE",
        chains=(["H", "L"], ["A"]),
        mods={"UFT", "CFL"},
        method="X-ray 2.00 A",
        reference="Gunaratne R, et al. Nat Biotechnol 2018;36:647-651. doi:10.1038/nbt.4153",
        notes=(
            "RNA aptamer 11F7t vs desGla-factor Xa S195A (construct caveat "
            "registered: gamma-carboxylation removed, catalytic-site mutant); "
            "FANA chemistry (CFL arabino-2'-F-C) mapped to C; light+heavy "
            "chains H+L kept (thrombin convention). Ternary 5VOF (+rivaroxaban) "
            "rejected as same complex plus drug."
        ),
    ),
    dict(
        aptamer_entry="kato16_autotaxin", target="Autotaxin", pdb_id="5HRT",
        chains=(["A"], ["B"]),
        mods={"OMC", "OMG", "A2M"},
        method="X-ray 2.00 A",
        reference="Kato K, et al. Nat Struct Mol Biol 2016;23:393-398. doi:10.1038/nsmb.3200",
        notes=(
            "Inhibitory DNA/2'-OMe chimeric aptamer vs MOUSE autotaxin "
            "(species caveat registered); 750-residue protein — largest anchor."
        ),
    ),
    dict(
        aptamer_entry="a9g_psma", target="PSMA", pdb_id="6RTI",
        chains=(["A"], ["X"]),
        mods={"CFZ", "UFT"},
        method="X-ray 2.20 A",
        reference="Ptacek J, et al. Nucleic Acids Res 2020;48:6735-6747. doi:10.1093/nar/gkaa494",
        notes=(
            "RNA aptamer A9g vs human GCPII/PSMA; the generation-time "
            "assertion screen found the aptamer chain is 2'-F modified "
            "(CFZ/UFT — the 8EPK NUC_MAP class; survey-level scan had missed "
            "it, corrected at curation). The known-wrong 'RB006'-vs-A9 "
            "sequence crosstalk hazard is sequence-level (Part A) and does "
            "not affect the structural anchor; guard retained for the Part-A "
            "pass."
        ),
    ),
    dict(
        aptamer_entry="p50apt_nfkb", target="NF-kB", pdb_id="1OOA",
        chains=(["A", "B"], ["C", "D"]), mods=set(),
        method="X-ray 2.45 A",
        reference="Huang DB, et al. Proc Natl Acad Sci USA 2003;100:9268-9273. doi:10.1073/pnas.1632011100",
        notes=(
            "High-affinity RNA aptamer vs p50 homodimer; the AU holds two "
            "identical 29-nt aptamer copies (C, D) — both included and "
            "perturbed as ONE rigid body in docking decoys."
        ),
    ),
    dict(
        aptamer_entry="cheung13_pfldh", target="P. falciparum LDH", pdb_id="3ZH2",
        chains=(["A"], ["E"]), mods=set(),
        method="X-ray 2.10 A",
        reference="Cheung YW, et al. Proc Natl Acad Sci USA 2013;110:15967-15972. doi:10.1073/PNAS.1309538110",
        notes=(
            "DNA aptamer vs PfLDH; AU holds four LDH protomers (A-D) and two "
            "aptamer copies (E, G) — pose = first pair A+E."
        ),
    ),
    dict(
        aptamer_entry="pl1_pvldh", target="P. vivax LDH", pdb_id="5HRU",
        chains=(["A"], ["C"]), mods=set(),
        method="X-ray 1.71 A",
        reference="Choi SJ, et al. Sci Rep 2016;6:34998. doi:10.1038/srep34998",
        notes=(
            "DNA aptamer pL1 vs PvLDH (highest-resolution anchor in the set); "
            "tetrameric-deposition variant 5HTO rejected as same complex."
        ),
    ),
    dict(
        aptamer_entry="c8n5t_pfldh", target="P. falciparum LDH", pdb_id="9RTD",
        chains=(["A"], ["G"]), mods=set(),
        method="X-ray 2.10 A",
        reference="Kunrade S, et al. Mol Ther Nucleic Acids 2026. doi:10.1016/j.omtn.2026.102977",
        notes=(
            "DNA aptamer C8N5t vs PfLDH — second independent aptamer family "
            "on this target."
        ),
    ),
    dict(
        aptamer_entry="m08s1_thrombin", target="Thrombin", pdb_id="8BW5",
        chains=(["H", "L"], ["F"]), mods=set(),
        method="X-ray 2.80 A",
        reference="Troisi M, et al. Nucleic Acids Res 2023;51:11050-11061. doi:10.1093/nar/gkad634",
        notes=(
            "Duplex/quadruplex DNA aptamer M08s-1_41mer — fourth independent "
            "thrombin aptamer family (TBA / HD22 / Toggle-25t / M08s-1)."
        ),
    ),
    dict(
        aptamer_entry="c1318_grk2", target="GRK2", pdb_id="3UZT",
        chains=(["A"], ["B"]), mods=set(),
        method="X-ray 3.51 A",
        reference="Tesmer JJG, et al. Structure 2012;20:1324-1334. doi:10.1016/j.str.2012.05.002",
        notes=(
            "RNA aptamer C13.18 vs GRK2; only a 7-nt core is modeled "
            "(registered: minimal interface). Ternary 3UZS (+Gbeta1gamma2, "
            "4.52 A) rejected as assembly-confounded."
        ),
    ),
    dict(
        aptamer_entry="cheng22_tfr1", target="Transferrin receptor 1", pdb_id="7ZQS",
        chains=(["B"], ["A"]), mods=set(),
        method="cryoEM 2.54 A",
        reference="Cheng L, et al. J Am Chem Soc 2022;144:15181-15190. doi:10.1021/jacs.2c05349",
        notes=(
            "DNA aptamer vs human TfR1 ectodomain; AU holds two copies "
            "(A+B, C+D) — pose = first pair B+A. First cryoEM anchor in the "
            "set (registered)."
        ),
    ),
    dict(
        aptamer_entry="fyapt_sars2rbd", target="SARS-CoV-2 RBD", pdb_id="9T74",
        chains=(["B"], ["A"]),
        mods={"CFZ", "UFT"},
        method="cryoEM 3.46 A",
        reference="Kristoffersen et al., RCSB 9T74 (to be published, deposited 2024)",
        notes=(
            "2'-F-pyrimidine (FY) RNA aptamer vs SARS-CoV-2 RBD — 8EPK "
            "NUC_MAP class (CFZ->C, UFT->U). RBD was Part-A-rejected (no Kd "
            "table then) but docking anchors need no affinity table. Primary "
            "citation pending (registered caveat)."
        ),
    ),
]


def cache_json(pdb_id: str) -> dict:
    """Fetch (once) and cache the RCSB entry metadata for the audit trail."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{pdb_id.lower()}_entry.json")
    if not os.path.exists(path):
        req = urllib.request.Request(
            f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}",
            headers={"User-Agent": "curl/8"},
        )
        data = urllib.request.urlopen(req, timeout=60).read()
        with open(path, "wb") as fh:
            fh.write(data)
        time.sleep(0.2)
    with open(path, "rb") as fh:
        return json.loads(fh.read())


def verify_structure(anchor: dict) -> dict:
    """Parse the anchor's PDB and assert the registered chain chemistry."""
    import gemmi

    pdb_id = anchor["pdb_id"]
    path = os.path.join(STRUCT_DIR, f"{pdb_id.lower()}.pdb")
    assert os.path.exists(path), f"missing structure file {path}"
    st = gemmi.read_structure(path)
    assert len(st) == 1, f"{pdb_id}: expected single model, got {len(st)}"
    model = st[0]
    prot_chains, apt_chains = anchor["chains"]

    chain_res = {}
    for ch in model:
        chain_res[ch.name] = [r.name for r in ch if r.name != "HOH"]
    for ch_name in prot_chains + apt_chains:
        assert ch_name in chain_res, f"{pdb_id}: registered chain {ch_name} absent"

    # protein chains: majority amino-acid three-letter codes
    from gemmi import find_tabulated_residue
    for ch_name in prot_chains:
        rns = chain_res[ch_name]
        assert rns, f"{pdb_id}: protein chain {ch_name} empty"
        n_prot = sum(
            1 for r in rns
            if find_tabulated_residue(r) is not None
            and find_tabulated_residue(r).is_amino_acid()
        )
        assert n_prot >= 0.8 * len(rns), (
            f"{pdb_id}: chain {ch_name} not protein-majority ({n_prot}/{len(rns)})"
        )
    # aptamer chains: all nucleotides standard, NUC_MAP-able or registered ion
    observed_mods = set()
    for ch_name in apt_chains:
        rns = chain_res[ch_name]
        n_nuc = sum(
            1 for r in rns
            if r in STD_RNA or r in STD_DNA or r in NUC_MAP
        )
        assert len(rns) >= 5, f"{pdb_id}: aptamer chain {ch_name} too short ({len(rns)})"
        assert n_nuc >= 0.6 * len(rns), (
            f"{pdb_id}: chain {ch_name} not nucleotide-majority ({n_nuc}/{len(rns)}); "
            "if a new modification appears, extend NUC_MAP explicitly"
        )
        for r in rns:
            if r not in STD_RNA and r not in STD_DNA:
                if r in NUC_MAP:
                    observed_mods.add(r)
                else:
                    assert r in NON_NUCLEOTIDE_OK, (
                        f"{pdb_id}: unregistered residue {r} on aptamer chain {ch_name}"
                    )
    assert observed_mods <= set(anchor["mods"]), (
        f"{pdb_id}: observed mods {observed_mods} exceed registered {set(anchor['mods'])}"
    )
    # cross-check RCSB metadata (method + resolution) matches the registry
    meta = cache_json(pdb_id)
    methods = " ".join(e.get("method", "") for e in meta.get("exptl", []))
    res = (meta.get("rcsb_entry_info", {}).get("resolution_combined") or [None])[0]
    reg_res = float(anchor["method"].split()[1])
    reg_kind = anchor["method"].split()[0].upper()
    methods_u = methods.upper()
    kind_ok = reg_kind in methods_u or (
        reg_kind == "CRYOEM" and "ELECTRON MICROSCOPY" in methods_u
    )
    assert kind_ok, (
        f"{pdb_id}: registered method {reg_kind} not in RCSB methods {methods!r}"
    )
    assert res is not None and abs(res - reg_res) < 0.06, (
        f"{pdb_id}: RCSB resolution {res} != registered {reg_res}"
    )
    return dict(
        observed_mods=sorted(observed_mods),
        n_protein_residues=sum(len(chain_res[c]) for c in prot_chains),
        n_aptamer_residues=sum(len(chain_res[c]) for c in apt_chains),
    )


# ── Part-A extension (second curation pass, 2026-08-28) ─────────────────────

LIT_CACHE = Path(HERE) / "lit_cache" / "part_a_v3"
PROTEIN_DIR = Path(ANCHOR_DIR) / "proteins"

_FGF2_BINDERS = [
    # (id, sequence as printed, kd_nm, biphasic)
    ("gf_5a", "AUCUCCUCCCGUCGAAGCUAACCUGGCCACUUCGACAUGAGGCCCGGA", 23.0, False),
    ("gf_7a", "AACGCUCAAUCGGCGAGCUAACCAAGACACUCGCUGCACUUCGACAUG", 5.0, False),
    ("gf_13a", "ACCCGCGGCCUCCGAAGCUAACCAGGACACUUCGACAUGAGGCCCGGA", 3.2, False),
    ("gf_14a", "UAAACGCUCAAUGGGUGCUAACCAGGACACACCCACGCUGUUUCGACA", 3.0, False),
    ("gf_21a", "AAACGCUCAAUGGGUGCUUAACCAGGCCACACCCUGCUGUUUCGACAU", 8.1, False),
    ("gf_12a", "AGAAUAAACGCUCAAGGGGCAACGCUACAGACAAGUGCACCCAACUUCGACAU", 0.51, True),
    ("gf_26a", "AACGCUCAACGUCAGAAGGCAACGUAUAGGCAAGCACACUUCGACAUGAGGC", 0.19, True),
    ("gf_22b", "CUGUCGAGCAUGCUGAGGGUAACGUACUGGCAAGCUCACCUCAGCGUAGCUA", 0.13, True),
    ("gf_28b", "CUGUCGAGCAUGCUGAGGGUAACGUAUAGUCAAGACACCUCAAGUCUAGCU", 0.32, True),
    ("gf_38b", "CUGUCGAGCAUGCUUGAGGUAACGCUGAGUCAAGUGCACUCGAAGUCUAGCU", 0.68, True),
]

_HA_BINDERS = [
    # (id, Table-4 40-mer DNA, kd_nm dot blot)
    ("ha68_swh3", "ACTCCGTCATCTTTAGTGGCCCCAATGTCGTTATCACCGA", 7.1),
    ("ha7_swh3", "CACTCCGTCACTTTAGTGGATCTTTATAAAACCGATGCTG", 22.3),
    ("ha2a_swh3", "GCCACTCCGTCACTTTAGTGGTTTTTTTTATAAATGCTTC", 16.0),
    ("ha2b_swh3", "TACTCCGTCACTTTAGTGGATATAACAACCTCCCTATGGG", 3.7),
]
_HA1C_NEG = "CGATCAAGACAGAAGAGGTGATAACTCCGTCACTTTAGTG"

_IFNG_B14 = "CCGCCCAAATCCCTAAGAGAAGACTGTAATGACATCAAACCAGACACACTACACACGCA"
_IFNG_MUTANTS = {
    # (1-based position, new base) lists — derived from B1-4, asserted == SI prints
    "m1_8_ifng": [(18, "G")],
    "m2_6_ifng": [(18, "G"), (49, "T")],
    "m3_6_ifng": [(18, "T"), (27, "G"), (44, "T")],
    "m4_10_ifng": [(18, "T"), (27, "G"), (29, "T"), (44, "T")],
    "m5_5_ifng": [(14, "G"), (18, "G"), (24, "G"), (34, "G"), (49, "T")],
}
_IFNG_KD = {  # Zhao 2022 Octet BLI, nM
    "b1_4_ifng": 913.9, "m1_8_ifng": 439.5, "m2_6_ifng": 481.6,
    "m3_6_ifng": 267.1, "m4_10_ifng": 276.6, "m5_5_ifng": 105.6,
}
_IFNG_NEG_MUT = "CCGCCCAAATCCCTAAGAGAAGACTATAATGACATCAAACCAGACACACTACACACGCA"


def _mutate(parent: str, mutations: list) -> str:
    out = list(parent)
    for pos, new in mutations:  # pos is 1-based
        out[pos - 1] = new
    return "".join(out)


def _in_silico_negatives(seed, n, alphabet, count, tag, target, note):
    import random

    rng = random.Random(seed)
    entries = []
    for i in range(count):
        seq = "".join(rng.choice(alphabet) for _ in range(n))
        entries.append({
            "id": f"{tag}_{chr(ord('a') + i)}",
            "name": f"in-silico negative {i + 1} ({note})",
            "target": target,
            "protein": None,  # filled by caller
            "sequence": seq,
            "alphabet": "rna" if "U" in alphabet else "dna",
            "length_nt": len(seq),
            "kd_nm": None,
            "role": "negative",
            "reference": f"in silico negative, fixed-seed RNG seed {seed} "
                         "(this generator, ANCHORS.md §3.6)",
            "kd_method": None,
            "sequence_verification": "generated (fixed-seed deterministic random)",
            "ranking_eligible": False,
        })
    return entries


def _read_fasta_cached(name):
    text = (LIT_CACHE / name).read_text()
    lines = text.splitlines()
    seq = "".join(l.strip() for l in lines[1:] if not l.startswith(">"))
    return lines[0], seq


def _protein_field(fasta_name, label, lo, hi, full_seq):
    mature = full_seq[lo - 1:hi]
    assert len(mature) == hi - lo + 1, f"{label}: slice length mismatch"
    return {
        "type": "uniprot_fasta",
        "uniprot": label,
        "range": f"{lo}-{hi}",
        "fasta": f"proteins/{fasta_name}",  # relative to the anchor dir (v2 convention)
    }, mature


def _translate_cached(fasta_name):
    codon_tab = {
        'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L', 'CTT': 'L', 'CTC': 'L',
        'CTA': 'L', 'CTG': 'L', 'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
        'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V', 'TCT': 'S', 'TCC': 'S',
        'TCA': 'S', 'TCG': 'S', 'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
        'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T', 'GCT': 'A', 'GCC': 'A',
        'GCA': 'A', 'GCG': 'A', 'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
        'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q', 'AAT': 'N', 'AAC': 'N',
        'AAA': 'K', 'AAG': 'K', 'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
        'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W', 'CGT': 'R', 'CGC': 'R',
        'CGA': 'R', 'CGG': 'R', 'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
        'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
    }
    seq = _read_fasta_cached(fasta_name)[1]
    prot = "".join(codon_tab.get(seq[i:i + 3], "X")
                   for i in range(0, len(seq) - 2, 3))
    stop = prot.find("*")
    return prot if stop == -1 else prot[:stop]


def build_part_a(v2):
    import textwrap

    entries = []

    # ---- FGF2 ---------------------------------------------------------------
    fgf2_full = _read_fasta_cached("P09038.fasta")[1]
    assert len(fgf2_full) == 288, "FGF2 canonical should be 288 aa"
    fgf2_prot, fgf2_mature = _protein_field("fgf2.fa", "P09038", 134, 288, fgf2_full)
    assert len(fgf2_mature) == 155  # the classic 18-kDa form
    family_a = [s for i, s, k, b in _FGF2_BINDERS if i.endswith("a")]
    family_b = [s for i, s, k, b in _FGF2_BINDERS if i.endswith("b")]
    assert all("CGACA" in s for s in family_a), "FGF2 family-A motif assertion failed"
    assert all(s.startswith("CUGUCGAGCAUGCU") for s in family_b), \
        "FGF2 family-B prefix assertion failed"
    b22 = next(s for i, s, k, b in _FGF2_BINDERS if i == "gf_22b")
    b28 = next(s for i, s, k, b in _FGF2_BINDERS if i == "gf_28b")
    assert b22[:26] == b28[:26], "FGF2 22B/28B 26-nt prefix assertion failed"
    for aid, seq, kd, biphasic in _FGF2_BINDERS:
        entries.append({
            "id": aid, "name": f"bFGF RNA ligand {aid[3:].upper()}",
            "target": "FGF2", "protein": fgf2_prot,
            "sequence": seq, "alphabet": "rna", "length_nt": len(seq),
            "kd_nm": kd, "role": "binder",
            "reference": "Jellinek D, Lynott CK, Rifkin DB, Janjic N. PNAS 1993;90:11227-11231. doi:10.1073/pnas.90.23.11227 (Table 1 + Fig. 4; sequences/Kd via the Ribocentre-aptamer transcription, aptamer.ribocentre.org/_posts/bFGF-aptamer — primary PDF bot-walled, deviation registered)",
            "kd_method": ("nitrocellulose filter binding, two-site fit — Kd1 stored"
                          if biphasic else
                          "nitrocellulose filter binding"),
            "sequence_verification": (
                "Ribocentre transcription cross-checked against the page's own "
                "Structure-section repeats (7A/26A identical); family-motif "
                "nesting asserted (family A contains CGACA; family B starts "
                "CUGUCGAGCAUGCU; 22B/28B share the 26-nt prefix)"),
            "ranking_eligible": True,
        })
    for e in _in_silico_negatives(20260828, 50, "ACGU", 3, "gf_rand", "FGF2",
                                  "50-nt random RNA"):
        e["protein"] = fgf2_prot
        entries.append(e)

    # ---- swine influenza H3N2 HA --------------------------------------------
    ha_full = _translate_cached("swine_h3_il2010.fasta")
    assert ha_full.startswith("MKT") and len(ha_full) == 549, \
        f"IL/2010 HA0 translation unexpected: {len(ha_full)} aa"
    ha_prot, ha_mature = _protein_field(
        "swine_h3_ha.fa", "GenBank:303305451", 17, 549, ha_full)
    assert len(ha_mature) == 533
    for seq in [s for _, s, _ in _HA_BINDERS] + [_HA1C_NEG]:
        assert len(seq) == 40, "HA Table-4 sequences are 40-mers"
        assert "ACTCCGTCA" in seq and "TTTAGTG" in seq, \
            "HA family motif assertion failed"
    for aid, seq, kd in _HA_BINDERS:
        entries.append({
            "id": aid, "name": f"swH3 DNA aptamer {aid.split('_')[0].upper()}",
            "target": "Influenza H3N2 HA", "protein": ha_prot,
            "sequence": seq, "alphabet": "dna", "length_nt": len(seq),
            "kd_nm": kd, "role": "binder",
            "reference": "Wongphatcharachai M, et al. J Clin Microbiol 2013;51:46-54. doi:10.1128/JCM.01984-12 (Kd in abstract + Results text; sequence Table 4)",
            "kd_method": "nitrocellulose dot blot (recombinant swH3, one assay)",
            "sequence_verification": "Table 4 printout equality",
            "ranking_eligible": True,
        })
    entries.append({
        "id": "ha1c_swh3", "name": "HA1c — printed non-binder",
        "target": "Influenza H3N2 HA", "protein": ha_prot,
        "sequence": _HA1C_NEG, "alphabet": "dna", "length_nt": 40,
        "kd_nm": None, "role": "negative",
        "reference": "Wongphatcharachai 2013 Table 4 + dot-blot text ('one (HA1c) did not bind to any proteins')",
        "kd_method": None,
        "sequence_verification": "Table 4 printout equality; family motif present",
        "ranking_eligible": False,
    })
    for e in _in_silico_negatives(20260829, 40, "ACGT", 2, "ha_rand",
                                  "Influenza H3N2 HA", "40-nt random DNA"):
        e["protein"] = ha_prot
        entries.append(e)

    # ---- IFN-gamma -----------------------------------------------------------
    ifng_full = _read_fasta_cached("P01579.fasta")[1]
    assert len(ifng_full) == 166, "IFN-gamma canonical should be 166 aa"
    ifng_prot, ifng_mature = _protein_field("ifng.fa", "P01579", 24, 166, ifng_full)
    assert len(ifng_mature) == 143
    mut_prints = {
        "m1_8_ifng": "CCGCCCAAATCCCTAAGGGAAGACTGTAATGACATCAAACCAGACACACTACACACGCA",
        "m2_6_ifng": "CCGCCCAAATCCCTAAGGGAAGACTGTAATGACATCAAACCAGACACATTACACACGCA",
        "m3_6_ifng": "CCGCCCAAATCCCTAAGTGAAGACTGGAATGACATCAAACCAGTCACACTACACACGCA",
        "m4_10_ifng": "CCGCCCAAATCCCTAAGTGAAGACTGGATTGACATCAAACCAGTCACACTACACACGCA",
        "m5_5_ifng": "CCGCCCAAATCCCGAAGGGAAGAGTGTAATGACGTCAAACCAGACACATTACACACGCA",
    }
    for mid, muts in _IFNG_MUTANTS.items():
        derived = _mutate(_IFNG_B14, muts)
        assert derived == mut_prints[mid], f"{mid}: derivation != SI print"
    assert _mutate(_IFNG_B14, [(26, "A")]) == _IFNG_NEG_MUT, \
        "IFN-gamma negative mutant derivation failed"
    entries.append({
        "id": "b1_4_ifng", "name": "B1-4 (parent aptamer)",
        "target": "IFN-gamma", "protein": ifng_prot,
        "sequence": _IFNG_B14, "alphabet": "dna", "length_nt": len(_IFNG_B14),
        "kd_nm": _IFNG_KD["b1_4_ifng"], "role": "binder",
        "reference": "Zhao L, et al. Molecules 2022;27:5725. doi:10.3390/molecules27175725 (Methods §3.1 sequence; Kd Results §2.2 text, Octet BLI). Parent B1-4 from Cao B, et al. PLoS ONE 2014 (PMID 24849390): Kd 74.5 nM there vs 913.9 nM here — cross-paper divergence registered",
        "kd_method": "Octet BLI (Zhao 2022); cross-paper Cao-2014 value 74.5 nM registered, not mixed into ranking",
        "sequence_verification": "Methods §3.1 printout equality",
        "ranking_eligible": True,
    })
    for mid, muts in _IFNG_MUTANTS.items():
        entries.append({
            "id": mid, "name": f"{mid.split('_')[0].upper()}-{mid.split('_')[1]} (B1-4 in-silico mutant)",
            "target": "IFN-gamma", "protein": ifng_prot,
            "sequence": mut_prints[mid], "alphabet": "dna",
            "length_nt": len(mut_prints[mid]),
            "kd_nm": _IFNG_KD[mid], "role": "binder",
            "reference": "Zhao 2022: Kd Results §2.2 text (Octet BLI); sequence SI Table S1 (zip mirrored at pub.mdpi-res.com; M5-5 cross-checked identical between SI Tables S1 and S5)",
            "kd_method": "Octet BLI (same assay as B1-4)",
            "sequence_verification": f"DERIVED from B1-4 by mutations {muts} (1-based) and asserted equal to the SI Table S1 printout",
            "ranking_eligible": True,
        })
    entries.append({
        "id": "negmut_ifng", "name": "positive-delta-G docking-negative mutant",
        "target": "IFN-gamma", "protein": ifng_prot,
        "sequence": _IFNG_NEG_MUT, "alphabet": "dna",
        "length_nt": len(_IFNG_NEG_MUT), "kd_nm": None, "role": "negative",
        "reference": "Zhao 2022 Methods §3.1 printout (docking-designed negative control, ZDOCK 1124 vs B1-4 1246; not experimentally binding-tested — caveat registered)",
        "kd_method": None,
        "sequence_verification": "DERIVED from B1-4 by mutation (26, G->A), asserted equal to the Methods printout",
        "ranking_eligible": False,
    })
    for e in _in_silico_negatives(20260830, 59, "ACGT", 2, "ifng_rand",
                                  "IFN-gamma", "59-nt random DNA"):
        e["protein"] = ifng_prot
        entries.append(e)

    # per-target coverage assertions (the ANCHORS.md §3.5 write-time check)
    from collections import Counter
    cov = {}
    for e in entries:
        c = cov.setdefault(e["target"], Counter())
        c[e["role"]] += 1
    for tgt, c in cov.items():
        assert c["binder"] >= 4, f"{tgt}: <4 Kd binders"
        assert c["negative"] >= 3, f"{tgt}: <3 negatives"

    # write the sliced protein fastas (generated, not hand-edited)
    PROTEIN_DIR.mkdir(parents=True, exist_ok=True)
    for fname, seq, label in [
        ("fgf2.fa", fgf2_mature, "FGF2 classic 155-aa form (P09038:134-288)"),
        ("fgf2_full.fa", fgf2_full, "FGF2 canonical (P09038, 288 aa)"),
        ("swine_h3_ha.fa", ha_mature, "swH3 HA0 mature (303305451:17-549)"),
        ("swine_h3_ha_full.fa", ha_full, "swH3 HA0 full translation (303305451:1-549)"),
        ("ifng.fa", ifng_mature, "IFN-gamma mature (P01579:24-166)"),
        ("ifng_full.fa", ifng_full, "IFN-gamma canonical (P01579, 166 aa)"),
    ]:
        wrapped = textwrap.fill(seq, width=60)
        (PROTEIN_DIR / fname).write_text(f">{label}\n{wrapped}\n")

    assert len(entries) == 29, f"expected 29 new Part-A entries, got {len(entries)}"
    return entries


def main() -> None:
    with open(V2_PATH) as fh:
        v2 = json.load(fh)

    part_a_entries = build_part_a(v2)

    new_anchors = []
    for anchor in NEW_ANCHORS:
        stats = verify_structure(anchor)
        prot_chains, apt_chains = anchor["chains"]
        record = {
            "aptamer_entry": anchor["aptamer_entry"],
            "target": anchor["target"],
            "pdb_id": anchor["pdb_id"],
            "aptamer_chain": apt_chains[0],
            "aptamer_chains": apt_chains,
            "protein_chains": prot_chains,
            "method": anchor["method"],
            "reference": anchor["reference"],
            "notes": anchor["notes"],
        }
        if anchor["mods"]:
            record["nuc_map"] = {m: NUC_MAP[m] for m in sorted(anchor["mods"])}
        record["curation_stats"] = stats
        new_anchors.append(record)

    v3 = copy.deepcopy(v2)
    # Part A: v2 entries carried verbatim (asserted), then extended
    assert v3["entries"] == v2["entries"], "Part A must be carried verbatim"
    v3["entries"] = list(v2["entries"]) + part_a_entries
    v3["n_entries"] = len(v3["entries"])
    retained_docking = copy.deepcopy(v2["docking_anchors"])
    assert len(retained_docking) == 5, "expected the 5 retained v2 docking anchors"
    v3["docking_anchors"] = retained_docking + new_anchors
    v3["n_docking_anchors"] = len(v3["docking_anchors"])
    # first-pass invariance: the docking section must be byte-identical to
    # the already-published (Exp-12-measured) first-pass v3 file
    if os.path.exists(V3_PATH):
        with open(V3_PATH) as fh:
            prev = json.load(fh)
        assert prev.get("docking_anchors") == v3["docking_anchors"], (
            "docking anchors must remain byte-identical to the first-pass v3 "
            "(the Fig. 3d run was measured on it)"
        )

    v3["description"] = (
        "E1 oracle capability-profiling anchor set v3 (two-pass extension of v2: "
        "(1) docking-power extension, 19 docking anchors over 14 independent "
        "protein targets — the Fig. 3d instrument; (2) Part-A extension with "
        "three admitted targets — FGF2 (10 binders), swine influenza H3N2 HA "
        "(4 binders + literature negative), IFN-gamma (6 binders + printed "
        "negative) — v2's six targets carried verbatim; SARS-CoV-2 RBD and "
        "HIV-1 RT FANA rejected at curation (sequence printability)"
    )
    v3["curated"] = "2026-08-27"
    v3["extends"] = "e1_anchor_set_v2.json"
    v3["preregistration"] = (
        "curate_e1_anchor_set_v3.py docstring, DOCKING-POWER EXTENSION "
        "PRE-REGISTRATION (2026-08-27)"
    )
    v3["docking_not_available"] = copy.deepcopy(v2["docking_not_available"])
    v3["docking_not_available"].update({
        "VEGF": v2["docking_not_available"].get(
            "VEGF",
            "no experimental aptamer-VEGF complex in RCSB (verified 2026-08-04)",
        ),
        "IL-17A": "no experimental aptamer-IL-17A complex in RCSB (verified 2026-08-04); docking N/A",
        "Angiopoietin-2": "no experimental aptamer-Ang2 complex in RCSB (verified 2026-08-04); docking N/A",
        "SARS-CoV-2 N": "superseded 2026-08-27: 8ZBF (N-NTD x DNA, X-ray 2.8 A) admitted to the v3 docking set",
        "SARS-CoV-2 RBD": "superseded 2026-08-27: 9T74 (2'-F RNA x RBD, cryoEM 3.46 A) admitted to the v3 docking set",
    })
    v3["docking_rejected"] = {
        "4WB2/4WB3 (C5a x spiegelmer NOX-D20)": "mirror-image L-RNA/L-DNA chemistry — chirality-level OOD for D-RNA oracles (registered 2026-08-27)",
        "4R8I (CCL2 x mirror-image RNA)": "mirror-image chemistry (registered 2026-08-27)",
        "4NI7/4NI9 (IL-6 x SOMAmer SL1025)": "SOMAmer non-natural protein-binding bases — PDGF-BB 4HQU/4HQX precedent",
        "7JTN/7JTQ (complement factor B x SOMAmer)": "SOMAmer class, same precedent",
        "5UC6 (IL-1alpha x naphthyl-modified aptamer)": "naphthyl base modification, same precedent",
        "4ZBN (NGF x DNA triplex)": "DUZ = 5-benzylcarbamoyl-dU (verified RCSB chemcomp) — hydrophobic base modification, same precedent",
        "8J1Q/8J26 (SARS-CoV-2 RBD x bivalent DNA)": "85Y = 5-naphthylmethylcarbamoyl-dU (verified RCSB chemcomp) — SOMAmer class, same precedent; 8J26 also same-complex variant",
        "7YQ3/7YQ4 (insulin receptor x A43/A62)": "85Y SOMAmer-class aptamer (verified RCSB chemcomp)",
        "9SA8 (insulin receptor x HIR-6)": "A1J boronate-modified residues x9/19 — non-mappable chemistry",
        "6TXR (PvLDH x cubane-modified aptamer)": "cubane modification non-mappable",
        "HIV-1 RT re-depositions (5D3G/5HLF/5HRO/5I3U/5I42/6VUG/7OZW/7P15/7Z24-series)": "same 38-mer hairpin aptamer family as 1HVU and/or drug-bound ternaries — redundant",
        "Thrombin TBA-family variants (6Z8V/4LZ4/6EO6/9U3I)": "same TBA family as 4DII and/or modified variants",
        "Thrombin bivalent ternaries (5EW1/5EW2/7NTU)": "two aptamers simultaneously bound — protocol confound",
        "same-complex variants (3HXQ/5VOF/5HTO/7YQ4/8J26)": "alternate depositions of admitted complexes",
        "peptide targets (1ULL/484D/6CF2/1EXY/2RSK/2RU7)": "peptide, not protein targets",
        "fluorogenic-Fab chaperone systems (4KZD-series etc.)": "aptamer targets a small molecule, not the protein",
        "riboswitch/RBP natural-recognition complexes (U1A/S8/Hfq/polymerase/MS2/RIG-I)": "not selected-against-target aptamers",
        "weak-relevance model systems (3AGV IgG / 6SY4 TetR / 4M4O lysozyme / 6U81 DUX4 / 9I0V DasR)": "outside the therapeutic-aptamer target domain focus",
    }
    v3["rejected_candidates"] = dict(v2.get("rejected_candidates", {}))
    v3["rejected_candidates"].update({
        "SARS-CoV-2 RBD (Part A, second pass)": "Shekar 2025 Table 3 prints 5 BLI KD values but the sequences sit in an 83-sequence SI zip WITHOUT any printed mapping to the aptamer IDs (Table S1 enumerates per-variant subsets with restarting S.No; two orderings internally consistent) — sequence identity not assertion-verifiable. Survey verdict overturned at curation 2026-08-28.",
        "HIV-1 RT FANA (Part A, second pass)": "Ferreira-Bravo 2015 Table 1 prints >=9 family Kd values but the sequences are figure-only (Fig 3A / SI Fig S1 images); PDF/SI bot-walled from this environment and a vision extraction misread the primer-flank regions against the paper's own text-printed template — no independent verification anchor. Survey verdict overturned at curation 2026-08-28.",
        "Streptavidin (Part A)": "Ruigrok 2012 ChemBioChem table behind paywall — 5 aptamers 35-375 nM SPR asserted at abstract level only; unverifiable this pass.",
    })
    v3["known_limitations"] = list(v2["known_limitations"]) + [
        "Docking v3: 8ZBF and 9T74 have 'to be published' citations — provenance is the RCSB deposition; re-verify when papers appear.",
        "5VOE is a desGla + S195A factor-Xa construct (registered); 11F7t FANA (CFL) residues map to C.",
        "5HRT is mouse autotaxin (species caveat); aptamer is a DNA/2'-OMe chimera.",
        "3UZT models only a 7-nt core of the C13.18 aptamer — minimal interface.",
        "7ZQS and 9T74 are cryoEM anchors (2.54 / 3.46 A) — first non-X-ray members of the docking set.",
        "DNA aptamers: residues renamed to RNA letters without adding O2' atoms — atom-level deoxyribose remains (the structure-level reading of the T->U convention).",
        "1OOA holds two identical aptamer copies (C, D) — decoys perturb both as one rigid body.",
        "FGF2: primary PDF bot-walled — sequences/Kd verified via the Ribocentre-aptamer transcription (printed twice on that page) + family-motif nesting assertions; biphasic binders store Kd1 (two-site fit).",
        "Influenza H3N2 HA: selection strain A/swine/Minnesota/SG-00235/2007 is GISAID-restricted — protein surrogate = A/swine/Illinois/03040/2010(H3N2) full-length HA0 (95.1% aa identity to the MN/2008 partial; mature slice 17-549, C-terminal 17 aa absent from the record); aptamer-binding breadth across swine H3 lineages is the paper's own live-virus result.",
        "IFN-gamma: the M-series is a single in-silico-mutant family of B1-4 (same-assay Octet ranking is within-family by construction); the printed negative mutant is docking-designed, not experimentally binding-tested; B1-4 Kd diverges across papers (Cao 2014: 74.5 nM vs Zhao 2022: 913.9 nM) — registered, ranking uses only Zhao's same-assay values.",
        "HA and FGF2 negatives are partly in silico (fixed-seed randoms, seeds in entry references) — the SARS-CoV-2 N convention; literature negatives where printed (HA1c; IFN-gamma negative mutant).",
    ]
    assert v3["n_entries"] == len(v3["entries"]) == 95
    assert len(v3["docking_anchors"]) == 19
    # coverage: every target has >=4 Kd binders and >=3 negatives
    from collections import Counter
    by_target = {}
    for e in v3["entries"]:
        t = by_target.setdefault(e["target"], {"binder": 0, "negative": 0})
        t[e["role"] if e["role"] in t else "binder"] += 1
    for tgt, counts in by_target.items():
        assert counts["binder"] >= 4, f"{tgt}: <4 binders ({counts})"
        assert counts["negative"] >= 3, f"{tgt}: <3 negatives ({counts})"

    with open(V3_PATH, "w") as fh:
        json.dump(v3, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print(f"wrote {V3_PATH}: {len(v3['entries'])} Part-A entries "
          f"(66 v2-verbatim + {len(part_a_entries)} new), "
          f"{len(v3['docking_anchors'])} docking anchors, "
          f"{len(v3['docking_rejected'])} rejection classes registered")


if __name__ == "__main__":
    main()
