"""Tests for shuffle_cds_junction_codons tool."""

from __future__ import annotations

import pytest

from agent_core.file_manager import save_sequence
from agent_core.tools import shuffle_cds_junction_codons


# A simple 30-codon CDS (90 nt) with mix of amino acids
_SIMPLE_CDS = (
    "AUG"      # M
    "GGG"      # G
    "UUU"      # F
    "AUG"      # M
    "CCG"      # P
    "UUU"      # F
    "AUG"      # M
    "GGC"      # G
    "UUU"      # F
    "AUG"      # M
    "CCU"      # P
    "UUU"      # F
    "AUG"      # M
    "GGU"      # G
    "UUU"      # F
    "AUG"      # M
    "CCC"      # P
    "UUU"      # F
    "AUG"      # M
    "GGA"      # G
    "UUU"      # F
    "AUG"      # M
    "CCA"      # P
    "UUU"      # F
    "AUG"      # M
    "GGG"      # G
    "UUU"      # F
    "AUG"      # M
    "CCG"      # P
    "UUU"      # F
)


class TestShuffleCdsJunctionCodons:
    def test_n_terminus_shuffle_produces_variants(self):
        fp = save_sequence(_SIMPLE_CDS, prefix="test_shuffle_n")
        result = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "n_terminus",
                "codon_count": 6,
                "num_variants": 4,
                "species": "human",
                "seed": 42,
            }
        )
        assert result["original_sequence"] == _SIMPLE_CDS
        assert result["junction_end"] == "n_terminus"
        assert result["shuffled_region_start"] == 0
        assert result["shuffled_region_end"] == 6
        assert len(result["variants"]) > 0
        assert len(result["variants"]) <= 4
        # Each variant should have a CAI score
        for v in result["variants"]:
            assert "sequence" in v
            assert "cai_score" in v
            assert 0.0 < v["cai_score"] <= 1.0
            assert v["sequence"] != _SIMPLE_CDS
            # Length must be preserved
            assert len(v["sequence"]) == len(_SIMPLE_CDS)
            # At least one codon should have changed
            assert v["changed_codons"] > 0
            assert len(v["changes"]) == v["changed_codons"]

    def test_c_terminus_shuffle_produces_variants(self):
        fp = save_sequence(_SIMPLE_CDS, prefix="test_shuffle_c")
        result = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "c_terminus",
                "codon_count": 6,
                "num_variants": 4,
                "species": "human",
                "seed": 42,
            }
        )
        assert result["junction_end"] == "c_terminus"
        total_codons = len(_SIMPLE_CDS) // 3
        assert result["shuffled_region_start"] == total_codons - 6
        assert result["shuffled_region_end"] == total_codons
        assert len(result["variants"]) > 0

    def test_seed_reproducibility(self):
        fp = save_sequence(_SIMPLE_CDS, prefix="test_shuffle_seed")
        result1 = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "n_terminus",
                "codon_count": 6,
                "num_variants": 4,
                "species": "human",
                "seed": 123,
            }
        )
        result2 = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "n_terminus",
                "codon_count": 6,
                "num_variants": 4,
                "species": "human",
                "seed": 123,
            }
        )
        # Same seed should produce same variants
        seqs1 = [v["sequence"] for v in result1["variants"]]
        seqs2 = [v["sequence"] for v in result2["variants"]]
        assert seqs1 == seqs2

    def test_different_seed_produces_different_variants(self):
        fp = save_sequence(_SIMPLE_CDS, prefix="test_shuffle_seed2")
        result1 = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "n_terminus",
                "codon_count": 6,
                "num_variants": 4,
                "species": "human",
                "seed": 123,
            }
        )
        result2 = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "n_terminus",
                "codon_count": 6,
                "num_variants": 4,
                "species": "human",
                "seed": 456,
            }
        )
        seqs1 = [v["sequence"] for v in result1["variants"]]
        seqs2 = [v["sequence"] for v in result2["variants"]]
        # Different seeds may or may not overlap, but likely different
        assert seqs1 != seqs2

    def test_invalid_junction_end_raises(self):
        fp = save_sequence(_SIMPLE_CDS, prefix="test_shuffle_bad")
        with pytest.raises(ValueError, match="junction_end must be"):
            shuffle_cds_junction_codons.invoke(
                {
                    "filepath": fp,
                    "junction_end": "middle",
                    "codon_count": 6,
                    "num_variants": 4,
                    "species": "human",
                }
            )

    def test_codon_count_larger_than_cds(self):
        """Should clamp codon_count to total codons."""
        short_cds = "AUGGGGUUU"  # 3 codons
        fp = save_sequence(short_cds, prefix="test_shuffle_short")
        result = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "n_terminus",
                "codon_count": 10,  # larger than 3
                "num_variants": 4,
                "species": "human",
                "seed": 42,
            }
        )
        assert result["shuffled_region_end"] == 3  # clamped to total codons

    def test_variants_sorted_by_cai_descending(self):
        fp = save_sequence(_SIMPLE_CDS, prefix="test_shuffle_sort")
        result = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "n_terminus",
                "codon_count": 6,
                "num_variants": 8,
                "species": "human",
                "seed": 42,
            }
        )
        cai_scores = [v["cai_score"] for v in result["variants"]]
        assert cai_scores == sorted(cai_scores, reverse=True)

    def test_amino_acid_sequence_preserved(self):
        """Verify synonymous substitution keeps the same protein sequence."""
        fp = save_sequence(_SIMPLE_CDS, prefix="test_shuffle_aa")

        # Build a simple codon->aa lookup from the tool's internal data
        from agent_core.sequence_utils import _load_builtin_codon_tables

        tables = _load_builtin_codon_tables()
        hs = tables["Homo sapiens"]
        codon_to_aa = {c: info["aa"] for c, info in hs.items()}

        def translate(seq: str) -> str:
            return "".join(codon_to_aa.get(seq[i : i + 3], "?") for i in range(0, len(seq), 3))

        original_protein = translate(_SIMPLE_CDS)

        result = shuffle_cds_junction_codons.invoke(
            {
                "filepath": fp,
                "junction_end": "n_terminus",
                "codon_count": 6,
                "num_variants": 4,
                "species": "human",
                "seed": 42,
            }
        )
        for v in result["variants"]:
            variant_protein = translate(v["sequence"])
            assert variant_protein == original_protein
