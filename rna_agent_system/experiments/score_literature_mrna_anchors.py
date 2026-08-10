#!/usr/bin/env python3
"""Fig 3f / 7A: score literature mRNA anchors with the RNADesignAgent metric suite.

Implements `docs/MANUSCRIPT.md` §5.3. For each anchor (BNT162b2, mRNA-1273,
wild-type Spike CDS) the script computes the same metrics the full-length
workflow reports:

- CDS: GC content, CAI (human), LinearFold MFE (+ MFE/nt)
- 5'UTR: GEMORNA predicted MRL
- 3'UTR: GEMORNA predicted stability
- Full concatenation: ViennaRNA fold → full-length MFE/nt, AUG start-codon and
  Kozak-context burial flags from the dot-bracket at the CDS start

Tools are called through `agent_core.tools.<fn>.func` (same code paths the
workflows use: local metric tools + LinearFold/ViennaRNA/GEMORNA services).
Vaccine contigs are split into 5'UTR / CDS (3822 nt spike) / 3'UTR at the
GCCACC Kozak motif; the split is validated against the spike reading frame.

Output: `experiments/results/fig3_anchors.json`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/score_literature_mrna_anchors.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_core.tools import (  # noqa: E402
    compute_cai_for_cds_sequence,
    compute_rna_sequence_gc_content,
    predict_3utr_stability_with_gemorna,
    predict_5utr_mrl_with_gemorna,
    predict_rna_secondary_structure,
    predict_rna_secondary_structure_with_linearfold,
)

ANCHORS = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors"
WORK = PROJECT_ROOT / "workspace" / "fig3_anchor_scoring"
SPIKE_CDS_NT = 3822  # 1273 aa + stop
OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig3_anchors.json"


def read_fasta(path: Path) -> str:
    return "".join(
        l.strip() for l in path.read_text().splitlines() if not l.startswith(">")
    ).upper()


def split_vaccine_mrna(seq: str) -> tuple[str, str, str]:
    """Split a vaccine contig into (5'UTR, CDS, 3'UTR) at the GCCACC Kozak motif."""
    kozak = seq.find("GCCACCATG")
    if kozak == -1:
        raise ValueError("GCCACCATG not found — cannot split vaccine contig")
    atg = kozak + 6
    cds = seq[atg : atg + SPIKE_CDS_NT]
    if len(cds) != SPIKE_CDS_NT:
        raise ValueError(f"contig too short for spike CDS: got {len(cds)} nt")
    if cds[-3:] not in ("TAA", "TAG", "TGA"):
        raise ValueError(f"CDS does not end in a stop codon: ...{cds[-9:]}")
    if cds[:9] != "ATGTTCGTG":
        raise ValueError(f"CDS does not start like spike (ATG TTC GTG): {cds[:12]}")
    return seq[:atg], cds, seq[atg + SPIKE_CDS_NT :]


def write_seq(name: str, seq: str) -> str:
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / f"{name}.fa"
    p.write_text(f">{name}\n{seq}\n", encoding="utf-8")
    return str(p.relative_to(PROJECT_ROOT))


def _gc(seq: str) -> float:
    return (seq.upper().count("G") + seq.upper().count("C")) / len(seq) if seq else 0.0


def junction_metrics(name: str, jname: str, left: str, right: str) -> dict:
    """Mirror `JunctionEvaluator` semantics: fold left+right with LinearFold and
    check AUG/Kozak burial at the boundary (offset = len(left)).

    AUG buried = any of the 3 start-codon nucleotides paired;
    Kozak buried = any nucleotide in [aug-4, aug+4) paired.
    """
    seq = left + right
    fold = predict_rna_secondary_structure_with_linearfold.func(filepath=write_seq(name, seq))
    structure = fold["structure"]
    aug_pos = len(left)
    out = {
        "mfe_kcal_per_mol": fold["mfe"],
        "mfe_per_nt": round(fold["mfe"] / len(seq), 4),
        "gc_diff": round(_gc(left) - _gc(right), 4),
        "length": len(seq),
    }
    if jname == "junction_5utr_cds" and seq[aug_pos : aug_pos + 3] == "ATG":
        aug_struct = structure[aug_pos : aug_pos + 3]
        kozak_struct = structure[max(0, aug_pos - 4) : min(len(seq), aug_pos + 4)]
        out["aug_buried"] = any(c in "()" for c in aug_struct)
        out["kozak_buried"] = any(c in "()" for c in kozak_struct)
    return out


def score_anchor(name: str, utr5: str, cds: str, utr3: str, atg_offset: int) -> dict:
    out: dict = {"anchor": name, "lengths": {"utr5": len(utr5), "cds": len(cds), "utr3": len(utr3)}}

    cds_path = write_seq(f"{name}_cds", cds)
    out["cds"] = {
        "gc_content": compute_rna_sequence_gc_content.func(filepath=cds_path)["gc_content"],
        "cai_score": compute_cai_for_cds_sequence.func(filepath=cds_path, species="human")["cai_score"],
    }
    lf = predict_rna_secondary_structure_with_linearfold.func(filepath=cds_path)
    out["cds"]["mfe_kcal_per_mol"] = lf["mfe"]
    out["cds"]["mfe_per_nt"] = round(lf["mfe"] / len(cds), 4)

    if utr5:
        mrl = predict_5utr_mrl_with_gemorna.func(filepath=write_seq(f"{name}_utr5", utr5))
        out["utr5"] = {"predicted_mrl": mrl["predicted_mrl"]}
    if utr3:
        stab = predict_3utr_stability_with_gemorna.func(filepath=write_seq(f"{name}_utr3", utr3))
        out["utr3"] = {"predicted_stability": stab["predicted_stability"]}

    full = utr5 + cds + utr3
    fold = predict_rna_secondary_structure.func(filepath=write_seq(f"{name}_full", full))
    out["full_length"] = {
        "mfe_kcal_per_mol": fold["mfe_kcal_per_mol"],
        "mfe_per_nt": round(fold["mfe_kcal_per_mol"] / len(full), 4),
        "fold_backend": fold.get("backend") or fold.get("model"),
    }

    if utr5 and len(utr5) >= 20 and len(cds) >= 20:
        out["junction_5utr_cds"] = junction_metrics(
            f"{name}_j1", "junction_5utr_cds", utr5[-20:], cds[:20])
    if utr3 and len(cds) >= 20 and len(utr3) >= 20:
        out["junction_cds_3utr"] = junction_metrics(
            f"{name}_j2", "junction_cds_3utr", cds[-20:], utr3[:20])
    j1 = out.get("junction_5utr_cds", {})
    print(f"  {name}: done (cds_cai={out['cds']['cai_score']:.3f}, "
          f"full_mfe/nt={out['full_length']['mfe_per_nt']}, "
          f"aug_buried={j1.get('aug_buried')})", flush=True)
    return out


def main() -> int:
    anchors: dict[str, dict] = {}

    for name, fasta in [("bnt162b2", "vaccine_mrna/bnt162b2_full.fa"),
                        ("mrna1273", "vaccine_mrna/mrna1273_full.fa")]:
        seq = read_fasta(ANCHORS / fasta)
        utr5, cds, utr3 = split_vaccine_mrna(seq)
        anchors[name] = score_anchor(name, utr5, cds, utr3, atg_offset=len(utr5))

    wt = read_fasta(ANCHORS / "wt_cds" / "SARS-CoV-2_Spike_WT.fa")
    anchors["wt_spike_cds"] = score_anchor("wt_spike_cds", "", wt, "", atg_offset=0)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(anchors, ensure_ascii=False, indent=2) + "\n")
    print(f"\n-> {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
