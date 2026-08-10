#!/usr/bin/env python3
"""Curate external literature anchors for the RNADesignAgent manuscript experiments.

Implements `docs/MANUSCRIPT.md` §2.2. Everything written lands under
`data/benchmarks/external_anchors/` and is reported in `SOURCES.md` there.

Automated parts (this script):
  1. `aptamers/known_aptamers.json`  — extracted from the two aptamer target JSONs
  2. `wt_cds/<target_id>.fa`         — wild-type CDS for the 20 Fig-3 proteins,
                                       fetched from NCBI eutils and validated against
                                       each target's `expected_cds_length_nt`
  3. `ires/ires_positive.fa`         — EMCV / HCV / poliovirus 5'UTR (IRES) regions
                                       from NCBI RefSeq genomes
  4. `ires/utr_negative.fa`          — 50 random human 5'-terminal windows from the
                                       local GENCODE v46 transcriptome (seed 0)

Manual parts (documented in SOURCES.md with TODO stubs):
  - vaccine_mrna/bnt162b2_full.fa, vaccine_mrna/mrna1273_full.fa
  - aptamers/pegaptanib.json
  - small_molecule/pairs.json

Usage (from `rna_agent_system/`):
    python experiments/curate_external_anchors.py
"""
from __future__ import annotations

import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCH = PROJECT_ROOT / "data" / "benchmarks"
OUT = BENCH / "external_anchors"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
HTTP_DELAY_S = 0.4  # be polite to NCBI (≤3 req/s without API key)


# --------------------------------------------------------------------------- helpers
def http_get(url: str, retries: int = 3) -> str:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as err:  # noqa: BLE001
            last_err = err
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} tries: {url}\n{last_err}")


def efetch_fasta(nuccore_id: str, seq_start: int | None = None, seq_stop: int | None = None,
                 strand: int | None = None) -> tuple[str, str]:
    """Return (header, sequence) for a nuccore record (optionally a sub-range)."""
    params = {"db": "nuccore", "id": nuccore_id, "rettype": "fasta", "retmode": "text"}
    if seq_start is not None:
        params["seq_start"] = str(seq_start)
    if seq_stop is not None:
        params["seq_stop"] = str(seq_stop)
    if strand is not None:
        params["strand"] = str(strand)
    text = http_get(f"{EUTILS}/efetch.fcgi?{urllib.parse.urlencode(params)}")
    time.sleep(HTTP_DELAY_S)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or not lines[0].startswith(">"):
        raise RuntimeError(f"efetch returned non-FASTA for {nuccore_id}: {text[:200]}")
    return lines[0], "".join(lines[1:]).upper()


def efetch_cds_na(nuccore_id: str) -> list[tuple[str, str]]:
    """Return all CDS regions of a record as [(header, sequence)]."""
    params = {"db": "nuccore", "id": nuccore_id, "rettype": "fasta_cds_na", "retmode": "text"}
    text = http_get(f"{EUTILS}/efetch.fcgi?{urllib.parse.urlencode(params)}")
    time.sleep(HTTP_DELAY_S)
    records: list[tuple[str, str]] = []
    header: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(buf).upper()))
            header, buf = line.strip(), []
        else:
            buf.append(line.strip())
    if header is not None:
        records.append((header, "".join(buf).upper()))
    if not records:
        raise RuntimeError(f"no CDS found for {nuccore_id}: {text[:200]}")
    return records


def esearch_nuccore(term: str, retmax: int = 5) -> list[str]:
    params = {"db": "nuccore", "term": term, "retmax": str(retmax), "retmode": "json"}
    text = http_get(f"{EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}")
    time.sleep(HTTP_DELAY_S)
    return json.loads(text)["esearchresult"].get("idlist", [])


def esearch_protein_uid(term: str) -> str | None:
    params = {"db": "protein", "term": term, "retmax": "1", "retmode": "json"}
    text = http_get(f"{EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}")
    time.sleep(HTTP_DELAY_S)
    ids = json.loads(text)["esearchresult"].get("idlist", [])
    return ids[0] if ids else None


