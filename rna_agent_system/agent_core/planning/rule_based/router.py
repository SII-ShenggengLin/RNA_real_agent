"""Deterministic keyword-based router (extracted from ``nodes.py`` router_node)."""

from __future__ import annotations

from typing import Literal

from agent_core.planning.base import AgentContext

from agent_core.planning.rule_based.parsers.common import (
    _needs_blast_search,
    _needs_crispr_mode,
    _needs_evitar_mode,
    _needs_iresfinder_prediction,
    _needs_rna_gc_content_metric,
    _needs_sirna_duplex_vienna,
)


class RuleBasedRouter:
    """Keyword-based dispatch to a specialist domain.

    This is a pure refactor of ``router_node`` logic.  It does **not**
    mutate state; it only returns a routing decision.
    """

    def classify(self, user_text: str, _ctx: AgentContext | None = None) -> Literal[
        "sirna_specialist",
        "mrna_specialist",
        "crispr_specialist",
        "unsupported",
    ]:
        lowered = user_text.lower()
        if _needs_crispr_mode(lowered):
            return "crispr_specialist"
        if _needs_evitar_mode(lowered):
            return "sirna_specialist"
        if _needs_iresfinder_prediction(lowered) or _needs_blast_search(lowered) or any(
            k in lowered
            for k in [
                "mrna",
                "rnafold",
                "fold",
                "structure",
                "tertiary",
                "3d",
                "三级结构",
                "三维结构",
                "rhofold",
                "rhodesign",
                "ribodiffusion",
                "ribo diffusion",
                "二级结构",
                "密码子",
                "codon",
                "codonw",
                "codonw-slim",
                "codon bias",
                "design",
                "设计",
                "gemorna",
                "rnarl",
                "lineardesign",
                "linear design",
                "linearfold",
                "pdb",
                "cif",
                "protein",
                "cds",
                "utr",
                "rnasmol",
                "rnastop",
                "stability",
                "degradation",
                "稳定性",
                "降解",
                "smiles",
                "ligand",
                "配体",
                "gernabind",
                "gerna-bind",
                "odesign",
                "aptamer",
                "适配体",
                "核酸适配体",
                "iresfinder",
                "internal ribosome",
                "aso",
                "gapmer",
                "morpholino",
                "accessibility",
                "可及性",
                "plfold",
                "rnaplfold",
                "lunp",
                "局部结构",
                "local structure",
                "local folding",
                "sliding window",
                "滑动窗口",
                "inverse fold",
                "逆折叠",
                "rnainverse",
                "gc content",
                "gc含量",
                "unpaired fraction",
                "未配对比例",
                "dot-bracket",
                "dot bracket",
            ]
        ):
            return "mrna_specialist"
        if _needs_sirna_duplex_vienna(lowered):
            return "sirna_specialist"
        if any(k in lowered for k in ["sirna", "脱靶", "off-target"]):
            return "unsupported"
        # Default to mRNA for current integration testing focus (RNAfold).
        return "mrna_specialist"
