"""2026-08-21 Layer-0 audit fixes — regression coverage.

Four defects found by the fresh-data tool audit (workspace/tool_layer_audit_
2026-08-21/; 41 production tools exercised on inputs created the same day):

1. ``analyze_rna_protein_interface`` computed buried SASA as (sum of the two
   selected chains' areas) − (whole-file SASA), which is <= 0 for any PDB
   containing extra chains (waters, ions, crystal copies) — a real 3-copy
   complex reported buried_sasa = 0.0. Its salt-bridge detector paired
   protein ARG/LYS/HIS against protein ASP/GLU, a combination that can never
   occur across a protein-RNA interface (always 0).
2. ``extract_rna_sequence_from_cif`` documented "non-standard nucleotides are
   rendered as N with a warning" but skipped hetero-flagged residues — and in
   mmCIF every modified nucleotide is hetero, so real structures came back
   silently shortened and position-shifted.
3. ``predict_rna_protein_complex_with_proteinx`` read only the LAST line of
   each FASTA, truncating every wrapped (>60 col) sequence.
4. CRISOT ``/spec`` accepted rows of any length (scored 20-nt spacers
   silently) while ``/score`` enforced 23 nt — server-side validation now
   mirrors /score (covered by the audit's negative control, not here).

The interface analysis and CIF fixes are locked interfaces; signatures and
return keys are unchanged — only the computations inside became correct.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_core import tools as T

# ---------------------------------------------------------------------------
# 1. analyze_rna_protein_interface: buried SASA on multi-chain PDB + salt bridges
# ---------------------------------------------------------------------------

_PDB = """\
ATOM      1  N   LYS A   1      10.000  10.000  10.000  1.00 20.00           N
ATOM      2  CA  LYS A   1      11.000  10.500  10.000  1.00 20.00           C
ATOM      3  CB  LYS A   1      11.500  11.900  10.400  1.00 20.00           C
ATOM      4  CG  LYS A   1      12.900  12.200   9.900  1.00 20.00           C
ATOM      5  CD  LYS A   1      13.400  13.600  10.300  1.00 20.00           C
ATOM      6  CE  LYS A   1      14.800  13.900   9.800  1.00 20.00           C
ATOM      7  NZ  LYS A   1      15.300  15.300  10.200  1.00 20.00           N
ATOM      8  P     U B   1      17.500  16.500  11.400  1.00 20.00           P
ATOM      9  OP1   U B   1      18.900  16.100  10.700  1.00 20.00           O
ATOM     10  OP2   U B   1      17.100  18.000  11.900  1.00 20.00           O
ATOM     11  O5'   U B   1      16.500  15.700  12.600  1.00 20.00           O
ATOM     12  C5'   U B   1      16.900  14.600  13.400  1.00 20.00           C
ATOM     13  C4'   U B   1      16.400  13.300  12.900  1.00 20.00           C
ATOM     14  C3'   U B   1      16.900  12.400  14.000  1.00 20.00           C
ATOM     15  C2'   U B   1      16.300  11.100  13.700  1.00 20.00           C
ATOM     16  O2'   U B   1      16.800   9.900  14.400  1.00 20.00           O
ATOM     17  C1'   U B   1      14.900  11.200  13.900  1.00 20.00           C
ATOM     18  N1    U B   1      14.400  10.900  15.200  1.00 20.00           N
HETATM   19  O   HOH W 100      40.000  40.000  40.000  1.00 20.00           O
TER
END
"""

freesasa = pytest.importorskip("freesasa")  # noqa: F841  (needed by the tool)


def _write(tmp_path: Path, name: str, text: str) -> str:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_buried_sasa_positive_with_extra_water_chain(tmp_path: Path):
    """Old formula: (A + B) − (A + B + water) <= 0 → always clamped to 0.0."""
    out = T.analyze_rna_protein_interface.func(
        _write(tmp_path, "mini.pdb", _PDB), protein_chain_id="A", rna_chain_id="B"
    )
    assert out["interface_contacts"] >= 1
    assert out["buried_sasa"] > 0.0, "buried SASA collapsed to 0 with an extra chain present"
    assert out["protein_surface_area"] > 0.0 and out["rna_surface_area"] > 0.0


def test_salt_bridges_detect_lysine_phosphate_pair(tmp_path: Path):
    """NZ nitrogen 3.5 A from OP1 must count; old protein-protein logic could
    never fire across a protein-RNA interface (always 0)."""
    out = T.analyze_rna_protein_interface.func(
        _write(tmp_path, "mini.pdb", _PDB), protein_chain_id="A", rna_chain_id="B"
    )
    assert out["salt_bridges"] == 1


def test_salt_bridges_zero_when_phosphate_far(tmp_path: Path):
    shifted = _PDB.replace(" 15.300  15.300  10.200", " 45.300  45.300  40.200")
    out = T.analyze_rna_protein_interface.func(
        _write(tmp_path, "far.pdb", shifted), protein_chain_id="A", rna_chain_id="B"
    )
    assert out["salt_bridges"] == 0


# ---------------------------------------------------------------------------
# 2. extract_rna_sequence_from_cif: hetero-flagged modified nucleotides
# ---------------------------------------------------------------------------

_CIF = """\
data_mini
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.label_atom_id
_atom_site.label_alt_id
_atom_site.label_comp_id
_atom_site.label_asym_id
_atom_site.label_entity_id
_atom_site.label_seq_id
_atom_site.pdbx_PDB_ins_code
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.occupancy
_atom_site.B_iso_or_equiv
_atom_site.auth_seq_id
_atom_site.auth_comp_id
_atom_site.auth_asym_id
_atom_site.auth_atom_id
_atom_site.pdbx_PDB_model_num
ATOM 1 N N . U A 1 1 ? 0.000 0.000 0.000 1.0 20.0 1 U A N 1
ATOM 2 C C1' . U A 1 1 ? 1.500 0.000 0.000 1.0 20.0 1 U A C1' 1
ATOM 3 O O2' . U A 1 1 ? 2.500 0.000 0.000 1.0 20.0 1 U A O2' 1
HETATM 4 C C1' . PSU A 1 2 ? 6.500 0.000 0.000 1.0 20.0 2 PSU A C1' 1
HETATM 5 O O2' . PSU A 1 2 ? 7.500 0.000 0.000 1.0 20.0 2 PSU A O2' 1
HETATM 6 O O . HOH W 1 . ? 20.000 20.000 20.000 1.0 20.0 100 HOH W O 1
#
"""


def test_cif_extract_keeps_modified_nucleotide_positions(tmp_path: Path):
    Bio = pytest.importorskip("Bio")  # noqa: F841
    out = T.extract_rna_sequence_from_cif.func(_write(tmp_path, "mini.cif", _CIF), chain_id="A")
    # PSU is hetero in mmCIF: it must be rendered as 'N', not dropped.
    assert out["sequence"] == "UN"
    assert out["residue_count"] == 2
    assert "PSU" in out["warnings"]


# ---------------------------------------------------------------------------
# 3. predict_rna_protein_complex_with_proteinx: multi-line FASTA
# ---------------------------------------------------------------------------


class _Resp:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"pdb_filepath": "/tmp/x.pdb", "mean_plddt": 80.0}


def test_proteinx_complex_sends_full_multiline_fasta(tmp_path: Path):
    protein_fp = _write(tmp_path, "p.fa", ">protein\nMKVKFGRGR\nKVCIEL\n")
    rna_fp = _write(tmp_path, "r.fa", ">rna\nGCGGAUUUAG\nCUCAGUU\n")
    fake = MagicMock(return_value=_Resp())
    with patch.object(T.requests, "post", fake):
        T.predict_rna_protein_complex_with_proteinx.func(
            protein_fp, rna_fp, service_url="http://stub/complex"
        )
    body = fake.call_args.kwargs["json"]
    # Old code sent only the last line of each file ("KVCIEL" / "CUCAGUU").
    assert body["protein_sequence"] == "MKVKFGRGRKVCIEL"
    assert body["rna_sequence"] == "GCGGAUUUAGCUCAGUU"
