#!/usr/bin/env python3
"""Download reference transcriptomes / genomes for RNA design workflows.

Usage:
    python download_references.py
    python download_references.py --species homo_sapiens mus_musculus
    python download_references.py --list
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import shutil
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger("download_references")

# ═══════════════════════════════════════════════════════════════════════════════
# Species configurations
# ═══════════════════════════════════════════════════════════════════════════════

SPECIES_CONFIG: Dict[str, Dict[str, Any]] = {
    "homo_sapiens": {
        "display_name": "Homo sapiens",
        "files": {
            "transcripts": {
                "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_46/gencode.v46.transcripts.fa.gz",
                "gz_filename": "gencode.v46.transcripts.fa.gz",
                "final_filename": "transcripts.fa",
            }
        },
        "default": True,
    },
    "mus_musculus": {
        "display_name": "Mus musculus",
        "files": {
            "transcripts": {
                "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_mouse/release_M36/gencode.vM36.transcripts.fa.gz",
                "gz_filename": "gencode.vM36.transcripts.fa.gz",
                "final_filename": "transcripts.fa",
            }
        },
        "default": False,
    },
    "sars_cov_2": {
        "display_name": "Severe acute respiratory syndrome coronavirus 2",
        "files": {
            "genome": {
                "url": "https://ftp.ncbi.nlm.nih.gov/refseq/release/viral/viral.1.1.genomic.fna.gz",
                "gz_filename": "viral.1.1.genomic.fna.gz",
                "final_filename": "genome.fa",
            }
        },
        "default": True,
    },
    "danio_rerio": {
        "display_name": "Danio rerio",
        "files": {
            "transcripts": {
                "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_zebrafish/release_47/gencode.v47.transcripts.fa.gz",
                "gz_filename": "gencode.v47.transcripts.fa.gz",
                "final_filename": "transcripts.fa",
            }
        },
        "default": False,
    },
    "rattus_norvegicus": {
        "display_name": "Rattus norvegicus",
        "files": {
            "transcripts": {
                "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_rat/release_M35/gencode.vM35.transcripts.fa.gz",
                "gz_filename": "gencode.vM35.transcripts.fa.gz",
                "final_filename": "transcripts.fa",
            }
        },
        "default": False,
    },
}


def _root_dir() -> Path:
    return Path(__file__).resolve().parent / "species"


def _download(url: str, dest: Path) -> None:
    """Download *url* to *dest* with progress logging."""
    _LOGGER.info("downloading %s -> %s", url, dest)
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as exc:
        _LOGGER.error("download_failed url=%s err=%s", url, exc)
        raise


def _decompress_gz(gz_path: Path, dest: Path) -> None:
    """Decompress gzip file."""
    _LOGGER.info("decompressing %s -> %s", gz_path, dest)
    with gzip.open(gz_path, "rb") as f_in, open(dest, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def download_species(species_id: str, force: bool = False) -> None:
    """Download reference files for a single species."""
    config = SPECIES_CONFIG.get(species_id)
    if not config:
        raise ValueError(
            f"Unknown species: {species_id!r}. "
            f"Supported: {sorted(SPECIES_CONFIG)}"
        )

    out_dir = _root_dir() / species_id
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata: Dict[str, Any] = {
        "species_id": species_id,
        "display_name": config["display_name"],
        "files": {},
    }

    for file_key, file_info in config["files"].items():
        gz_path = out_dir / file_info["gz_filename"]
        final_path = out_dir / file_info["final_filename"]

        if final_path.exists() and not force:
            _LOGGER.info("[%s] %s already exists, skipping", species_id, final_path.name)
            metadata["files"][file_key] = {
                "path": str(final_path),
                "url": file_info["url"],
                "status": "skipped",
            }
            continue

        # Download
        if not gz_path.exists() or force:
            _download(file_info["url"], gz_path)

        # Decompress
        _decompress_gz(gz_path, final_path)
        gz_path.unlink(missing_ok=True)

        metadata["files"][file_key] = {
            "path": str(final_path),
            "url": file_info["url"],
            "status": "downloaded",
        }

    # Write metadata
    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    _LOGGER.info("[%s] done -> %s", species_id, out_dir)


def list_species() -> None:
    """Print available species."""
    print("Available species:")
    for sid, config in sorted(SPECIES_CONFIG.items()):
        flag = " (default)" if config["default"] else ""
        print(f"  {sid:<20} {config['display_name']}{flag}")
        for fk, fi in config["files"].items():
            print(f"      {fk}: {fi['final_filename']} <- {fi['url']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download reference transcriptomes / genomes for RNA workflows"
    )
    parser.add_argument(
        "--species",
        nargs="+",
        help="Species IDs to download (default: all species marked as default)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download ALL configured species (not just defaults)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if files already exist",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available species and exit",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.list:
        list_species()
        return

    if args.all:
        species_to_download = sorted(SPECIES_CONFIG)
    elif args.species:
        species_to_download = args.species
    else:
        species_to_download = [
            sid for sid, cfg in SPECIES_CONFIG.items() if cfg["default"]
        ]

    if not species_to_download:
        print("No species selected. Use --list to see available options.")
        return

    _LOGGER.info("species_to_download=%s", species_to_download)
    for sid in species_to_download:
        try:
            download_species(sid, force=args.force)
        except Exception as exc:
            _LOGGER.error("species_download_failed species=%s err=%s", sid, exc)


if __name__ == "__main__":
    main()
