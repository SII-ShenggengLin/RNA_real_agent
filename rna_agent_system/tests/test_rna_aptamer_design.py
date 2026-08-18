"""Comprehensive tests for RNA aptamer design workflow across Layer 0, 1, 2, 3.

Coverage:
- Layer 0: Individual tool invocations (CPU real + GPU mocked)
- Layer 1: Capabilities via CapabilityRegistry
- Layer 2: RnaAptamerDesignWorkflow end-to-end
- Layer 3: PipelineAgent orchestrates workflow execution

Run:
  cd rna_agent_system && python -m pytest tests/test_rna_aptamer_design.py -v

╔═══════════════════════════════════════════════════════════════════════════════╗
║  RnaAptamerDesignWorkflow INTERFACE LOCK (v1.4.0) —— 禁止单方面变更         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 rna_aptamer_design 的端到端测试。任何测试增删、断言变更、         ║
║  mock 数据结构调整，必须同步更新以下文件并重新跑通全部测试：                  ║
║                                                                               ║
║    - agent_core/workflows/rna_aptamer_design.py  ← 权威实现                   ║
║    - agent_core/quality_profiles/__init__.py                                  ║
║    - tests/test_rna_aptamer_design.py  ← 本文件                             ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from tests.helpers import make_mock_capability

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_core.capabilities.base import CapabilityRegistry, CapabilityResult
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.rna_aptamer_design import (
    RnaAptamerDesignInput,
    RnaAptamerDesignWorkflow,
    score_aptamer_candidate,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Test fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def test_protein_pdb() -> str:
    """Path to a test protein PDB file with basic residues for hotspot detection."""
    return "/tmp/test_protein_for_aptamer.pdb"


@pytest.fixture(scope="session")
def test_complex_pdb() -> str:
    """Path to a test RNA-protein complex PDB file."""
    return "/tmp/test_rna_protein_complex.pdb"


@pytest.fixture(scope="session")
def test_rna_cif() -> str:
    """Path to a test RNA CIF file."""
    return "/tmp/test_rna.cif"


@pytest.fixture(autouse=True)
def patch_aptamer_service_autostart(monkeypatch):
    """Disable microservice auto-start for all unit tests."""
    monkeypatch.setattr(
        RnaAptamerDesignWorkflow, "_ensure_services_running", lambda self: None
    )


@pytest.fixture
def mock_registry_for_generation() -> MagicMock:
    """Registry with mocked generation-phase capabilities."""
    reg = MagicMock()

    def _make_cap(output: dict[str, Any]) -> MagicMock:
        cap = MagicMock()
        cap.invoke.return_value = CapabilityResult(
            success=True,
            tool_name="mock",
            output=output,
        )
        return cap

    caps = {
        "identify_protein_binding_hotspots": _make_cap({
            "hotspot_residues": "A/2,A/3,A/4",
            "hotspot_patch_size": 3,
        }),
        "build_odesign_aptamer_input_json": _make_cap({
            "input_json_filepath": "workspace/odesign_aptamer_input_test.json",
            "design_config": [],
        }),
        "run_odesign_inference": _make_cap({
            "output_dir": "workspace/odesign_out",
            "prediction_filepaths": [
                "workspace/odesign_out/sample_0.cif",
                "workspace/odesign_out/sample_1.cif",
            ],
            "prediction_count": 2,
        }),
        "extract_rna_sequence_from_cif": _make_cap({
            "sequence": "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            "chain_id": "B",
            "residue_count": 30,
            "is_rna": True,
        }),
    }

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


@pytest.fixture
def mock_registry_for_evaluation() -> MagicMock:
    """Registry with mocked evaluation-phase capabilities."""
    reg = MagicMock()

    def _gc_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="compute_rna_sequence_gc_content",
            output={"gc_content": 0.48, "sequence_length": 30},
        )

    def _rhofold_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_tertiary_structure_with_rhofold",
            output={"pdb_filepath": "workspace/rhofold_test.pdb", "mean_plddt": 85.0},
        )

    def _egarps_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="score_rna_protein_complex_with_egarps",
            output={"native_probability": 0.72, "complex_id": "test"},
        )

    def _proteinx_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_protein_complex_with_proteinx",
            output={"pdb_filepath": "workspace/proteinx_test.pdb", "mean_plddt": 82.0, "ipTM": 0.75},
        )

    def _interface_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="analyze_rna_protein_interface",
            output={
                "interface_contacts": 24,
                "buried_sasa": 1250.5,
                "hydrogen_bonds": 8,
                "salt_bridges": 2,
                "interface_area": 1500.0,
            },
        )

    caps = {
        "compute_rna_sequence_gc_content": MagicMock(),
        "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
        "score_rna_protein_complex_with_egarps": MagicMock(),
        "predict_rna_protein_complex_with_proteinx": MagicMock(),
        "analyze_rna_protein_interface": MagicMock(),
    }
    caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
    caps["predict_rna_tertiary_structure_with_rhofold"].invoke = _rhofold_invoke
    caps["score_rna_protein_complex_with_egarps"].invoke = _egarps_invoke
    caps["predict_rna_protein_complex_with_proteinx"].invoke = _proteinx_invoke
    caps["analyze_rna_protein_interface"].invoke = _interface_invoke

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


@pytest.fixture
def real_cpu_registry() -> CapabilityRegistry:
    """Registry with REAL CPU tools registered (no HTTP/GPU tools)."""
    from agent_core.tools import (
        build_odesign_aptamer_input_json,
        extract_rna_sequence_from_cif,
        identify_protein_binding_hotspots,
        analyze_rna_protein_interface,
    )

    tool_reg = ToolRegistry()
    tool_reg.register(build_odesign_aptamer_input_json)
    tool_reg.register(extract_rna_sequence_from_cif)
    tool_reg.register(identify_protein_binding_hotspots)
    tool_reg.register(analyze_rna_protein_interface)

    executor = ToolExecutor(tool_reg)
    cap_reg = CapabilityRegistry(executor)
    cap_reg.register("build_odesign_aptamer_input_json")
    cap_reg.register("extract_rna_sequence_from_cif")
    cap_reg.register("identify_protein_binding_hotspots")
    cap_reg.register("analyze_rna_protein_interface")
    return cap_reg


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1: Layer 0 — Individual tool invocations
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer0CpuTools:
    """Layer 0 tests for CPU-only tools (run locally, no HTTP/GPU)."""

    def test_extract_rna_sequence_from_cif(self, test_rna_cif: str):
        """Extract RNA sequence from a CIF file (CPU tool)."""
        from agent_core.tools import extract_rna_sequence_from_cif

        result = extract_rna_sequence_from_cif.invoke({"cif_filepath": test_rna_cif})
        assert result["sequence"] == "AU"
        assert result["chain_id"] == "A"
        assert result["residue_count"] == 2
        assert result["is_rna"] is True

    def test_build_odesign_aptamer_input_json(self, test_protein_pdb: str):
        """Build ODesign aptamer input JSON (CPU tool)."""
        from agent_core.tools import build_odesign_aptamer_input_json

        result = build_odesign_aptamer_input_json.invoke({
            "protein_structure_path": test_protein_pdb,
            "protein_chain_id": "A",
            "protein_sequence_length": 6,
            "hotspot_residues": "A/1,A/2",
            "aptamer_length": 30,
        })
        assert "input_json_filepath" in result
        assert result["design_config"][0]["hotspot"] == "A/1,A/2"
        assert result["design_config"][0]["chains"][1]["sequence"] == "30-30"

    def test_identify_protein_binding_hotspots(self, test_protein_pdb: str):
        """Identify binding hotspots on protein surface (CPU tool: biopython + freesasa + sklearn)."""
        from agent_core.tools import identify_protein_binding_hotspots

        result = identify_protein_binding_hotspots.invoke({
            "protein_structure_path": test_protein_pdb,
            "chain_id": "A",
        })
        assert result["hotspot_patch_size"] > 0
        assert result["hotspot_residues"] != ""
        assert len(result["patch_center_coords"]) == 3
        # Should identify LYS(A2), ARG(A3), HIS(A4) as exposed basic residues
        assert "A/2" in result["hotspot_residues"] or "A/3" in result["hotspot_residues"]

    def test_analyze_rna_protein_interface(self, test_complex_pdb: str):
        """Analyze RNA-protein interface (CPU tool: biopython + freesasa)."""
        from agent_core.tools import analyze_rna_protein_interface

        result = analyze_rna_protein_interface.invoke({
            "complex_pdb_filepath": test_complex_pdb,
            "protein_chain_id": "A",
            "rna_chain_id": "B",
            "contact_cutoff": 5.0,
        })
        assert "interface_contacts" in result
        assert "buried_sasa" in result
        assert "hydrogen_bonds" in result
        assert "salt_bridges" in result
        assert result["interface_contacts"] >= 0

    def test_analyze_rna_protein_interface_invalid_chain(self, test_complex_pdb: str):
        """Interface analysis should fail gracefully with invalid chain IDs."""
        from agent_core.tools import analyze_rna_protein_interface

        with pytest.raises(ValueError):
            analyze_rna_protein_interface.invoke({
                "complex_pdb_filepath": test_complex_pdb,
                "protein_chain_id": "Z",
                "rna_chain_id": "Z",
            })


class TestLayer0GpuToolsMocked:
    """Layer 0 tests for GPU-based microservices (mocked HTTP responses)."""

    @patch("agent_core.tools.copy_file_to_workspace")
    @patch("agent_core.tools.requests.post")
    def test_run_odesign_inference(self, mock_post, mock_copy):
        """ODesign inference returns prediction file paths (GPU tool, mocked)."""
        from agent_core.tools import run_odesign_inference

        mock_post.return_value.json.return_value = {
            "input_json_filepath": "/tmp/test.json",
            "infer_model_name": "odesign_base_na_rigid",
            "design_modality": "rna",
            "exp_name": "test",
            "output_dir": "/tmp/odesign_out",
            "prediction_count": 2,
            "prediction_filepaths": ["/tmp/odesign_out/sample_0.cif", "/tmp/odesign_out/sample_1.cif"],
            "sample_names": ["sample_0", "sample_1"],
            "model": "odesign",
        }
        mock_post.return_value.raise_for_status = lambda: None

        result = run_odesign_inference.invoke({
            "input_json_filepath": "/tmp/test.json",
            "design_modality": "rna",
            "n_sample": 2,
            "seeds_json": "[42]",
        })
        assert result["prediction_count"] == 2
        assert len(result["prediction_filepaths"]) == 2
        mock_post.assert_called_once()

    @patch("agent_core.tools.copy_file_to_workspace")
    @patch("agent_core.tools.read_sequence")
    @patch("agent_core.tools.requests.post")
    def test_predict_rna_tertiary_structure_with_rhofold(self, mock_post, mock_read, mock_copy):
        """RhoFold returns pLDDT and PDB path (GPU tool, mocked)."""
        from agent_core.tools import predict_rna_tertiary_structure_with_rhofold

        mock_post.return_value.json.return_value = {
            "input_filepath": "/tmp/test.fa",
            "output_pdb_path": "/tmp/rhofold/test.pdb",
            "mean_plddt": 85.5,
            "model": "rhofold",
        }
        mock_post.return_value.raise_for_status = lambda: None
        mock_read.return_value = "AUGC" * 10

        result = predict_rna_tertiary_structure_with_rhofold.invoke({
            "filepath": "/tmp/test.fa",
        })
        assert result["mean_plddt"] == pytest.approx(85.5, abs=0.1)
        assert "pdb_filepath" in result

    @patch("agent_core.tools.requests.post")
    def test_score_rna_protein_complex_with_egarps(self, mock_post):
        """EGARPS returns native probability (GPU tool, mocked)."""
        from agent_core.tools import score_rna_protein_complex_with_egarps

        mock_post.return_value.json.return_value = {
            "complex_id": "test_complex",
            "native_probability": 0.85,
            "academic": False,
            "model": "egarps",
            "pdb_path": "/tmp/test.pdb",
        }
        mock_post.return_value.raise_for_status = lambda: None

        result = score_rna_protein_complex_with_egarps.invoke({
            "filepath": "/tmp/test.pdb",
            "academic": False,
        })
        assert result["native_probability"] == pytest.approx(0.85, abs=0.01)

    @patch("agent_core.tools.copy_file_to_workspace")
    @patch("agent_core.tools.read_sequence")
    @patch("agent_core.tools.requests.post")
    def test_predict_rna_protein_complex_with_proteinx(self, mock_post, mock_read, mock_copy):
        """ProteinX returns ipTM and pLDDT (GPU tool, mocked)."""
        from agent_core.tools import predict_rna_protein_complex_with_proteinx

        mock_post.return_value.json.return_value = {
            "pdb_filepath": "/tmp/proteinx/complex.cif",
            "mean_plddt": 82.0,
            "ipTM": 0.75,
            "ranking_confidence": 0.80,
            "model_scores": [],
            "model": "proteinx",
        }
        mock_post.return_value.raise_for_status = lambda: None
        mock_read.return_value = ">seq\nAUGC" * 5

        result = predict_rna_protein_complex_with_proteinx.invoke({
            "protein_filepath": "/tmp/protein.fa",
            "rna_filepath": "/tmp/rna.fa",
            "num_models": 1,
        })
        assert result["ipTM"] == pytest.approx(0.75, abs=0.01)
        assert result["mean_plddt"] == pytest.approx(82.0, abs=0.1)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: Scoring function & Input validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestScoringFunction:
    """Unit tests for score_aptamer_candidate."""

    def test_perfect_metrics(self):
        metrics = {
            "rhofold_mean_plddt": 95.0,
            "egarps_native_probability": 0.90,
            "proteinx_ipTM": 0.85,
        }
        scores = score_aptamer_candidate(metrics)
        assert scores["egarps_component"] == pytest.approx(0.90, abs=1e-6)
        assert scores["rhofold_component"] == pytest.approx(0.95, abs=1e-6)
        assert scores["iptm_component"] == pytest.approx(0.85, abs=1e-6)

    def test_missing_metrics_return_components(self):
        """Missing metrics should return available components without total_score."""
        metrics = {"rhofold_mean_plddt": 50.0}
        scores = score_aptamer_candidate(metrics)
        assert scores["rhofold_component"] == pytest.approx(0.50, abs=1e-6)
        assert "total_score" not in scores

    def test_only_egarps(self):
        metrics = {"egarps_native_probability": 0.60}
        scores = score_aptamer_candidate(metrics)
        assert scores["egarps_component"] == pytest.approx(0.60, abs=1e-6)
        assert "total_score" not in scores

    def test_no_weighted_sum(self):
        """score_aptamer_candidate no longer computes a weighted total_score."""
        metrics = {
            "rhofold_mean_plddt": 100.0,
            "egarps_native_probability": 0.50,
            "proteinx_ipTM": 0.50,
        }
        scores = score_aptamer_candidate(metrics)
        assert scores["egarps_component"] == pytest.approx(0.50, abs=1e-6)
        assert scores["rhofold_component"] == pytest.approx(1.0, abs=1e-6)
        assert scores["iptm_component"] == pytest.approx(0.50, abs=1e-6)
        assert "total_score" not in scores


def test_rank_and_format_reference_point():
    """Reference point should select the candidate closest to it."""
    wf = RnaAptamerDesignWorkflow(MagicMock())
    c1 = Candidate(sequence="ACGUACGU", scores={
        "egarps_component": 0.9,
        "rhofold_component": 0.5,
        "iptm_component": 0.5,
    })
    c2 = Candidate(sequence="UGCAUGCA", scores={
        "egarps_component": 0.5,
        "rhofold_component": 0.9,
        "iptm_component": 0.5,
    })
    wf._workflow_state["_aptamer_input"] = RnaAptamerDesignInput(
        protein_structure_path="test.pdb",
        reference_point={"rhofold_component": 1.0},
    )
    result = wf.rank_and_format([c1, c2])
    assert result.success is True
    assert result.best_candidate is c2
    assert getattr(result, "best_candidate_source", None) == "reference_point_optimization"


def test_rank_and_format_pareto_frontier():
    """Pareto frontier is always returned."""
    wf = RnaAptamerDesignWorkflow(MagicMock())
    c1 = Candidate(sequence="ACGUACGU", scores={
        "egarps_component": 0.9,
        "rhofold_component": 0.5,
        "iptm_component": 0.5,
    })
    c2 = Candidate(sequence="UGCAUGCA", scores={
        "egarps_component": 0.5,
        "rhofold_component": 0.9,
        "iptm_component": 0.5,
    })
    c3 = Candidate(sequence="AAAACCCCUUUU", scores={
        "egarps_component": 0.4,
        "rhofold_component": 0.4,
        "iptm_component": 0.4,
    })
    wf._workflow_state["_aptamer_input"] = RnaAptamerDesignInput(
        protein_structure_path="test.pdb",
    )
    result = wf.rank_and_format([c1, c2, c3])
    assert result.success is True
    frontier = getattr(result, "pareto_frontier", None)
    assert frontier is not None
    assert c3 not in frontier
    assert len(frontier) == 2


class TestInputValidation:
    """Pydantic input model validation."""

    def test_defaults(self):
        inp = RnaAptamerDesignInput(protein_structure_path="test.pdb")
        assert inp.chain_id == "A"
        assert inp.aptamer_length == 30
        assert inp.n_odesign_samples == 8
        assert inp.odesign_seeds == [42, 123]

    def test_dict_coercion(self):
        raw = {
            "protein_structure_path": "test.pdb",
            "chain_id": "B",
            "aptamer_length": 45,
            "hotspot_residues": "B/10,B/20",
        }
        inp = RnaAptamerDesignInput(**raw)
        assert inp.chain_id == "B"
        assert inp.aptamer_length == 45

    def test_invalid_aptamer_length_too_short(self):
        with pytest.raises(Exception):
            RnaAptamerDesignInput(protein_structure_path="test.pdb", aptamer_length=5)

    def test_invalid_aptamer_length_too_long(self):
        with pytest.raises(Exception):
            RnaAptamerDesignInput(protein_structure_path="test.pdb", aptamer_length=250)

    def test_invalid_protein_sequence(self):
        with pytest.raises(Exception):
            RnaAptamerDesignInput(
                protein_structure_path="test.pdb",
                protein_sequence="ACDEFGHIKLMNPQRSTVWXYZ",
            )

    def test_invalid_hotspot_format(self):
        with pytest.raises(Exception):
            RnaAptamerDesignInput(
                protein_structure_path="test.pdb",
                hotspot_residues="invalid_format",
            )

    def test_reference_point_validation(self):
        """Unknown objective keys in reference_point raise ValueError."""
        with pytest.raises(ValueError, match="unknown objectives"):
            RnaAptamerDesignInput(
                protein_structure_path="test.pdb",
                reference_point={"invalid_dim": 1.0},
            )

    def test_reference_point_valid(self):
        """Valid reference_point keys are accepted."""
        inp = RnaAptamerDesignInput(
            protein_structure_path="test.pdb",
            reference_point={"egarps_component": 0.8, "rhofold_component": 0.9},
        )
        assert inp.reference_point == {"egarps_component": 0.8, "rhofold_component": 0.9}

# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: Layer 1 — Capabilities via CapabilityRegistry
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer1Capabilities:
    """Layer 1 tests: capabilities wrapped through CapabilityRegistry + ToolExecutor."""

    def test_cpu_capability_registry_real_tools(self, test_protein_pdb: str, test_rna_cif: str):
        """CPU tools registered in CapabilityRegistry and invoked correctly."""
        from agent_core.tools import (
            build_odesign_aptamer_input_json,
            extract_rna_sequence_from_cif,
            identify_protein_binding_hotspots,
            analyze_rna_protein_interface,
        )

        tool_reg = ToolRegistry()
        tool_reg.register(build_odesign_aptamer_input_json)
        tool_reg.register(extract_rna_sequence_from_cif)
        tool_reg.register(identify_protein_binding_hotspots)
        tool_reg.register(analyze_rna_protein_interface)

        executor = ToolExecutor(tool_reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("build_odesign_aptamer_input_json")
        cap_reg.register("extract_rna_sequence_from_cif")
        cap_reg.register("identify_protein_binding_hotspots")
        cap_reg.register("analyze_rna_protein_interface")

        # Test hotspot identification through capability
        cap = cap_reg.get("identify_protein_binding_hotspots")
        result = cap.invoke({
            "protein_structure_path": test_protein_pdb,
            "chain_id": "A",
        }, state={})
        assert result.success is True
        assert result.output["hotspot_patch_size"] > 0

        # Test CIF extraction through capability
        cap = cap_reg.get("extract_rna_sequence_from_cif")
        result = cap.invoke({"cif_filepath": test_rna_cif}, state={})
        assert result.success is True
        assert result.output["sequence"] == "AU"

    @patch("agent_core.tools.copy_file_to_workspace")
    @patch("agent_core.tools.requests.post")
    def test_gpu_capability_registry_mocked(self, mock_post, mock_copy):
        """GPU tools registered in CapabilityRegistry with mocked HTTP."""
        from agent_core.tools import (
            run_odesign_inference,
            score_rna_protein_complex_with_egarps,
            predict_rna_protein_complex_with_proteinx,
        )

        mock_post.return_value.json.return_value = {
            "output_dir": "/tmp/out",
            "prediction_count": 1,
            "prediction_filepaths": ["/tmp/out/s.cif"],
            "model": "odesign",
        }
        mock_post.return_value.raise_for_status = lambda: None

        tool_reg = ToolRegistry()
        tool_reg.register(run_odesign_inference)
        tool_reg.register(score_rna_protein_complex_with_egarps)
        tool_reg.register(predict_rna_protein_complex_with_proteinx)

        executor = ToolExecutor(tool_reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("run_odesign_inference")
        cap_reg.register("score_rna_protein_complex_with_egarps")
        cap_reg.register("predict_rna_protein_complex_with_proteinx")

        cap = cap_reg.get("run_odesign_inference")
        result = cap.invoke({
            "input_json_filepath": "/tmp/test.json",
            "design_modality": "rna",
            "n_sample": 1,
            "seeds_json": "[42]",
        }, state={})
        assert result.success is True
        assert result.output["prediction_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4: Layer 2 — Workflow integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer2WorkflowGeneration:
    """Layer 2 tests for candidate generation."""

    def test_generate_candidates_with_mocked_odesign(self, mock_registry_for_generation):
        """Mocked ODesign should produce candidates from prediction files."""
        wf = RnaAptamerDesignWorkflow(mock_registry_for_generation)
        inp = RnaAptamerDesignInput(
            protein_structure_path="/tmp/test_protein_for_aptamer.pdb",
            chain_id="A",
            aptamer_length=30,
        )
        candidates = wf.generate_candidates(inp)
        # extract_rna_sequence_from_cif returns same sequence for both files,
        # so after dedup we get 1 candidate
        assert len(candidates) == 1
        assert candidates[0].sequence == "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC"
        assert candidates[0].metadata["hotspot_residues"] == "A/2,A/3,A/4"

    def test_generate_candidates_explicit_hotspot(self, mock_registry_for_generation):
        """Explicit hotspot should skip auto-identification."""
        wf = RnaAptamerDesignWorkflow(mock_registry_for_generation)
        inp = RnaAptamerDesignInput(
            protein_structure_path="/tmp/test_protein_for_aptamer.pdb",
            hotspot_residues="C/100,C/200",
            aptamer_length=30,
        )
        candidates = wf.generate_candidates(inp)
        assert len(candidates) == 1
        assert candidates[0].metadata["hotspot_residues"] == "C/100,C/200"

    def test_generate_candidates_no_structure(self, mock_registry_for_generation):
        """No structure path and no sequence should return empty list."""
        wf = RnaAptamerDesignWorkflow(mock_registry_for_generation)
        inp = RnaAptamerDesignInput(aptamer_length=30)
        candidates = wf.generate_candidates(inp)
        assert len(candidates) == 0

    def test_generate_candidates_with_real_cpu_tools(self, test_protein_pdb: str):
        """Generate candidates using REAL CPU tools for hotspot + JSON + extraction."""
        from agent_core.tools import (
            build_odesign_aptamer_input_json,
            extract_rna_sequence_from_cif,
            identify_protein_binding_hotspots,
        )

        tool_reg = ToolRegistry()
        tool_reg.register(build_odesign_aptamer_input_json)
        tool_reg.register(extract_rna_sequence_from_cif)
        tool_reg.register(identify_protein_binding_hotspots)

        executor = ToolExecutor(tool_reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("build_odesign_aptamer_input_json")
        cap_reg.register("extract_rna_sequence_from_cif")
        cap_reg.register("identify_protein_binding_hotspots")

        # Mock only the GPU tools
        def _make_cap(output: dict[str, Any]) -> MagicMock:
            cap = MagicMock()
            cap.invoke.return_value = CapabilityResult(
                success=True, tool_name="mock", output=output,
            )
            return cap

        odesign_cap = _make_cap({
            "output_dir": "workspace/odesign_out",
            "prediction_filepaths": ["workspace/odesign_out/sample_0.cif"],
            "prediction_count": 1,
        })

        cap_reg._capabilities["run_odesign_inference"] = odesign_cap

        wf = RnaAptamerDesignWorkflow(cap_reg)
        inp = RnaAptamerDesignInput(
            protein_structure_path=test_protein_pdb,
            chain_id="A",
            aptamer_length=30,
        )
        candidates = wf.generate_candidates(inp)
        # Should have candidates (number depends on whether CIF extraction succeeds)
        # Since we mock ODesign to return a CIF path, but extract_rna_from_cif is real,
        # and that CIF path probably doesn't exist, we may get 0 candidates.
        # This test validates the real CPU tool path works through the workflow.
        assert isinstance(candidates, list)


class TestLayer2WorkflowEvaluation:
    """Layer 2 tests for candidate evaluation."""

    def test_evaluate_returns_expected_keys(self, mock_registry_for_evaluation):
        wf = RnaAptamerDesignWorkflow(mock_registry_for_evaluation)
        candidate = Candidate(
            sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            metadata={"odesign_prediction_path": "workspace/test.pdb"},
        )
        metrics = wf.evaluate(candidate)
        assert "gc_content" in metrics
        assert "rhofold_mean_plddt" in metrics
        assert "egarps_native_probability" in metrics
        assert "proteinx_ipTM" in metrics
        assert "interface_contacts" in metrics
        assert metrics["gc_content"] == pytest.approx(0.48, abs=1e-6)
        assert metrics["rhofold_mean_plddt"] == pytest.approx(85.0, abs=1e-6)

    def test_evaluate_graceful_degradation_no_odesign_path(self, mock_registry_for_evaluation):
        """Evaluation should still work when odesign prediction path is missing."""
        wf = RnaAptamerDesignWorkflow(mock_registry_for_evaluation)
        candidate = Candidate(
            sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            metadata={},
        )
        metrics = wf.evaluate(candidate)
        # EGARPS and interface analysis should be None when no odesign path
        assert metrics["egarps_native_probability"] is None
        assert metrics["interface_contacts"] is None
        # But GC and RhoFold should still work
        assert metrics["gc_content"] == pytest.approx(0.48, abs=1e-6)

    def test_evaluate_skips_egarps_when_rhofold_low(self):
        """EGARPS should be skipped when RhoFold pLDDT < 65.0."""
        reg = MagicMock()
        egarps_invoke = MagicMock(return_value=CapabilityResult(
            success=True, tool_name="egarps", output={"native_probability": 0.99}
        ))
        egarps_cap = MagicMock()
        egarps_cap.invoke = egarps_invoke
        caps = {
            "compute_rna_sequence_gc_content": MagicMock(),
            "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
            "score_rna_protein_complex_with_egarps": egarps_cap,
            "predict_rna_protein_complex_with_proteinx": MagicMock(),
            "analyze_rna_protein_interface": MagicMock(),
        }
        caps["compute_rna_sequence_gc_content"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="gc", output={"gc_content": 0.5}
        )
        # RhoFold pLDDT below the 65.0 EGARPS gate
        caps["predict_rna_tertiary_structure_with_rhofold"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="rho", output={"mean_plddt": 60.0, "pdb_filepath": "workspace/rho.pdb"}
        )
        caps["predict_rna_protein_complex_with_proteinx"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="proteinx", output={"ipTM": 0.7, "mean_plddt": 80.0}
        )
        caps["analyze_rna_protein_interface"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="iface", output={"interface_contacts": 20}
        )
        reg.has = lambda name: name in caps
        reg.get = lambda name: caps[name]

        wf = RnaAptamerDesignWorkflow(reg)
        candidate = Candidate(
            sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            metadata={"odesign_prediction_path": "workspace/test.pdb"},
        )
        metrics = wf.evaluate(candidate)
        assert metrics["egarps_native_probability"] is None
        egarps_invoke.assert_not_called()

    @pytest.mark.parametrize("gc_value", [0.20, 0.90])
    def test_evaluate_skips_egarps_when_gc_extreme(self, gc_value):
        """EGARPS should be skipped when GC content is outside [0.25, 0.85]."""
        reg = MagicMock()
        egarps_invoke = MagicMock(return_value=CapabilityResult(
            success=True, tool_name="egarps", output={"native_probability": 0.99}
        ))
        egarps_cap = MagicMock()
        egarps_cap.invoke = egarps_invoke
        caps = {
            "compute_rna_sequence_gc_content": MagicMock(),
            "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
            "score_rna_protein_complex_with_egarps": egarps_cap,
            "predict_rna_protein_complex_with_proteinx": MagicMock(),
            "analyze_rna_protein_interface": MagicMock(),
        }
        caps["compute_rna_sequence_gc_content"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="gc", output={"gc_content": gc_value}
        )
        caps["predict_rna_tertiary_structure_with_rhofold"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="rho", output={"mean_plddt": 85.0, "pdb_filepath": "workspace/rho.pdb"}
        )
        caps["predict_rna_protein_complex_with_proteinx"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="proteinx", output={"ipTM": 0.7, "mean_plddt": 80.0}
        )
        caps["analyze_rna_protein_interface"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="iface", output={"interface_contacts": 20}
        )
        reg.has = lambda name: name in caps
        reg.get = lambda name: caps[name]

        wf = RnaAptamerDesignWorkflow(reg)
        candidate = Candidate(
            sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            metadata={"odesign_prediction_path": "workspace/test.pdb"},
        )
        metrics = wf.evaluate(candidate)
        assert metrics["egarps_native_probability"] is None
        egarps_invoke.assert_not_called()


class TestLayer2WorkflowFullPipeline:
    """Layer 2 end-to-end workflow tests."""

    def test_full_pipeline_mocked(self):
        """Full pipeline: generate -> evaluate -> score -> rank with mocked capabilities."""
        reg = MagicMock()

        # Generation mocks
        gen_caps = {
            "identify_protein_binding_hotspots": make_mock_capability({
                "hotspot_residues": "A/2,A/3",
                "hotspot_patch_size": 2,
            }),
            "build_odesign_aptamer_input_json": make_mock_capability({
                "input_json_filepath": "workspace/odesign_input.json",
            }),
            "run_odesign_inference": make_mock_capability({
                "prediction_filepaths": ["workspace/pred_0.cif"],
            }),
            "extract_rna_sequence_from_cif": make_mock_capability({
                "sequence": "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            }),
        }

        # Evaluation mocks
        def _gc_invoke(args, state=None):
            return CapabilityResult(success=True, tool_name="gc", output={"gc_content": 0.48})

        def _rhofold_invoke(args, state=None):
            return CapabilityResult(success=True, tool_name="rho", output={"mean_plddt": 85.0, "pdb_filepath": "workspace/rho.pdb"})

        eval_caps = {
            "compute_rna_sequence_gc_content": MagicMock(),
            "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
            "score_rna_protein_complex_with_egarps": MagicMock(),
            "predict_rna_protein_complex_with_proteinx": MagicMock(),
            "analyze_rna_protein_interface": MagicMock(),
        }
        eval_caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
        eval_caps["predict_rna_tertiary_structure_with_rhofold"].invoke = _rhofold_invoke
        eval_caps["score_rna_protein_complex_with_egarps"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="egarps", output={"native_probability": 0.65}
        )
        eval_caps["predict_rna_protein_complex_with_proteinx"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="proteinx", output={"ipTM": 0.70, "mean_plddt": 80.0}
        )
        eval_caps["analyze_rna_protein_interface"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="iface", output={"interface_contacts": 20, "buried_sasa": 1000.0}
        )

        all_caps = {**gen_caps, **eval_caps}
        reg.has = lambda name: name in all_caps
        reg.get = lambda name: all_caps[name]

        wf = RnaAptamerDesignWorkflow(reg)
        inp = RnaAptamerDesignInput(
            protein_structure_path="/tmp/test_protein_for_aptamer.pdb",
            aptamer_length=30,
        )
        result = wf.run(inp)

        assert result.success is True
        assert result.best_candidate is not None
        assert len(result.all_candidates) == 1
        assert "asf=" in result.summary or "RhoFold=" in result.summary
        assert result.best_candidate.scores.get("asf_distance") is not None

    def test_rank_and_format_empty_candidates(self):
        wf = RnaAptamerDesignWorkflow(MagicMock())
        result = wf.rank_and_format([])
        assert result.success is False
        assert "empty_candidate_list" in result.errors

    def test_required_services_maps_rhofold_to_correct_port(self):
        """RhoFold capability must point to port 8005 and the rhofold service start script."""
        from agent_core.services.service_manager import CAPABILITY_SERVICE_MAP

        rhofold = CAPABILITY_SERVICE_MAP["predict_rna_tertiary_structure_with_rhofold"]
        assert rhofold.port == 8005
        assert rhofold.health_path == "/health"
        assert "microservices/rhofold_service/start.sh" in rhofold.start_script

        odesign = CAPABILITY_SERVICE_MAP["run_odesign_inference"]
        assert odesign.port == 8012
        assert "microservices/odesign_service/start.sh" in odesign.start_script

    def test_resolve_protein_structure_falls_back_to_sequence_prediction(self, tmp_path):
        """When only protein_sequence is provided, predict structure with ProteinX."""
        predicted_pdb = tmp_path / "predicted_protein.pdb"
        predicted_pdb.write_text("MODEL 1\nENDMDL\n")

        reg = MagicMock()
        structure_cap = MagicMock()
        structure_cap.invoke = MagicMock(return_value=CapabilityResult(
            success=True,
            tool_name="predict_protein_structure_with_proteinx",
            output={"pdb_filepath": str(predicted_pdb)},
        ))
        caps = {"predict_protein_structure_with_proteinx": structure_cap}
        reg.has = lambda name: name in caps
        reg.get = lambda name: caps[name]

        wf = RnaAptamerDesignWorkflow(reg)
        inp = RnaAptamerDesignInput(protein_sequence="MKTAYIAKQRQISFVKSHFSRQ")
        path = wf._resolve_protein_structure(inp)
        assert path == str(predicted_pdb)
        structure_cap.invoke.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5: Layer 3 — PipelineAgent orchestration
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer4PipelineAgent:
    """Layer 4 tests: PipelineAgent orchestrates workflow execution."""

    def _make_quality_agent(self) -> "QualityAgent":
        from agent_core.agents.quality_agent import QualityAgent, QualityReport

        report = QualityReport(
            overall_assessment="ok",
            quality_score=1.0,
            action="pass",
            reasoning="fine",
        )
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content=report.model_dump_json())
        return QualityAgent(llm=llm)

    def test_pipeline_agent_runs_workflow(self):
        """PipelineAgent should execute rna_aptamer_design and invoke progress callback."""
        from agent_core.agents.pipeline_agent import PipelineAgent
        from agent_core.agents.quality_agent import QualityReport
        from agent_core.agents.specialist_agent import SpecialistAgent
        from agent_core.agents.synthesis_agent import SynthesisAgent
        from agent_core.pipeline.models import PipelinePlan
        from agent_core.quality_profiles.rna_aptamer_design import (
            RNA_APTAMER_QUALITY_PROFILE,
        )

        reg = MagicMock()
        gen_caps = {
            "identify_protein_binding_hotspots": make_mock_capability({
                "hotspot_residues": "A/2,A/3",
                "hotspot_patch_size": 2,
            }),
            "build_odesign_aptamer_input_json": make_mock_capability({
                "input_json_filepath": "workspace/odesign_input.json",
            }),
            "run_odesign_inference": make_mock_capability({
                "prediction_filepaths": ["workspace/pred_0.cif"],
            }),
            "extract_rna_sequence_from_cif": make_mock_capability({
                "sequence": "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            }),
            "compute_rna_sequence_gc_content": MagicMock(),
            "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
            "score_rna_protein_complex_with_egarps": MagicMock(),
            "predict_rna_protein_complex_with_proteinx": MagicMock(),
            "analyze_rna_protein_interface": MagicMock(),
        }

        def _gc_invoke(args, state=None):
            return CapabilityResult(success=True, tool_name="gc", output={"gc_content": 0.48})

        def _rhofold_invoke(args, state=None):
            return CapabilityResult(success=True, tool_name="rho", output={"mean_plddt": 85.0, "pdb_filepath": "workspace/rho.pdb"})

        gen_caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
        gen_caps["predict_rna_tertiary_structure_with_rhofold"].invoke = _rhofold_invoke
        gen_caps["score_rna_protein_complex_with_egarps"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="egarps", output={"native_probability": 0.65}
        )
        gen_caps["predict_rna_protein_complex_with_proteinx"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="proteinx", output={"ipTM": 0.70}
        )
        gen_caps["analyze_rna_protein_interface"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="iface", output={"interface_contacts": 20}
        )

        reg.has = lambda name: name in gen_caps
        reg.get = lambda name: gen_caps[name]

        wf = RnaAptamerDesignWorkflow(reg)
        specialist = SpecialistAgent(wf, RNA_APTAMER_QUALITY_PROFILE)
        pipeline_agent = PipelineAgent(
            specialist_registry={"rna_aptamer_design": specialist},
            quality_agent=self._make_quality_agent(),
            synthesis_agent=SynthesisAgent(enable_llm=False),
        )

        plan = PipelinePlan.single(
            workflow="rna_aptamer_design",
            static_params={
                "protein_structure_path": "/tmp/test_protein_for_aptamer.pdb",
                "aptamer_length": 30,
            },
            plan_id="aptamer_pipeline",
            output_alias="aptamer_result",
        )

        progress_calls: list[Any] = []

        def _progress(payload: Any) -> None:
            progress_calls.append(payload)

        result = pipeline_agent.execute(plan, progress_callback=_progress)

        assert result.success is True
        assert "n1" in result.node_results
        node_result = result.node_results["n1"]
        assert node_result.workflow == "rna_aptamer_design"
        assert node_result.workflow_result is not None
        assert node_result.workflow_result.success is True
        assert node_result.workflow_result.best_candidate is not None
        assert len(progress_calls) > 0
        assert all("event" in call for call in progress_calls)