def elink_protein_to_nuccore(protein_uid: str) -> list[str]:
    params = {"dbfrom": "protein", "db": "nuccore", "id": protein_uid, "retmode": "json"}
    text = http_get(f"{EUTILS}/elink.fcgi?{urllib.parse.urlencode(params)}")
    time.sleep(HTTP_DELAY_S)
    data = json.loads(text)
    links: list[str] = []
    for ls in data.get("linksets", []):
        for dbs in ls.get("linksetdbs", []):
            if dbs.get("dbto") == "nuccore":
                links.extend(dbs.get("links", []))
    return links


def write_fasta(path: Path, header: str, seq: str, width: int = 80) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(seq[i : i + width] for i in range(0, len(seq), width))
    path.write_text(f">{header}\n{body}\n", encoding="utf-8")


# --------------------------------------------------------------------------- WT CDS plans
# Each plan: (strategy, kwargs, expected_len_nt, note)
# Strategies:
#   range  — efetch a sub-range of a genome accession (viral CDS with known coordinates)
#   cds_pick — efetch all CDS of a record, pick the one closest to expected length
#   gene   — esearch a human RefSeq mRNA by gene name, then cds_pick
WT_CDS_PLANS: dict[str, dict] = {
    "SARS-CoV-2_Spike_WT": {"strategy": "range", "id": "NC_045512.2", "start": 21563, "stop": 25384,
                            "note": "spike glycoprotein CDS (Wuhan-Hu-1)"},
    "Influenza_HA_H1N1": {"strategy": "cds_pick", "id": "NC_002017.1",
                          "note": "A/PR/8/1934(H1N1) segment 4 HA (xref P03452; 566 aa — benchmark "
                                  "protein is 565 aa with a 1-aa deletion near residue 148)"},
    "HIV-1_Env_gp120": {"strategy": "range", "id": "K03455.1", "start": 6225, "stop": 8795,
                        "note": "HXB2 env (gp160) CDS"},
    "RSV_F_protein": {"strategy": "cds_pick", "id": "M11486.1",
                      "note": "RSV A2 complete genome, F gene (exact UniProt P03420 strain)"},
    "Zika_E_protein": {"strategy": "cds_pick", "id": "NC_012532.1", "note": "ZIKV MR766 polyprotein"},
    "HPV16_L1": {"strategy": "cds_pick", "id": "NC_001526.4", "note": "HPV16 L1 capsid"},
    "GFP": {"strategy": "cds_pick", "id": "MN114103.1", "note": "Aequorea victoria GFP cDNA (717 nt)"},
    "Luciferase": {"strategy": "cds_pick", "id": "M15077.1", "note": "Photinus pyralis luciferase"},
    "Beta_galactosidase": {"strategy": "range", "id": "NC_000913.3", "start": 363231, "stop": 366305,
                           "strand": 2, "note": "E. coli K-12 MG1655 lacZ CDS (NP_414878.1, complement)"},
    "A1AT": {"strategy": "gene", "gene": "SERPINA1", "note": "alpha-1 antitrypsin"},
    "Albumin": {"strategy": "gene", "gene": "ALB", "note": "human serum albumin"},
    "EPO": {"strategy": "gene", "gene": "EPO", "note": "erythropoietin"},
    "Factor_VIII": {"strategy": "gene", "gene": "F8", "note": "coagulation factor VIII"},
    "Growth_hormone": {"strategy": "gene", "gene": "GH1", "note": "growth hormone 1"},
    "HER2": {"strategy": "cds_pick", "id": "NM_004448.4",
             "note": "canonical ERBB2 mRNA (CCDS32642.1); longer than the shortest isoform"},
    "IFN_alpha_2a": {"strategy": "gene", "gene": "IFNA2", "note": "interferon alpha 2"},
    "IL-2": {"strategy": "gene", "gene": "IL2", "note": "interleukin 2"},
    "Insulin": {"strategy": "gene", "gene": "INS", "note": "insulin"},
    "Transferrin": {"strategy": "cds_pick", "id": "NM_001063.4",
                    "note": "canonical TF mRNA (CCDS3080.1); not the short isoform"},
    "Ovalbumin": {"strategy": "gene", "gene": "SERPINB14", "organism": "Gallus gallus",
                  "note": "chicken ovalbumin"},
}

