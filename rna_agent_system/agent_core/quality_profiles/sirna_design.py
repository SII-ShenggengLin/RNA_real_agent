"""QualityProfile for sirna_design workflow."""

from __future__ import annotations

from agent_core.agents.quality_agent import QualityProfile

SIRNA_QUALITY_PROFILE = QualityProfile(
    workflow_name="sirna_design",
    workflow_description="Design siRNA candidates for gene silencing",
    evaluation_dimensions=[
        "Duplex MFE (RNAcofold): more negative = more stable duplex. Very positive values indicate poor binding.",
        "Off-target count should be minimal. High off-target counts reduce specificity and increase toxicity.",
        "GC content: the workflow already filters candidates to [mingc, maxgc] (defaults 0.25-0.60). Flag values outside the user's requested range; as a heuristic, ~30-60% GC balances duplex stability against specificity (very high GC raises off-target risk, very low GC weakens duplex stability).",
        "Consecutive homopolymers (>3 identical bases) should be avoided as they can cause non-specific effects.",
        "For antiviral mode: Evitar predicted efficiency should be high.",
    ],
    adjustable_params={
        "mode": {
            "type": "enum",
            "values": ["antiviral", "generic"],
            "hint": "Switch between antiviral (uses Evitar) and generic (sliding window) modes.",
        },
        "candidate_count": {
            "type": "int",
            "min": 1,
            "max": 100,
            "hint": "Number of candidates to generate. Increase if too few survive filtering.",
        },
        "maxgc": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Maximum GC content filter. Lower if candidates have too-high GC.",
        },
        "mingc": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Minimum GC content filter. Raise if candidates have too-low GC.",
        },
        "off_target_scan": {
            "type": "bool",
            "hint": "Whether to run the transcriptome off-target scan (bowtie2 by default). Keep True unless it's failing.",
        },
        "blast_perc_identity": {
            "type": "float",
            "min": 70.0,
            "max": 100.0,
            "hint": "BLAST minimum percent-identity filter (only used when alignment_tool='blast'). Higher = stricter off-target filtering (fewer alignments reported); lower = looser (more matches).",
        },
        "alignment_tool": {
            "type": "enum",
            "values": ["blast", "bowtie2"],
            "hint": "Switch between BLAST (legacy, slower) and Bowtie2 (default, faster) off-target scan engines.",
        },
        "bowtie2_score_min": {
            "type": "str",
            "hint": "Bowtie2 --score-min function (only used when alignment_tool='bowtie2'). Default G,10,4 allows ~2 mismatches in 21 nt. Tighten (e.g. G,20,8) for stricter filtering.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)
