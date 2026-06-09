#!/usr/bin/env python3
"""Download real protein sequences and structures for RNA-BioBench datasets."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any
import requests

BASE_DIR = Path(__file__).parent.resolve()
UNIPROT_API = "https://rest.uniprot.org/uniprotkb"
PDB_API = "https://data.rcsb.org/rest/v1/core/entry"
PDB_DOWNLOAD = "https://files.rcsb.org/download"
NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def fetch_uniprot(accession: str) -> dict[str, Any]:
    url = f"{UNIPROT_API}/{accession}.json"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def parse_uniprot(data: dict[str, Any]) -> dict[str, Any]:
    seq = data.get("sequence", {})
    protein_desc = data.get("proteinDescription", {})
    recommended = protein_desc.get("recommendedName", {})
    return {
        "accession": data.get("primaryAccession", ""),
        "entry_name": data.get("uniProtkbId", ""),
        "protein_name": recommended.get("fullName", {}).get("value", ""),
        "organism_scientific": data.get("organism", {}).get("scientificName", ""),
        "organism_common": data.get("organism", {}).get("commonName", ""),
        "sequence": seq.get("sequence", ""),
        "sequence_length": seq.get("length", 0),
        "sequence_checksum": seq.get("md5", ""),
        "gene": [g.get("geneName", {}).get("value", "") for g in data.get("genes", [])],
    }


def fetch_uniprot_fasta(accession: str) -> str:
    url = f"{UNIPROT_API}/{accession}.fasta"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text


def fetch_pdb_info(pdb_id: str) -> dict[str, Any]:
    url = f"{PDB_API}/{pdb_id.lower()}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def download_pdb(pdb_id: str, out_dir: Path) -> Path:
    pdb_id = pdb_id.lower()
    out_path = out_dir / f"{pdb_id}.pdb"
    if out_path.exists() and out_path.stat().st_size > 1000:
        print(f"  [skip] {out_path.name} already exists")
        return out_path
    url = f"{PDB_DOWNLOAD}/{pdb_id}.pdb"
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    out_path.write_text(resp.text)
    print(f"  [downloaded] {out_path.name} ({len(resp.text)} chars)")
    return out_path


def fetch_ncbi_protein_fasta(accession: str) -> str:
    url = f"{NCBI_EUTILS}/efetch.fcgi?db=protein&id={accession}&rettype=fasta&retmode=text"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  [saved] {path}")


def save_fasta(path: Path, header: str, sequence: str) -> None:
    path.write_text(f">{header}\n{sequence}\n")
    print(f"  [saved] {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Full-Length mRNA targets
# ─────────────────────────────────────────────────────────────────────────────

def build_full_length_mrna_datasets() -> None:
    out_targets = BASE_DIR / "RNA-BioBench-FullLength-mRNA" / "targets"
    out_seqs = BASE_DIR / "RNA-BioBench-FullLength-mRNA" / "sequences"

    targets = [
        {
            "target_id": "SARS-CoV-2_Spike_WT",
            "target_name": "SARS-CoV-2 spike glycoprotein (wild-type, Wuhan-Hu-1)",
            "target_type": "vaccine",
            "source_database": "UniProt",
            "accession": "P0DTC2",
            "ncbi_reference": "YP_009724390.1",
            "genome_accession": "NC_045512.2",
            "species_for_codon_optimization": "Homo sapiens",
            "expression_system": "HEK293",
            "paper_references": [
                "doi:10.1038/s41586-020-2622-0",
                "doi:10.1126/science.abe8499"
            ],
            "notes": "Wild-type full-length Spike used in original COVID-19 vaccine development",
            "uniprot_accession": "P0DTC2",
        },
        {
            "target_id": "Influenza_HA_H1N1",
            "target_name": "Influenza A hemagglutinin (H1N1 A/California/04/2009)",
            "target_type": "vaccine",
            "source_database": "UniProt",
            "accession": "Q6DU13",
            "species_for_codon_optimization": "Homo sapiens",
            "expression_system": "HEK293",
            "paper_references": [
                "doi:10.1126/science.1172482"
            ],
            "notes": "High variability influenza HA; UTR optimization is critical",
            "uniprot_accession": "Q6DU13",
        },
        {
            "target_id": "EPO",
            "target_name": "Erythropoietin",
            "target_type": "therapeutic",
            "source_database": "UniProt",
            "accession": "P01588",
            "species_for_codon_optimization": "Homo sapiens",
            "expression_system": "CHO",
            "paper_references": [
                "doi:10.1038/313806a0"
            ],
            "notes": "High-expression-demand therapeutic protein",
            "uniprot_accession": "P01588",
        },
        {
            "target_id": "GFP",
            "target_name": "Green fluorescent protein (avGFP)",
            "target_type": "reporter",
            "source_database": "UniProt",
            "accession": "P42212",
            "species_for_codon_optimization": "Aequorea victoria",
            "expression_system": "E. coli",
            "paper_references": [
                "doi:10.1126/science.8303295"
            ],
            "notes": "Standard reporter/control for mRNA expression validation",
            "uniprot_accession": "P42212",
        },
        {
            "target_id": "Luciferase",
            "target_name": "Firefly luciferase",
            "target_type": "reporter",
            "source_database": "UniProt",
            "accession": "P08659",
            "species_for_codon_optimization": "Photinus pyralis",
            "expression_system": "HEK293",
            "paper_references": [
                "doi:10.1016/0003-2697(87)90103-0"
            ],
            "notes": "Widely used benchmark for mRNA transfection and expression",
            "uniprot_accession": "P08659",
        },
    ]

    for target in targets:
        acc = target["uniprot_accession"]
        print(f"\nFetching {target['target_id']} ({acc})...")
        try:
            data = fetch_uniprot(acc)
            parsed = parse_uniprot(data)
            target["protein_sequence"] = parsed["sequence"]
            target["protein_length_aa"] = parsed["sequence_length"]
            target["sequence_checksum"] = parsed["sequence_checksum"]
            target["organism_scientific"] = parsed["organism_scientific"]
            target["entry_name"] = parsed["entry_name"]
            target["expected_cds_length_nt"] = parsed["sequence_length"] * 3

            fasta = fetch_uniprot_fasta(acc)
            save_fasta(
                out_seqs / f"{target['target_id']}.fa",
                f"{target['target_id']}|{acc}|{target['target_name']}",
                parsed["sequence"]
            )
            time.sleep(0.5)
        except Exception as e:
            print(f"  [ERROR] {target['target_id']}: {e}")
            continue

        save_json(out_targets / f"{target['target_id']}.json", target)

    # dataset manifest
    manifest = {
        "dataset_name": "RNA-BioBench-FullLength-mRNA",
        "schema_version": "1.0.0",
        "description": "Benchmark dataset for full-length mRNA design (Type-I BMC)",
        "created_date": time.strftime("%Y-%m-%d"),
        "targets": [t["target_id"] for t in targets],
        "target_count": len(targets),
        "fields": [
            "target_id", "target_name", "target_type", "accession",
            "protein_sequence", "protein_length_aa", "species_for_codon_optimization",
            "expression_system", "expected_cds_length_nt", "paper_references"
        ]
    }
    save_json(out_targets / "../dataset_manifest.json", manifest)


# ─────────────────────────────────────────────────────────────────────────────
# Aptamer targets
# ─────────────────────────────────────────────────────────────────────────────

def build_aptamer_datasets() -> None:
    out_targets = BASE_DIR / "RNA-BioBench-Aptamer" / "targets"
    out_structs = BASE_DIR / "RNA-BioBench-Aptamer" / "structures"

    targets = [
        {
            "target_id": "SARS-CoV-2_Nucleocapsid",
            "target_name": "SARS-CoV-2 Nucleocapsid phosphoprotein",
            "target_type": "viral",
            "pdb_id": "6M3M",
            "pdb_chain": "A",
            "uniprot_accession": "P0DTC9",
            "known_hotspot_residues": "A/44,A/45,A/46,A/47,A/48",
            "hotspot_source": "Literature-reported RNA binding domain (aa 44-174)",
            "known_aptamer_reference": {
                "sequence": "AGGGGAGUGGAGGUUGGUUU",
                "kd_nm": 15.2,
                "reference": "doi:10.1101/2020.04.17.046920"
            },
            "paper_references": [
                "doi:10.1101/2020.04.17.046920",
                "doi:10.1016/j.cell.2020.05.015"
            ],
            "notes": "Real RNA aptamer target with published binding data",
        },
        {
            "target_id": "Thrombin",
            "target_name": "Human alpha-thrombin",
            "target_type": "therapeutic",
            "pdb_id": "1HAO",
            "pdb_chain": "H",
            "uniprot_accession": "P00734",
            "known_hotspot_residues": "H/46,H/67,H/70,H/72,H/97",
            "hotspot_source": "Exosite I / II (reference TBA aptamer)",
            "known_aptamer_reference": {
                "sequence": "GGTTGGTGTGGTTGG",
                "kd_nm": 25.0,
                "reference": "pmid:8318863"
            },
            "paper_references": [
                "doi:10.1126/science.8318863",
                "pmid:8318863"
            ],
            "notes": "Classic thrombin-binding aptamer (TBA) target",
        },
        {
            "target_id": "GFP",
            "target_name": "Green fluorescent protein (avGFP)",
            "target_type": "reporter",
            "pdb_id": "1GFL",
            "pdb_chain": "A",
            "uniprot_accession": "P42212",
            "known_hotspot_residues": "",
            "hotspot_source": "Beta-barrel surface (non-specific binding region)",
            "known_aptamer_reference": None,
            "paper_references": [
                "doi:10.1126/science.8303295"
            ],
            "notes": "Reporter protein for aptamer binding validation; no known natural aptamer",
        },
    ]

    for target in targets:
        pdb_id = target["pdb_id"]
        acc = target.get("uniprot_accession")
        print(f"\nProcessing {target['target_id']} (PDB {pdb_id})...")

        # Download PDB
        try:
            download_pdb(pdb_id, out_structs)
        except Exception as e:
            print(f"  [ERROR] PDB download {pdb_id}: {e}")

        # Fetch UniProt for sequence
        if acc:
            try:
                data = fetch_uniprot(acc)
                parsed = parse_uniprot(data)
                target["protein_sequence"] = parsed["sequence"]
                target["protein_length_aa"] = parsed["sequence_length"]
                target["sequence_checksum"] = parsed["sequence_checksum"]
                target["organism_scientific"] = parsed["organism_scientific"]
                target["gene"] = parsed["gene"]
                time.sleep(0.5)
            except Exception as e:
                print(f"  [ERROR] UniProt {acc}: {e}")

        save_json(out_targets / f"{target['target_id']}.json", target)

    # dataset manifest
    manifest = {
        "dataset_name": "RNA-BioBench-Aptamer",
        "schema_version": "1.0.0",
        "description": "Benchmark dataset for RNA aptamer design (Type-II BMC)",
        "created_date": time.strftime("%Y-%m-%d"),
        "targets": [t["target_id"] for t in targets],
        "target_count": len(targets),
        "fields": [
            "target_id", "target_name", "target_type", "pdb_id", "pdb_chain",
            "protein_sequence", "protein_length_aa", "known_hotspot_residues",
            "known_aptamer_reference", "paper_references"
        ]
    }
    save_json(out_targets / "../dataset_manifest.json", manifest)


if __name__ == "__main__":
    print("=" * 60)
    print("RNA-BioBench Dataset Builder")
    print("=" * 60)
    print("\n--- Building Full-Length mRNA dataset ---")
    build_full_length_mrna_datasets()
    print("\n--- Building Aptamer dataset ---")
    build_aptamer_datasets()
    print("\nDone!")