IRES_PLANS = [
    ("EMCV", "NC_001479.1", 1, 840, "encephalomyocarditis virus 5'UTR (contains IRES, ~nt 260-834)"),
    ("HCV", "NC_004102.1", 1, 341, "hepatitis C virus 5'UTR (contains IRES)"),
    ("Poliovirus", "NC_002058.3", 1, 742, "poliovirus type 1 5'UTR (contains IRES)"),
]


def curate_known_aptamers(report: list[str]) -> None:
    targets_dir = BENCH / "RNA-BioBench-Aptamer" / "targets"
    out = {}
    for name in ("SARS-CoV-2_Nucleocapsid", "Thrombin"):
        d = json.loads((targets_dir / f"{name}.json").read_text())
        ref = d.get("known_aptamer_reference") or {}
        out[name] = {
            "pdb_id": d.get("pdb_id"),
            "pdb_chain": d.get("pdb_chain"),
            "sequence": ref.get("sequence"),
            "kd_nm": ref.get("kd_nm"),
            "reference": ref.get("reference"),
            "known_hotspot_residues": d.get("known_hotspot_residues"),
        }
    dest = OUT / "aptamers" / "known_aptamers.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    report.append(f"known_aptamers.json: {list(out)} (extracted from target JSONs)")


def curate_wt_cds(report: list[str]) -> None:
    targets_dir = BENCH / "RNA-BioBench-FullLength-mRNA" / "targets"
    for target_id, plan in WT_CDS_PLANS.items():
        expected = json.loads((targets_dir / f"{target_id}.json").read_text())["expected_cds_length_nt"]
        try:
            if plan["strategy"] == "range":
                header, seq = efetch_fasta(plan["id"], plan["start"], plan["stop"],
                                           strand=plan.get("strand"))
                src = f'{plan["id"]}:{plan["start"]}-{plan["stop"]}' + ("(-)" if plan.get("strand") == 2 else "")
            elif plan["strategy"] == "cds_pick":
                records = efetch_cds_na(plan["id"])
                header, seq = min(records, key=lambda r: abs(len(r[1]) - expected))
                src = plan["id"]
            elif plan["strategy"] == "protein_link":
                uid = esearch_protein_uid(plan["protein_acc"])
                links = elink_protein_to_nuccore(uid) if uid else []
                if not links:
                    raise RuntimeError("no nuccore link for protein accession")
                records = efetch_cds_na(links[0])
                header, seq = min(records, key=lambda r: abs(len(r[1]) - expected))
                src = f'{plan["protein_acc"]} -> nuccore uid {links[0]}'
            elif plan["strategy"] == "gene":
                organism = plan.get("organism", "Homo sapiens")
                term = f'{plan["gene"]}[Gene Name] AND "{organism}"[Organism] AND refseq[filter] AND mrna[filter]'
                ids = esearch_nuccore(term)
                if not ids:
                    raise RuntimeError(f"esearch empty for {term}")
                best = None
                for uid in ids[:3]:
                    records = efetch_cds_na(uid)
                    cand = min(records, key=lambda r: abs(len(r[1]) - expected))
                    if best is None or abs(len(cand[1]) - expected) < abs(len(best[1]) - expected):
                        best = cand
                        best_uid = uid
                header, seq = best
                src = f'esearch "{plan["gene"]}" -> uid {best_uid}'
            else:  # pragma: no cover
                raise RuntimeError(f"unknown strategy {plan['strategy']}")

            diff = len(seq) - expected
            status = "OK" if abs(diff) <= 3 else "LENGTH-MISMATCH"
            dest = OUT / "wt_cds" / f"{target_id}.fa"
            write_fasta(dest, f"{target_id} wild-type CDS | {src} | {plan['note']}", seq)
            report.append(f"wt_cds/{target_id}.fa: {len(seq)} nt (expected {expected}, diff {diff:+d}) [{status}] {src}")
        except Exception as err:  # noqa: BLE001
            report.append(f"wt_cds/{target_id}.fa: FAILED - {err}")


