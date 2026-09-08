#!/usr/bin/env python3
"""Wet-lab comparison batch — human EPO (193 aa) × Influenza A HA H1N1 PR8 (565 aa).

Five design arms per protein, ONE full-length construct (5'UTR + CDS + 3'UTR)
per arm, user-confirmed pre-registration (2026-09-08):

  WT           wild-type CDS (RefSeq NM_000799.5 / GenBank PR8 segment-4 CDS)
               + unified BNT162b2 UTR chassis
  LinearDesign official binary, lambda = 4, human codon table, default beam,
               stop convention: single UGA appended (supplement convention)
               + unified BNT162b2 UTR chassis
  RNARL        deployed RNARL actor service (port 8008),
               model_type "Homo sapiens mRNA" (deterministic inference)
               + unified BNT162b2 UTR chassis
  GEMORNA      STANDALONE GEMORNA repo runs only (gemorna_service_env python on
               src/generate.py / main_pred5UTR.py / main_pred3UTR.py) — zero
               platform components in the design path. Pre-registered pick:
               5 CDS draws per protein -> exact-translation filter -> highest
               human CAI; UTR pool 12 5'UTR (4/4/4 short/medium/long) + 10
               3'UTR (4/3/3, shared across both proteins — the UTR generators
               are not protein-conditioned and the GEMORNA paper reuses one
               UTR set across targets) -> top PRED-5UTR MRL / PRED-3UTR score.
  Ours         full_length_mrna_design via the CLI form entry, navigation
               unset (platform default = GenNav-λ + two-step governed UTR
               pool, DECISIONS (aa)/(bb)), rank-1 of one frozen run.

Outputs land in experiments/wetlab_batch_epo_ha/{refs,outputs}/ and the final
deliverable is outputs/wetlab_batch_EPO_HA.xlsx (sequences + in-silico metrics
+ provenance sheets).

Usage (from rna_agent_system/):
  PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/wetlab_batch_epo_ha/run_wetlab_batch.py --stage <fetch_refs|verify|lineardesign|rnarl|gemorna|ours|metrics|xlsx> [--target EPO|HA|all]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REFS = HERE / "refs"
OUT = HERE / "outputs"
TARGETS_FL = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
LINEARDESIGN_DIR = PROJECT_ROOT / "external_repos" / "LinearDesign"
GEMORNA_DIR = PROJECT_ROOT / "external_repos" / "GEMORNA"
RELEVANT_REFS = PROJECT_ROOT.parent / "relevant_references"
RNARL_START = PROJECT_ROOT / "microservices" / "rnarl_service" / "start.sh"

PROTEINS = ["EPO", "HA"]
UTR5_DRAWS = {"short": 4, "medium": 4, "long": 4}   # 12 (GEMORNA paper screening scale)
UTR3_DRAWS = {"short": 4, "medium": 3, "long": 3}   # 10
CDS_DRAWS_PER_PROTEIN = 5                            # GEMORNA direct-full-length protocol

UNIPROT = {
    "EPO": "P01588",
    "HA": "P03452",
}
NCBI_PROTEIN = {"HA": "ABD77675.1"}     # GenBank PR8 segment-4 protein, EXACT match to UniProt
                                         # P03452 (565 aa; verified against all five UniProt EMBL
                                         # xrefs - the asset's original AAL09324.1 ref was WRONG,
                                         # baboon duffy antigen, corrected by this batch)
HA_SEGMENT_ACC = "CY009444"              # GenBank PR8 segment 4 whose CDS = ABD77675.1 = the
                                         # SAME 565-aa HA as the target asset (Mount Sinai lineage,
                                         # NIAID re-sequencing). Disclosed NOT-used variant: RefSeq
                                         # NC_002017.1 = V01088 = Winter 1981 lineage (566 aa),
                                         # differing by only 8 HA1 residues (TK146-147N + E155A/
                                         # P199S/E203D/L207I/M268R/Y308F/T397S, 98.6% identity)
REFSEQ_MRNA = {"EPO": "NM_000799.4"}   # current RefSeq version (esummary-verified 2026-09-08)
BNT_VECTOR_ACC = "PP544446.1"         # BNT162b2 vector (Raoult direct submission 2024)
HBA1_REFSEQ = "NM_000558.5"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

_STOP_CODONS = {"TAA", "TAG", "TGA"}

_CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


# ── small helpers ────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def to_rna(seq: str) -> str:
    return seq.upper().replace("T", "U")


def to_dna(seq: str) -> str:
    return seq.upper().replace("U", "T")


def translate(dna: str) -> str:
    dna = to_dna(dna)
    aa = []
    for i in range(0, len(dna) - len(dna) % 3, 3):
        aa.append(_CODON_TABLE.get(dna[i:i + 3], "X"))
    return "".join(aa)


def revcomp(dna: str) -> str:
    return to_dna(dna).translate(str.maketrans("ACGT", "TGCA"))[::-1]


def gc_percent(seq: str) -> float:
    s = to_dna(seq)
    return round(100.0 * (s.count("G") + s.count("C")) / len(s), 2)


def http_get(url: str, dest: Path, timeout: int = 120) -> str:
    if dest.exists():
        return dest.read_text()
    REFSp = dest.parent
    REFSp.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "rnada-wetlab-batch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", "replace")
    dest.write_text(text)
    return text


def parse_fasta(text: str) -> list[tuple[str, str]]:
    recs: list[tuple[str, str]] = []
    name, buf = None, []
    for line in text.splitlines():
        if line.startswith(">"):
            if name is not None:
                recs.append((name, "".join(buf)))
            name, buf = line[1:].strip(), []
        elif line.strip():
            buf.append(line.strip())
    if name is not None:
        recs.append((name, "".join(buf)))
    return recs


def find_orf_encoding(dna: str, protein: str) -> list[tuple[int, int, int]]:
    """Return (start, frame, strand) hits whose ATG..stop translation == protein."""
    hits = []
    plen = len(protein)
    for strand, seq in ((1, to_dna(dna)), (-1, revcomp(dna))):
        for frame in range(3):
            i = frame
            while i < len(seq):
                if seq[i:i + 3] == "ATG":
                    j = i
                    prot = []
                    ok = True
                    while j + 3 <= len(seq):
                        c = seq[j:j + 3]
                        a = _CODON_TABLE.get(c, "X")
                        if a == "*":
                            break
                        prot.append(a)
                        j += 3
                        if len(prot) > plen:
                            ok = False
                            break
                    if ok and "".join(prot) == protein and j + 3 <= len(seq) and seq[j:j + 3] in _STOP_CODONS:
                        hits.append((i, frame, strand))
                i += 3   # stay in frame
    return hits


def load_target(name: str) -> dict[str, Any]:
    return json.loads((TARGETS_FL / f"{'Influenza_HA_H1N1' if name == 'HA' else 'EPO'}.json").read_text())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


# ── stage: fetch_refs ────────────────────────────────────────────────────────

def stage_fetch_refs() -> None:
    REFSp = REFS
    jobs = {
        "uniprot_EPO.fasta": f"https://rest.uniprot.org/uniprotkb/{UNIPROT['EPO']}.fasta",
        "uniprot_HA.fasta": f"https://rest.uniprot.org/uniprotkb/{UNIPROT['HA']}.fasta",
        "ncbi_protein_HA.fasta": f"{EUTILS}/efetch.fcgi?db=protein&id={NCBI_PROTEIN['HA']}&rettype=fasta&retmode=text",
        "refseq_EPO.gb": f"{EUTILS}/efetch.fcgi?db=nuccore&id={REFSEQ_MRNA['EPO']}&rettype=gb&retmode=text",
        "bnt_vector_PP544446.fasta": f"{EUTILS}/efetch.fcgi?db=nuccore&id={BNT_VECTOR_ACC}&rettype=fasta&retmode=text",
        "hba1_NM_000558.fasta": f"{EUTILS}/efetch.fcgi?db=nuccore&id={HBA1_REFSEQ}&rettype=fasta&retmode=text",
    }
    for fname, url in jobs.items():
        text = http_get(url, REFSp / fname)
        log(f"fetched {fname} ({len(text)} chars)")

    # HA WT CDS: original PR8 segment 4 (V01088, UniProt P03452 xref)
    gb_text = http_get(
        f"{EUTILS}/efetch.fcgi?db=nuccore&id={HA_SEGMENT_ACC}&rettype=gb&retmode=text",
        REFS / f"ha_segment_{HA_SEGMENT_ACC}.gb",
    )
    (REFS / "ha_segment_accession.txt").write_text(HA_SEGMENT_ACC)
    log(f"fetched HA segment GenBank {HA_SEGMENT_ACC} ({len(gb_text)} chars)")
    # disclosure reference: RefSeq segment 4 = the OTHER PR8 variant (566 aa)
    http_get(
        f"{EUTILS}/efetch.fcgi?db=nuccore&id=NC_002017.1&rettype=gb&retmode=text",
        REFS / "ha_segment_NC_002017.1.gb",
    )
    log("fetched RefSeq NC_002017.1 (disclosure: 566-aa PR8 variant, not used)")


def parse_genbank_origin(gb_text: str) -> str:
    seq_lines = []
    in_origin = False
    for line in gb_text.splitlines():
        if line.startswith("ORIGIN"):
            in_origin = True
            continue
        if in_origin:
            if line.startswith("//"):
                break
            seq_lines.append(re.sub(r"[^A-Za-z]", "", line))
    return "".join(seq_lines).upper()


# ── stage: verify ────────────────────────────────────────────────────────────

def _first_seq(path: Path) -> str:
    recs = parse_fasta(path.read_text())
    return max((s for _, s in recs), key=len)


def stage_verify() -> dict[str, Any]:
    report: dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat(), "channels": {}}
    checks: list[tuple[str, bool, str]] = []

    epo = load_target("EPO")
    ha = load_target("HA")

    # 1. EPO protein: UniProt + RefSeq mRNA CDS (GenBank record, ORF-verified)
    up_epo = _first_seq(REFS / "uniprot_EPO.fasta")
    checks.append(("EPO UniProt P01588 == target asset", up_epo == epo["protein_sequence"],
                   f"uniprot_len={len(up_epo)} asset_len={epo['protein_length_aa']}"))
    epo_mrna = parse_genbank_origin((REFS / "refseq_EPO.gb").read_text())
    epo_hits = find_orf_encoding(epo_mrna, epo["protein_sequence"])
    epo_uniq = {(h[1], h[2]) for h in epo_hits}
    checks.append((f"EPO RefSeq {REFSEQ_MRNA['EPO']} contains a single-frame ORF encoding the protein",
                   len(epo_uniq) == 1, f"mrna_len={len(epo_mrna)} frame/strand hits={sorted(epo_uniq)}"))
    strand_e = next(iter(epo_uniq))[1]
    hit_e = [h for h in epo_hits if h[2] == strand_e][0]
    scan_e = to_dna(epo_mrna) if strand_e == 1 else revcomp(epo_mrna)
    epo_cds_full = scan_e[hit_e[0]: hit_e[0] + 3 * len(epo["protein_sequence"]) + 3]
    epo_stop = to_rna(epo_cds_full[-3:])
    epo_cds_dna = epo_cds_full[:-3]
    checks.append(("EPO RefSeq CDS length == 579 (no stop)",
                   len(epo_cds_dna) == 579, f"len={len(epo_cds_dna)} natural_stop={epo_stop}"))
    checks.append(("EPO RefSeq CDS translation == protein",
                   translate(epo_cds_dna) == epo["protein_sequence"], ""))

    # 2. HA protein: UniProt + NCBI protein record
    up_ha = _first_seq(REFS / "uniprot_HA.fasta")
    ncbi_ha = _first_seq(REFS / "ncbi_protein_HA.fasta")
    checks.append(("HA UniProt P03452 == target asset", up_ha == ha["protein_sequence"],
                   f"uniprot_len={len(up_ha)} asset_len={ha['protein_length_aa']}"))
    checks.append(("HA GenBank ABD77675.1 == UniProt P03452", ncbi_ha == up_ha,
                   f"ncbi_len={len(ncbi_ha)}"))

    # 3. HA WT CDS from the linked segment record
    acc = (REFS / "ha_segment_accession.txt").read_text().strip()
    seg = parse_genbank_origin((REFS / f"ha_segment_{acc}.gb").read_text())
    hits = find_orf_encoding(seg, ha["protein_sequence"])
    uniq = {(h[1], h[2]) for h in hits}
    checks.append(("HA segment contains an ORF encoding the target protein (one reading frame)",
                   len(uniq) == 1, f"segment={acc} len={len(seg)} frame/strand hits={sorted(uniq)}"))
    # extract the WT CDS (with its natural stop, then strip for storage)
    strand = next(iter(uniq))[1]
    hit = [h for h in hits if h[2] == strand][0]
    wt_cds_dna = to_dna(seg) if strand == 1 else revcomp(seg)
    ha_wt_full = wt_cds_dna[hit[0]: hit[0] + 3 * len(ha["protein_sequence"]) + 3]
    assert translate(ha_wt_full[:-3]) == ha["protein_sequence"], "HA WT CDS re-extraction failed"
    checks.append(("HA WT CDS length == 1695 (no stop)", len(ha_wt_full) - 3 == 1695,
                   f"len={len(ha_wt_full) - 3} natural_stop={to_rna(ha_wt_full[-3:])}"))
    # disclosure (report-only): RefSeq NC_002017.1 = the 566-aa PR8 variant (NOT used)
    refseq_seg = parse_genbank_origin((REFS / "ha_segment_NC_002017.1.gb").read_text())
    m_cds = re.search(r"CDS\s+(\d+)\.\.(\d+)", (REFS / "ha_segment_NC_002017.1.gb").read_text())
    if m_cds:
        a, b = int(m_cds.group(1)), int(m_cds.group(2))
        refseq_prot = translate(refseq_seg[a - 1: b]).rstrip("*")
        checks.append(("RefSeq NC_002017.1 HA = 566-aa variant, differs from target (disclosed, not used)",
                       len(refseq_prot) == 566 and refseq_prot != ha["protein_sequence"],
                       f"refseq_prot_len={len(refseq_prot)} target_len={ha['protein_length_aa']}"))

    # 4. BNT162b2 UTR pair vs the deposited vaccine-batch plasmids (PP544446.1 /
    #     PP544445.1, Raoult direct submissions 2024) and the LinearDesign supplement
    sys.path.insert(0, str(PROJECT_ROOT))
    from agent_core.generation.utr_pool import load_utr_benchmarks  # noqa: E402
    bench = {e["id"]: e for e in load_utr_benchmarks()}
    b5 = bench["bnt162b2_5utr"]["sequence"]
    b3 = bench["bnt162b2_3utr"]["sequence"]
    vector = to_dna(_first_seq(REFS / "bnt_vector_PP544446.fasta"))
    vector2 = to_dna(_first_seq(REFS / "bnt_vector_PP544445.fasta"))
    interval = vector[3526:3577]   # asset source: between T7 promoter end (3526) and CDS start (3578)
    checks.append(("BNT 5'UTR (51 nt) == PP544446.1 interval 3527..3577 (batch FP9359)",
                   to_dna(b5) == interval, f"asset_len={len(b5)} interval_len={len(interval)}"))
    checks.append(("BNT 5'UTR (51 nt) also present verbatim in batch FP8191 plasmid PP544445.1",
                   vector2.count(to_dna(b5)) == 1, ""))
    checks.append(("BNT vector interval is followed by ATG (CDS start)", vector[3577:3580] == "ATG", ""))
    checks.append(("BNT 3'UTR not carried by the ORF-only batch plasmids (disclosed; insert = ORF subclone)",
                   to_dna(b3) not in vector and to_dna(b3) not in vector2,
                   "3'UTR verified against the LinearDesign supplement instead (below)"))

    # 5. BNT 3'UTR == LinearDesign supplement block (verbatim; must appear TWICE —
    #    COVID and VZV wet-lab sections — byte-identical; header uses U+2019 apostrophe)
    supp_pdf = RELEVANT_REFS / "Supplementary information Lineardesign.pdf"
    txt = subprocess.run(["pdftotext", "-layout", str(supp_pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    supp_blocks: list[str] = []
    lines = txt.splitlines()
    for idx, line in enumerate(lines):
        if line.strip().startswith(">") and "UTR" in line and "3" in line and "5" not in line:
            block = []
            for follow in lines[idx + 1: idx + 8]:
                s = follow.strip()
                if s and set(s.upper()) <= set("ACGTU"):
                    block.append(s.upper())
                else:
                    break
            if block:
                supp_blocks.append("".join(block))
    checks.append(("BNT 3'UTR == LinearDesign supplement 3'UTR blocks (2 occurrences, verbatim)",
                   len(supp_blocks) == 2 and all(x == b3 for x in supp_blocks),
                   f"blocks_found={len(supp_blocks)} lens={[len(x) for x in supp_blocks]}"))

    # 6. HBA1 cross-check (report-only): natural leader differs at the Kozak C->G
    hba1 = to_dna(_first_seq(REFS / "hba1_NM_000558.fasta"))
    core = "CTTCTGGTCCCCACAGACTCAGAGAGAACC"
    checks.append(("HBA1 NM_000558.5 mRNA contains the alpha-globin leader core (report)",
                   core in hba1, "BNT 5'UTR carries the GCCACCAUG Kozak optimization (Xia & Lim 2021)"))

    ok = all(c[1] for c in checks)
    report["checks"] = [{"name": n, "pass": p, "note": note} for n, p, note in checks]
    report["all_pass"] = ok
    # persist the verified WT CDS sequences (U-form, no stop)
    report["wt_cds"] = {
        "EPO": {"source": f"RefSeq {REFSEQ_MRNA['EPO']} CDS (GenBank record, exact-translation ORF, natural stop {epo_stop})",
                "sequence": to_rna(epo_cds_dna),
                "natural_stop": epo_stop},
        "HA": {"source": f"GenBank {acc} CDS located by exact-translation ORF search (strand {strand})",
               "sequence": to_rna(ha_wt_full[:-3]),
               "natural_stop": to_rna(ha_wt_full[-3:])},
    }
    report["utr_chassis"] = {"utr5": b5, "utr3": b3}
    write_json(OUT / "verification.json", report)
    for n, p, note in checks:
        log(f"{'PASS' if p else 'FAIL'}  {n}  {note}")
    if not ok:
        raise SystemExit("verification failed — see checks above")


# ── stage: lineardesign ──────────────────────────────────────────────────────

def stage_lineardesign() -> None:
    ver = json.loads((OUT / "verification.json").read_text())
    results = {}
    for prot in PROTEINS:
        prot_seq = load_target(prot)["protein_sequence"]
        cmd = ["./bin/LinearDesign_2D", "4", "0", "codon_usage_freq_table_human.csv"]
        proc = subprocess.run(cmd, cwd=LINEARDESIGN_DIR, input=prot_seq + "\n",
                              capture_output=True, text=True, timeout=3600)
        out = proc.stdout
        m_seq = re.search(r"mRNA sequence:\s*([ACGTUacgtu]+)", out)
        m_meta = re.search(r"mRNA folding free energy:\s*([-\d.]+) kcal/mol; mRNA CAI:\s*([\d.]+)", out)
        assert m_seq and m_meta, f"LinearDesign parse failure for {prot}: {out[-400:]}"
        cds = m_seq.group(1).upper()
        assert len(cds) == 3 * len(prot_seq), f"{prot}: CDS length {len(cds)} != {3 * len(prot_seq)}"
        assert translate(cds) == prot_seq, f"{prot}: LinearDesign CDS translation mismatch"
        results[prot] = {
            "cds": cds,  # U-form, no stop (algorithm output)
            "self_reported_mfe_kcal_mol": float(m_meta.group(1)),
            "self_reported_cai": float(m_meta.group(2)),
            "lambda": 4, "codon_table": "codon_usage_freq_table_human.csv",
            "binary": "external_repos/LinearDesign/bin/LinearDesign_2D.real (default beam)",
        }
        log(f"LinearDesign {prot}: len={len(cds)} selfMFE={m_meta.group(1)} selfCAI={m_meta.group(2)}")
    write_json(OUT / "lineardesign.json", results)


# ── stage: rnarl ─────────────────────────────────────────────────────────────

def _rnarl_ensure_service() -> None:
    import urllib.error
    try:
        with urllib.request.urlopen("http://127.0.0.1:8008/health", timeout=5) as r:
            if r.status == 200:
                log("RNARL service already up")
                return
    except urllib.error.URLError:
        pass
    env = os.environ.copy()
    env["RNADA_DEVICE"] = env.get("RNARL_DEVICE", "cuda:0")
    env["RNARL_DEVICE"] = env.get("RNARL_DEVICE", "cuda:0")
    logp = OUT / "rnarl_service.log"
    OUT.mkdir(parents=True, exist_ok=True)
    with logp.open("w") as fp:
        subprocess.Popen(["bash", str(RNARL_START)], stdout=fp, stderr=subprocess.STDOUT,
                         cwd=RNARL_START.parent, env=env)
    for _ in range(120):
        time.sleep(5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8008/health", timeout=5) as r:
                if r.status == 200:
                    log("RNARL service started")
                    return
        except urllib.error.URLError:
            continue
    raise SystemExit("RNARL service failed to start — see outputs/rnarl_service.log")


def stage_rnarl() -> None:
    import urllib.request
    _rnarl_ensure_service()
    results = {}
    for prot in PROTEINS:
        prot_seq = load_target(prot)["protein_sequence"]
        payload = json.dumps({
            "protein_sequence": prot_seq,
            "model_type": "Homo sapiens mRNA",
        }).encode()
        req = urllib.request.Request("http://127.0.0.1:8008/generate/cds", data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1800) as r:
            resp = json.loads(r.read())
        cds = to_rna(resp["generated_sequence"]).upper()
        cds_nostop = cds[:-3] if cds[-3:] in {"UAA", "UAG", "UGA"} else cds
        assert len(cds_nostop) == 3 * len(prot_seq), \
            f"{prot}: RNARL CDS length {len(cds_nostop)} != {3 * len(prot_seq)}"
        assert translate(cds_nostop) == prot_seq, f"{prot}: RNARL CDS translation mismatch"
        results[prot] = {
            "cds": cds_nostop,
            "model_type": "Homo sapiens mRNA",
            "checkpoint": resp.get("checkpoint_path"),
            "device": resp.get("device"),
        }
        log(f"RNARL {prot}: len={len(cds_nostop)} OK")
    write_json(OUT / "rnarl.json", results)


# ── stage: gemorna (standalone, GEMORNA-native only) ─────────────────────────

def _gemorna_python() -> str:
    base = subprocess.run(["conda", "info", "--base"], capture_output=True, text=True, check=True).stdout.strip()
    py = Path(base) / "envs" / "gemorna_service_env" / "bin" / "python"
    assert py.exists(), f"missing {py}"
    return str(py)


def _extract_longest_nt(stdout: str, min_length: int) -> str:
    pattern = rf"[ACGTUNacgtun]{{{min_length},}}"
    m = re.findall(pattern, stdout)
    if m:
        return max(m, key=len).upper().replace("T", "U")
    raise RuntimeError(f"cannot parse GEMORNA stdout: {stdout[-200:]}")


def _extract_pred_value(stdout: str) -> float:
    for line in reversed([l.strip() for l in stdout.splitlines() if l.strip()]):
        parts = line.split()
        try:
            return float(parts[-1])
        except ValueError:
            continue
    raise RuntimeError(f"cannot parse GEMORNA prediction stdout: {stdout[-200:]}")


def stage_gemorna() -> None:
    py = _gemorna_python()
    log(f"GEMORNA standalone via {py}")

    def run(args: list[str], timeout: int = 900) -> str:
        proc = subprocess.run([py] + args, cwd=GEMORNA_DIR, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"GEMORNA call failed: {proc.stderr[-400:]}")
        return proc.stdout

    # CDS draws per protein
    cds_pool: dict[str, list[dict[str, Any]]] = {}
    for prot in PROTEINS:
        prot_seq = load_target(prot)["protein_sequence"]
        pool = []
        for i in range(CDS_DRAWS_PER_PROTEIN):
            out = run(["src/generate.py", "--mode", "cds", "--ckpt_path", "checkpoints/gemorna_cds.pt",
                       "--protein_seq", prot_seq], timeout=1800)
            seq = _extract_longest_nt(out, 30)
            naturalness = None
            for line in out.splitlines():
                if to_rna(seq[:40])[:20] in to_rna(line):
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            naturalness = float(parts[-1])
                        except ValueError:
                            pass
                    break
            has_stop = seq[-3:] in {"UAA", "UAG", "UGA"}
            body = seq[:-3] if has_stop else seq
            exact = len(body) == 3 * len(prot_seq) and body.startswith("AUG") and translate(body) == prot_seq
            pool.append({"draw": i + 1, "sequence": seq, "length": len(seq),
                         "naturalness": naturalness, "exact_translation": bool(exact),
                         "ends_with_stop": bool(has_stop)})
            log(f"GEMORNA CDS {prot} draw{i + 1}: len={len(seq)} exact={exact} stop={has_stop}")
        cds_pool[prot] = pool

    # UTR pool draws (12 + 10), shared across proteins (generators are unconditioned)
    utr5_pool, utr3_pool = [], []
    for preset, n in UTR5_DRAWS.items():
        for i in range(n):
            out = run(["src/generate.py", "--mode", "5utr", "--ckpt_path", "checkpoints/gemorna_5utr.pt",
                       "--utr_length", preset])
            seq = _extract_longest_nt(out, 10)
            utr5_pool.append({"preset": preset, "draw": i + 1, "sequence": seq})
    for preset, n in UTR3_DRAWS.items():
        for i in range(n):
            out = run(["src/generate.py", "--mode", "3utr", "--ckpt_path", "checkpoints/gemorna_3utr.pt",
                       "--utr_length", preset])
            seq = _extract_longest_nt(out, 10)
            utr3_pool.append({"preset": preset, "draw": i + 1, "sequence": seq})
    log(f"GEMORNA UTR pool: {len(utr5_pool)} 5'UTR + {len(utr3_pool)} 3'UTR drawn")

    # predictor scoring (their own released models)
    for e in utr5_pool:
        out = run(["src/main_pred5UTR.py", "--ckpt_path", "checkpoints/5utr.pt", "--sequence", to_dna(e["sequence"])])
        e["pred_5utr_mrl"] = _extract_pred_value(out)
    for e in utr3_pool:
        out = run(["src/main_pred3UTR.py", "--ckpt_path", "checkpoints/3utr.pt", "--sequence", to_dna(e["sequence"])])
        e["pred_3utr_stability"] = _extract_pred_value(out)

    # CDS pick: exact-translation filter -> highest human CAI (platform Kazusa table as neutral metric)
    sys.path.insert(0, str(PROJECT_ROOT))
    from agent_core.sequence_utils import build_cai_weights, compute_cai  # noqa: E402
    from agent_core.tools import _load_builtin_codon_tables  # noqa: E402
    weights = build_cai_weights(_load_builtin_codon_tables()["Homo sapiens"])
    picks = {}
    for prot in PROTEINS:
        prot_seq = load_target(prot)["protein_sequence"]
        for e in cds_pool[prot]:
            body = e["sequence"][:-3] if e["sequence"][-3:] in {"UAA", "UAG", "UGA"} else e["sequence"]
            e["cai"] = round(compute_cai(body, weights)["cai_score"], 4)
        elig = [e for e in cds_pool[prot] if e["exact_translation"]]
        assert elig, f"{prot}: no GEMORNA CDS draw passed exact-translation filter"
        best = max(elig, key=lambda e: (e["cai"], -e["draw"]))
        picks[prot] = best["sequence"]
        log(f"GEMORNA CDS pick {prot}: draw{best['draw']} CAI={best['cai']}")

    best5 = max(utr5_pool, key=lambda e: e["pred_5utr_mrl"])
    best3 = max(utr3_pool, key=lambda e: e["pred_3utr_stability"])
    log(f"GEMORNA UTR picks: 5'UTR {best5['preset']}#{best5['draw']} MRL={best5['pred_5utr_mrl']}; "
        f"3'UTR {best3['preset']}#{best3['draw']} stability={best3['pred_3utr_stability']}")

    write_json(OUT / "gemorna.json", {
        "cds_pool": cds_pool,
        "utr5_pool": utr5_pool,
        "utr3_pool": utr3_pool,
        "picks": {"cds": picks,
                  "utr5": best5["sequence"], "utr5_preset": best5["preset"],
                  "utr3": best3["sequence"], "utr3_preset": best3["preset"]},
        "rule": ("pre-registered: 5 CDS draws -> exact-translation filter -> highest human CAI; "
                 "UTR pool 12+10 (GEMORNA paper screening scale, shared across proteins) -> "
                 "top PRED-5UTR MRL / top PRED-3UTR stability; all tools = GEMORNA repo "
                 "scripts under gemorna_service_env, zero platform components in the design path"),
    })


# ── stage: ours (platform full_length_mrna_design, rank-1 of one frozen run) ─

def _find_results_file(session_dir: Path) -> Optional[Path]:
    files = sorted(session_dir.glob("workflow_results_*.json"),
                   key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def stage_ours(target: str, *, reuse: bool = True) -> None:
    assert target in PROTEINS, target
    tgt = load_target(target)
    session = f"wetlab_ours_{target}"
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session
    session_dir.mkdir(parents=True, exist_ok=True)
    results_file = _find_results_file(session_dir)
    prot_seq = tgt["protein_sequence"]
    if reuse and results_file is not None:
        log(f"ours {target}: reusing frozen session result {results_file.name}")
        elapsed = 0.0
    else:
        params = {
            "protein_sequence": prot_seq,
            "cai_species": tgt.get("species_for_codon_optimization", "Homo sapiens"),
            "utr_mode": "all",
            # navigation deliberately UNSET -> platform default (object of this arm)
        }
        (session_dir / "params.json").write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
        env["RNADA_CAPGATE"] = "advisory"
        cmd = [sys.executable, str(PROJECT_ROOT / "cli" / "form_chat.py"),
               "--workflow", "full_length_mrna_design",
               "--params-file", str(session_dir / "params.json"),
               "--session-id", session]
        started = time.monotonic()
        with (session_dir / "driver.log").open("a", encoding="utf-8", errors="replace") as fp:
            proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, stdout=fp,
                                  stderr=subprocess.STDOUT, input="y\n", text=True)
        elapsed = time.monotonic() - started
        assert proc.returncode == 0, f"CLI run failed (exit={proc.returncode}), see {session_dir/'driver.log'}"
        results_file = _find_results_file(session_dir)
        assert results_file, "no results file"
    results = json.loads(results_file.read_text())
    assert results.get("success"), "workflow success=False"
    best = results["best_candidate"]
    md = best["metadata"]
    # metadata cds_sequence may be truncated for long CDSs; the authoritative
    # decomposition is full sequence + per-segment lengths (all archived)
    full = best["sequence"].upper()
    u5l, cl, u3l = md["utr5_length"], md["cds_length"], md["utr3_length"]
    assert u5l + cl + u3l == best["total_length"] == len(full), "segment lengths inconsistent"
    utr5, cds, utr3 = full[:u5l], full[u5l:u5l + cl], full[u5l + cl:]
    assert utr5 == md["utr5_sequence"].upper() and utr3 == md["utr3_sequence"].upper(), \
        "UTR metadata mismatch"
    assert cds.startswith("AUG") and translate(cds) == prot_seq, "ours: CDS translation mismatch"
    record = {
        "target": target, "session_id": session, "wall_seconds": round(elapsed, 1),
        "rank": best.get("rank"), "cds_source": md.get("cds_source"),
        "utr5_origin": md.get("utr5_origin"), "utr3_origin": md.get("utr3_origin"),
        "utr5_preset": md.get("utr5_preset"), "utr3_preset": md.get("utr3_preset"),
        "utr5": utr5, "cds": cds, "utr3": utr3,
        "full_sequence": full,
        "asf_distance": (best.get("scores") or {}).get("asf_distance"),
        "scores": best.get("scores"),
        "n_candidates": len(results.get("candidates") or []),
        "results_file": str(results_file),
    }
    write_json(OUT / f"ours_{target}.json", record)
    log(f"ours {target}: wall={elapsed:.0f}s candidates={record['n_candidates']} "
        f"cds_source={record['cds_source']} presets={record['utr5_preset']}/{record['utr3_preset']}")


# ── stage: metrics ───────────────────────────────────────────────────────────

def _rnafold_mfe(seq: str) -> float:
    proc = subprocess.run(["RNAfold", "--noPS"], input=to_rna(seq) + "\n",
                          capture_output=True, text=True, timeout=1800)
    m = re.search(r"\(\s*(-?\d+\.\d+)\s*\)", proc.stdout)
    assert m, f"RNAfold parse failure: {proc.stdout[:200]}"
    return float(m.group(1))


def _pred5utr(py: str, seq: str) -> float:
    out = subprocess.run([py, "src/main_pred5UTR.py", "--ckpt_path", "checkpoints/5utr.pt",
                          "--sequence", to_dna(seq)], cwd=GEMORNA_DIR, capture_output=True,
                         text=True, timeout=600).stdout
    return _extract_pred_value(out)


def _pred3utr(py: str, seq: str) -> float:
    out = subprocess.run([py, "src/main_pred3UTR.py", "--ckpt_path", "checkpoints/3utr.pt",
                          "--sequence", to_dna(seq)], cwd=GEMORNA_DIR, capture_output=True,
                         text=True, timeout=600).stdout
    return _extract_pred_value(out)


def stage_metrics() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from agent_core.sequence_utils import build_cai_weights, compute_cai  # noqa: E402
    from agent_core.tools import _load_builtin_codon_tables  # noqa: E402
    from agent_core.generation.utr_pool import (  # noqa: E402  (report-only diagnostics)
        utr5_has_upstream_aug, utr3_are_class2, utr3_are_auuua_count)
    weights = build_cai_weights(_load_builtin_codon_tables()["Homo sapiens"])
    py = _gemorna_python()

    ver = json.loads((OUT / "verification.json").read_text())
    ld = json.loads((OUT / "lineardesign.json").read_text())
    rl = json.loads((OUT / "rnarl.json").read_text())
    gm = json.loads((OUT / "gemorna.json").read_text())
    chassis = ver["utr_chassis"]

    constructs = []
    mrl_cache: dict[str, float] = {}
    utr3_cache: dict[str, float] = {}
    for prot in PROTEINS:
        tgt = load_target(prot)
        prot_seq = tgt["protein_sequence"]
        ours = json.loads((OUT / f"ours_{prot}.json").read_text())
        arms = [
            ("WT", ver["wt_cds"][prot]["sequence"], chassis["utr5"], chassis["utr3"],
             ver["wt_cds"][prot]["source"]),
            ("LinearDesign_lambda4", ld[prot]["cds"], chassis["utr5"], chassis["utr3"],
             f"LinearDesign binary lambda=4 human table (self MFE {ld[prot]['self_reported_mfe_kcal_mol']}, "
             f"self CAI {ld[prot]['self_reported_cai']})"),
            ("RNARL", rl[prot]["cds"], chassis["utr5"], chassis["utr3"],
             f"RNARL actor ({rl[prot]['model_type']}, {Path(rl[prot]['checkpoint']).name})"),
            ("GEMORNA", gm["picks"]["cds"][prot], gm["picks"]["utr5"], gm["picks"]["utr3"],
             f"GEMORNA standalone; 5'UTR {gm['picks']['utr5_preset']}-preset top PRED-5UTR, "
             f"3'UTR {gm['picks']['utr3_preset']}-preset top PRED-3UTR, CDS top-CAI of 5 draws"),
            ("Ours_platform_rank1", ours["cds"], ours["utr5"], ours["utr3"],
             f"full_length_mrna_design rank-1 ({ours['cds_source']}; "
             f"5'UTR {ours['utr5_origin']}/{ours['utr5_preset']}, "
             f"3'UTR {ours['utr3_origin']}/{ours['utr3_preset']}, "
             f"session {ours['session_id']})"),
        ]
        for arm, cds, u5, u3, note in arms:
            body = cds[:-3] if cds[-3:] in {"UAA", "UAG", "UGA"} else cds
            assert len(body) == 3 * len(prot_seq), f"{prot}/{arm}: CDS body length mismatch"
            assert translate(body) == prot_seq, f"{prot}/{arm}: translation mismatch"
            assert cds[-3:] not in {"UAA", "UAG", "UGA"}, \
                f"{prot}/{arm}: stored CDS unexpectedly ends in a stop codon (single appended stop is added at assembly)"
            full = u5 + cds + u3   # cds carries the single appended UGA (WT keeps natural stop)
            if arm != "WT":
                full = u5 + body + "UGA" + u3
                cds_ship = body + "UGA"
            else:
                natural = ver["wt_cds"][prot].get("natural_stop", "UGA")
                full = u5 + body + natural + u3
                cds_ship = body + natural
            if u5 not in mrl_cache:
                mrl_cache[u5] = _pred5utr(py, u5)
            if u3 not in utr3_cache:
                utr3_cache[u3] = _pred3utr(py, u3)
            constructs.append({
                "protein": prot, "protein_accession": tgt["accession"], "arm": arm,
                "protein_sequence": prot_seq, "protein_length_aa": len(prot_seq),
                "utr5_sequence": u5, "utr5_length": len(u5),
                "cds_sequence_with_stop": cds_ship, "cds_length_with_stop": len(cds_ship),
                "cds_sequence_coding": body, "cds_length_coding": len(body),
                "utr3_sequence": u3, "utr3_length": len(u3),
                "full_sequence": full, "full_length": len(full),
                "cai_human": round(compute_cai(body, weights)["cai_score"], 4),
                "mfe_full_kcal_mol": _rnafold_mfe(full),
                "mfe_cds_kcal_mol": _rnafold_mfe(body),
                "gc_full_percent": gc_percent(full),
                "gc_cds_percent": gc_percent(body),
                "utr5_pred_mrl_gemorna": mrl_cache[u5],
                "utr3_pred_stability_gemorna": utr3_cache[u3],
                "utr5_has_upstream_aug": utr5_has_upstream_aug(u5),
                "utr3_are_class2": utr3_are_class2(u3),
                "utr3_are_auuua_count": utr3_are_auuua_count(u3),
                "provenance": note,
            })
            log(f"metrics {prot}/{arm}: CAI={constructs[-1]['cai_human']} "
                f"MFE_full={constructs[-1]['mfe_full_kcal_mol']} MFE_cds={constructs[-1]['mfe_cds_kcal_mol']}")
    write_json(OUT / "constructs_metrics.json", {"constructs": constructs,
                                                 "mfe_tool": "ViennaRNA RNAfold (system binary, 37 C)",
                                                 "cai_source": "Kazusa human table, Sharp&Li weights (platform sequence_utils)",
                                                 "mrl_utr5": "GEMORNA PRED-5UTR (their released checkpoint)",
                                                 "utr3_stability": "GEMORNA PRED-3UTR (their released checkpoint)"})


# ── stage: xlsx ──────────────────────────────────────────────────────────────

def stage_xlsx() -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    data = json.loads((OUT / "constructs_metrics.json").read_text())
    ver = json.loads((OUT / "verification.json").read_text())
    gm = json.loads((OUT / "gemorna.json").read_text())
    constructs = data["constructs"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "构建总表"
    headers = [
        "蛋白", "方法(臂)", "蛋白accession", "氨基酸序列", "氨基酸长度",
        "5'UTR序列", "5'UTR长度", "CDS序列(含终止码, RNA)", "CDS长度(含终止码)",
        "3'UTR序列", "3'UTR长度", "全长序列(5UTR+CDS+3UTR)", "全长长度",
        "CAI(人)", "MFE-全长(kcal/mol)", "MFE-CDS(kcal/mol)",
        "GC%-全长", "GC%-CDS", "5'UTR预测MRL(GEMORNA PRED-5UTR)",
        "3'UTR稳定性评分(GEMORNA PRED-3UTR)", "5'UTR含uAUG(诊断)",
        "3'UTR II类ARE(诊断)", "3'UTR散在AUUUA数(诊断)", "来源/选择规则",
    ]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in constructs:
        ws.append([
            row["protein"], row["arm"], row["protein_accession"],
            row["protein_sequence"], row["protein_length_aa"],
            row["utr5_sequence"], row["utr5_length"],
            row["cds_sequence_with_stop"], row["cds_length_with_stop"],
            row["utr3_sequence"], row["utr3_length"],
            row["full_sequence"], row["full_length"],
            row["cai_human"], row["mfe_full_kcal_mol"], row["mfe_cds_kcal_mol"],
            row["gc_full_percent"], row["gc_cds_percent"],
            row["utr5_pred_mrl_gemorna"], row["utr3_pred_stability_gemorna"],
            "是" if row["utr5_has_upstream_aug"] else "否",
            "是" if row["utr3_are_class2"] else "否",
            row["utr3_are_auuua_count"],
            row["provenance"],
        ])
    widths = [8, 22, 14, 52, 10, 60, 10, 90, 12, 60, 10, 110, 10, 9, 12, 12, 10, 10, 14, 14, 12, 12, 12, 60]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).alignment = Alignment(vertical="top", wrap_text=(c in (4, 6, 8, 10, 12, 24)))
    ws.freeze_panes = "D2"

    ws2 = wb.create_sheet("验证与溯源")
    ws2.append(["验证项", "结果", "备注"])
    for c in ws2[1]:
        c.font = Font(bold=True)
    for chk in ver["checks"]:
        ws2.append([chk["name"], "PASS" if chk["pass"] else "FAIL", chk["note"]])
    ws2.append([])
    ws2.append(["约定", "说明"])
    ws2.append(["CDS 终止码", "所有臂统一单终止码（设计方法输出不带终止的统一补 UGA；WT 用天然终止码）"])
    ws2.append(["CDS 指标口径", "CAI / MFE-CDS / GC%-CDS 按编码区（不含终止码，3N nt）计算"])
    ws2.append(["全长指标口径", "MFE-全长 / GC%-全长 按 5'UTR+CDS(含终止码)+3'UTR 计算；不含 poly(A) 尾与帽"])
    ws2.append(["湿实验拼接", "加尾/加帽/修饰核苷酸由湿实验统一处理（十臂一致）"])
    ws2.append(["HA 毒株", "A/Puerto Rico/8/1934 (H1N1), UniProt P03452 / GenBank ABD77675.1 (segment CY009444), 565 aa"])
    ws2.append(["HA 引用修正", "靶点资产原 ncbi_reference=AAL09324.1 有误（解析为狒狒 duffy 抗原），本批次已修正为 ABD77675.1（与 UniProt P03452 逐残基一致；蛋白序列本身未变）"])
    ws2.append(["HA 变体披露", "PR8 有两个常用谱系：本表 565 aa = Mount Sinai 谱系（UniProt P03452 / CY009444，即 Hoffmann-Webster 反向遗传学体系、商品化 PR8 HA 试剂与近期晶体结构所用谱系）；RefSeq NC_002017.1 = V01088 = Winter 1981 经典测序谱系（566 aa），与前者仅差 8 个 HA1 残基（TK146-147N 即 1-aa 缺失+替换，E155A/P199S/E203D/L207I/M268R/Y308F/T397S，98.6% 一致）——565/566 的疑问即源于此，已披露不采用"])
    ws2.append(["EPO 参考版本", "UniProt P01588 (193 aa) = 靶点资产 = RefSeq NM_000799.4 CDS 翻译（WT CDS 取自该记录，天然终止码 UGA）"])
    ws2.append(["BNT162b2 底盘", f"5'UTR 51 nt (PP544446.1:3527-3577) + 3'UTR 94 nt (AES-mtRNR1, LinearDesign 补充材料逐字)"])
    ws2.append(["MRL/稳定性指标", "GEMORNA 自家 PRED-5UTR/PRED-3UTR checkpoint（与其基线臂选择同一模型，全臂统一）"])
    for i, w in enumerate([70, 10, 80], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    ws3 = wb.create_sheet("GEMORNA池明细")
    ws3.append(["类别", "蛋白/预设", "draw", "序列", "长度", "exact_translation",
                "CAI(人)", "PRED-5UTR MRL", "PRED-3UTR稳定性", "是否选中"])
    for c in ws3[1]:
        c.font = Font(bold=True)
    for prot, pool in gm["cds_pool"].items():
        for e in pool:
            ws3.append(["CDS", prot, e["draw"], e["sequence"], e["length"],
                        e["exact_translation"], e.get("cai"), None, None,
                        "YES" if gm["picks"]["cds"][prot] == e["sequence"] else ""])
    for e in gm["utr5_pool"]:
        ws3.append(["5'UTR", e["preset"], e["draw"], e["sequence"], len(e["sequence"]),
                    None, None, e["pred_5utr_mrl"], None,
                    "YES" if gm["picks"]["utr5"] == e["sequence"] else ""])
    for e in gm["utr3_pool"]:
        ws3.append(["3'UTR", e["preset"], e["draw"], e["sequence"], len(e["sequence"]),
                    None, None, None, e["pred_3utr_stability"],
                    "YES" if gm["picks"]["utr3"] == e["sequence"] else ""])
    for i, w in enumerate([8, 10, 6, 100, 8, 14, 9, 14, 16, 9], start=1):
        ws3.column_dimensions[get_column_letter(i)].width = w

    out_path = OUT / "wetlab_batch_EPO_HA.xlsx"
    wb.save(out_path)
    log(f"xlsx written: {out_path}")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["fetch_refs", "verify", "lineardesign", "rnarl", "gemorna",
                             "ours", "metrics", "xlsx"])
    ap.add_argument("--target", default="all", choices=["EPO", "HA", "all"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.stage == "fetch_refs":
        stage_fetch_refs()
    elif args.stage == "verify":
        stage_verify()
    elif args.stage == "lineardesign":
        stage_lineardesign()
    elif args.stage == "rnarl":
        stage_rnarl()
    elif args.stage == "gemorna":
        stage_gemorna()
    elif args.stage == "ours":
        targets = PROTEINS if args.target == "all" else [args.target]
        for t in targets:
            stage_ours(t)
    elif args.stage == "metrics":
        stage_metrics()
    elif args.stage == "xlsx":
        stage_xlsx()


if __name__ == "__main__":
    main()
