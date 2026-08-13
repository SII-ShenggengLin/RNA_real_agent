#!/usr/bin/env python3
"""Swap the two oversized Fig-2a null-panel targets (Zika_E_protein 3419 aa,
Factor_VIII 2351 aa — both beyond the LinearDesign memory guard) for two
200-400 aa human proteins: OTC (354 aa, UniProt P00480) and PDGFB (241 aa,
UniProt P01127).

Fetches the UniProt canonical protein and the NCBI RefSeq CDS, verifies that
the CDS (stop codon stripped) translates exactly to the UniProt sequence,
then writes:

- `data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/<Id>.json`
- `data/benchmarks/external_anchors/wt_cds/<Id>.fa`

Usage (from `rna_agent_system/`):
    python experiments/swap_fig2a_targets.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
WT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "wt_cds"

SWAP_IN = {
    "OTC": {
        "target_name": "Ornithine transcarbamylase",
        "target_type": "therapeutic",
        "uniprot_accession": "P00480",
        "entry_name": "OTC_HUMAN",
        "refseq": "NM_000531.6",
        "expression_system": "HEK293",
        "paper_references": ["doi:10.1056/NEJMoa2303574"],
        "notes": ("Urea-cycle enzyme deficient in OTC deficiency; clinical mRNA therapy "
                  "target. Replaces Zika_E_protein (3419 aa, beyond LinearDesign memory guard)."),
    },
    "PDGFB": {
        "target_name": "Platelet-derived growth factor subunit B",
        "target_type": "therapeutic",
        "uniprot_accession": "P01127",
        "entry_name": "PDGFB_HUMAN",
        "refseq": "NM_002608.4",
        "expression_system": "HEK293",
        "paper_references": ["doi:10.1038/309722a0"],
        "notes": ("Secreted growth factor; PDGF-BB is also an aptamer anchor target in this "
                  "project. Replaces Factor_VIII (2351 aa, beyond LinearDesign memory guard)."),
    },
}

_CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L", "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M", "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S", "AGT": "S", "AGC": "S", "CCT": "P", "CCC": "P",
    "CCA": "P", "CCG": "P", "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T", "GCT": "A", "GCC": "A",
    "GCA": "A", "GCG": "A", "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*", "CAT": "H", "CAC": "H",
    "CAA": "Q", "CAG": "Q", "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K", "GAT": "D", "GAC": "D",
    "GAA": "E", "GAG": "E", "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W", "CGT": "R", "CGC": "R",
    "CGA": "R", "CGG": "R", "AGA": "R", "AGG": "R", "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as fh:
        return fh.read().decode()


def fasta_seq(text: str) -> str:
    return "".join(l.strip() for l in text.splitlines() if not l.startswith(">")).upper()


def translate(cds: str) -> str:
    assert len(cds) % 3 == 0, f"CDS length {len(cds)} not divisible by 3"
    return "".join(_CODON_TABLE[cds[i:i + 3]] for i in range(0, len(cds), 3))


def wrap(seq: str, width: int = 70) -> str:
    return "\n".join(seq[i:i + width] for i in range(0, len(seq), width))


def main() -> int:
    for target_id, meta in SWAP_IN.items():
        protein = fasta_seq(fetch(f"https://rest.uniprot.org/uniprotkb/{meta['uniprot_accession']}.fasta"))
        cds_raw = fasta_seq(fetch(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id="
            f"{meta['refseq']}&rettype=fasta_cds_na&retmode=text"))
        assert translate(cds_raw).endswith("*"), f"{target_id}: fetched CDS lacks stop codon"
        cds = cds_raw[:-3]
        assert translate(cds) == protein, f"{target_id}: CDS translation != UniProt sequence"
        assert 200 <= len(protein) <= 400, f"{target_id}: {len(protein)} aa outside 200-400 window"

        doc = {
            "target_id": target_id,
            "target_name": meta["target_name"],
            "target_type": meta["target_type"],
            "source_database": "UniProt",
            "accession": meta["uniprot_accession"],
            "species_for_codon_optimization": "Homo sapiens",
            "expression_system": meta["expression_system"],
            "paper_references": meta["paper_references"],
            "notes": meta["notes"],
            "uniprot_accession": meta["uniprot_accession"],
            "protein_sequence": protein,
            "protein_length_aa": len(protein),
            "sequence_checksum": hashlib.md5(protein.encode()).hexdigest().upper(),
            "organism_scientific": "Homo sapiens",
            "entry_name": meta["entry_name"],
            "expected_cds_length_nt": len(cds),
        }
        (TARGETS_DIR / f"{target_id}.json").write_text(json.dumps(doc, indent=2) + "\n")
        header = f">{target_id} wild-type CDS | RefSeq {meta['refseq']} CDS | {meta['target_name']}"
        (WT_DIR / f"{target_id}.fa").write_text(header + "\n" + wrap(cds) + "\n")
        print(f"{target_id}: {len(protein)} aa, CDS {len(cds)} nt, translation verified -> targets/ + wt_cds/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