def curate_ires(report: list[str]) -> None:
    dest = OUT / "ires" / "ires_positive.fa"
    dest.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    for name, acc, start, stop, note in IRES_PLANS:
        try:
            _, seq = efetch_fasta(acc, start, stop)
            chunks.append((f"{name} IRES | {acc}:{start}-{stop} | {note}", seq))
            report.append(f"ires_positive {name}: {len(seq)} nt from {acc}:{start}-{stop}")
        except Exception as err:  # noqa: BLE001
            report.append(f"ires_positive {name}: FAILED - {err}")
    body = "\n".join(
        ">" + h + "\n" + "\n".join(s[i : i + 80] for i in range(0, len(s), 80)) for h, s in chunks
    )
    dest.write_text(body + "\n", encoding="utf-8")


def curate_utr_negatives(report: list[str], n: int = 50, window: int = 200, seed: int = 0) -> None:
    src = PROJECT_ROOT / "data" / "references" / "species" / "homo_sapiens" / "transcripts.fa"
    rng = random.Random(seed)
    entries: list[tuple[str, str]] = []
    current_header: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if current_header and buf:
            seq = "".join(buf)
            if len(seq) >= window:
                entries.append((current_header, seq[:window]))

    with src.open() as fh:
        for line in fh:
            if line.startswith(">"):
                flush()
                current_header, buf = line[1:].strip(), []
            else:
                buf.append(line.strip())
        flush()

    rng.shuffle(entries)
    picked = entries[:n]
    dest = OUT / "ires" / "utr_negative.fa"
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        f">neg_{i:03d} 5prime-{window}nt-window | {h}\n" + "\n".join(s[i : i + 80] for i in range(0, len(s), 80))
        for i, (h, s) in enumerate(picked)
    )
    dest.write_text(body + "\n", encoding="utf-8")
    report.append(f"utr_negative.fa: {len(picked)} windows of {window} nt (seed {seed}) from {src.relative_to(PROJECT_ROOT)}")


def write_sources_md(report: list[str]) -> None:
    """Regenerate the automated-curation section of SOURCES.md.

    The full hand-curated SOURCES.md (vaccine sequences, pegaptanib, small-molecule
    pairs, validation tables) lives in the repository; this function only rewrites
    the automated report section so re-runs stay consistent. If SOURCES.md exists,
    its content after the marker line is preserved.
    """
    marker = "<!-- MANUAL-SECTIONS-BELOW -->"
    header = [
        "# External Anchors — Provenance & Validation",
        "",
        "> Automated section regenerated by `experiments/curate_external_anchors.py`",
        "> (`docs/MANUSCRIPT.md` §2.2). See below the marker for the hand-curated sections.",
        "",
        "## Automated curation report",
        "",
    ]
    header += [f"- {r}" for r in report]
    header += ["", marker, ""]
    dest = OUT / "SOURCES.md"
    manual: list[str] = []
    if dest.exists():
        old = dest.read_text(encoding="utf-8").splitlines()
        if marker in old:
            manual = old[old.index(marker) + 1 :]
    if not manual:
        manual = [
            "Hand-curated sections (vaccine_mrna, pegaptanib, small_molecule/pairs.json,",
            "validation tables, benchmark-input repairs) — see git history or re-create",
            "from `docs/MANUSCRIPT.md` §2.2 if this file was regenerated from scratch.",
        ]
    dest.write_text("\n".join(header + manual) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: list[str] = []
    curate_known_aptamers(report)
    curate_wt_cds(report)
    curate_ires(report)
    curate_utr_negatives(report)
    write_sources_md(report)
    print("\n".join(f"- {r}" for r in report))
    print(f"\nAnchors -> {OUT}")


if __name__ == "__main__":
    main()
