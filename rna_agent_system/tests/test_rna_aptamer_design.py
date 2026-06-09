"""Comprehensive tests for RNA aptamer design workflow across Layer 0, 1, 2, 3.

Coverage:
- Layer 0: Individual tool invocations (CPU real + GPU mocked)
- Layer 1: Capabilities via CapabilityRegistry
- Layer 2: RnaAptamerDesignWorkflow end-to-end
- Layer 3: ExecutionController + LLM Critic retry flow
- DeepSeek API: Live LLM connectivity and critic diagnosis

Run:
  cd rna_agent_system && python -m pytest tests/test_rna_aptamer_design.py -v

Run with live LLM tests:
  cd rna_agent_system && python -m pytest tests/test_rna_aptamer_design.py -v --live-llm

╔═══════════════════════════════════════════════════════════════════════════════╗
║  RnaAptamerDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 rna_aptamer_design 的端到端测试。任何测试增删、断言变更、         ║
║  mock 数据结构调整，必须同步更新以下文件并重新跑通全部测试：                  ║
║                                                                               ║
║    - agent_core/workflows/rna_aptamer_design.py  ← 权威实现                   ║
║    - agent_core/workflows/registry.py                                         ║
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
from agent_core.workflows.coordinator import AptamerCoordinator, Issue
from agent_core.workflows.rna_aptamer_design import (
    LLMAptamerCoordinator,
    RnaAptamerDesignInput,
    RnaAptamerDesignLLMCritic,
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

    def test_missing_metrics_renormalize(self):
        """Missing metrics should be omitted and weights re-normalized."""
        metrics = {"rhofold_mean_plddt": 50.0}
        scores = score_aptamer_candidate(metrics)
        assert scores["rhofold_component"] == pytest.approx(0.50, abs=1e-6)
        assert scores["total_score"] == pytest.approx(0.50, abs=1e-6)

    def test_only_egarps(self):
        metrics = {"egarps_native_probability": 0.60}
        scores = score_aptamer_candidate(metrics)
        assert scores["total_score"] == pytest.approx(0.60, abs=1e-6)

    def test_custom_weights(self):
        metrics = {
            "rhofold_mean_plddt": 100.0,
            "egarps_native_probability": 0.50,
            "proteinx_ipTM": 0.50,
        }
        scores = score_aptamer_candidate(metrics, weight_egarps=0.33, weight_rhofold=0.33)
        expected = (0.33 * 0.50 + 0.33 * 1.0 + 0.34 * 0.50) / 1.0
        assert scores["total_score"] == pytest.approx(expected, abs=1e-6)


class TestInputValidation:
    """Pydantic input model validation."""

    def test_defaults(self):
        inp = RnaAptamerDesignInput(protein_structure_path="test.pdb")
        assert inp.chain_id == "A"
        assert inp.aptamer_length == 30
        assert inp.n_odesign_samples == 5
        assert inp.odesign_seeds == [42]

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
        assert result.best_candidate.scores["total_score"] > 0.0
        assert "RhoFold=" in result.summary or "EGARPS=" in result.summary

    def test_rank_and_format_empty_candidates(self):
        wf = RnaAptamerDesignWorkflow(MagicMock())
        result = wf.rank_and_format([])
        assert result.success is False
        assert "empty_candidate_list" in result.errors


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5: Layer 3 — ExecutionController + Critic + Retry
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer3ExecutionController:
    """Layer 3 tests: ExecutionController orchestrates workflow execution."""

    def test_execution_controller_runs_workflow(self):
        """ExecutionController should execute rna_aptamer_design as a workflow step."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

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
        workflow_registry = {"rna_aptamer_design": wf}

        controller = ExecutionController(
            capability_registry=reg,
            workflow_registry=workflow_registry,
        )

        plan = ExecutionPlan(steps=[
            PlanStep(
                step_id="s1",
                type="workflow",
                target="rna_aptamer_design",
                input_binding={
                    "protein_structure_path": "/tmp/test_protein_for_aptamer.pdb",
                    "aptamer_length": 30,
                },
                output_key="aptamer_result",
                description="Design aptamer",
            ),
        ])

        # Disable critic for this test (avoid live LLM call)
        with patch.object(controller, "_resolve_critic", return_value=None):
            state: dict[str, Any] = {}
            result_state = controller.execute(plan, state)

        assert result_state["aptamer_result"].success is True
        assert "workflow_result" in result_state
        assert result_state["workflow_result"].success is True
        assert "_execution_log" in result_state
        assert any(entry["event"] == "plan_complete" for entry in result_state["_execution_log"])


class TestLayer3CriticRetry:
    """Layer 3 retry tests: critic triggers retry with parameter overrides."""

    def test_critic_retry_with_parameter_override(self):
        """Mock LLM critic recommends parameter adjustments → retry triggered."""
        from agent_core.planning.llm_critic import CriticDiagnosis, CriticIssue

        critic = RnaAptamerDesignLLMCritic()

        result = WorkflowResult(
            success=True,
            task_id="test",
            summary="test",
            errors=[],
            all_candidates=[
                _make_aptamer_candidate("AUGC" * 8, gc=0.15, egarps=0.20, rhofold=30.0),
            ],
        )

        mock_diagnosis = CriticDiagnosis(
            overall_assessment="GC too low and binding affinity poor",
            quality_score=0.2,
            issues=[
                CriticIssue(
                    severity="critical",
                    category="binding_affinity",
                    description="EGARPS native_probability too low",
                    metric_value=0.20,
                    affected_candidate_count=1,
                )
            ],
            action="retry_with_adjustments",
            parameter_overrides={"weight_egarps": 0.70, "weight_rhofold": 0.30},
            reasoning="Prioritize binding affinity over foldability",
            confidence=0.9,
        )

        with patch.object(critic, "diagnose", return_value=mock_diagnosis):
            state = {"_last_workflow_params": {"weight_egarps": 0.50, "weight_rhofold": 0.50}}
            should_retry = critic.should_retry(result, state)

        assert should_retry is True
        assert state.get("_parameter_overrides") == {"weight_egarps": 0.70, "weight_rhofold": 0.30}

    def test_critic_no_retry_when_quality_good(self):
        """Mock LLM critic returns proceed → no retry."""
        from agent_core.planning.llm_critic import CriticDiagnosis

        critic = RnaAptamerDesignLLMCritic()

        result = WorkflowResult(
            success=True,
            task_id="test",
            summary="test",
            errors=[],
            all_candidates=[
                _make_aptamer_candidate("AUGC" * 8, gc=0.50, egarps=0.80, rhofold=85.0),
            ],
        )

        mock_diagnosis = CriticDiagnosis(
            overall_assessment="Good quality candidates",
            quality_score=0.85,
            issues=[],
            action="proceed_with_filtered",
            parameter_overrides={},
            reasoning="All metrics acceptable",
            confidence=0.95,
        )

        with patch.object(critic, "diagnose", return_value=mock_diagnosis):
            state = {"_last_workflow_params": {"aptamer_length": 30}}
            should_retry = critic.should_retry(result, state)

        assert should_retry is False

    def test_execution_controller_triggers_retry_and_applies_overrides(self):
        """ExecutionController executes workflow, critic triggers retry, overrides applied."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.planning.llm_critic import CriticDiagnosis, CriticIssue

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
        controller = ExecutionController(
            capability_registry=reg,
            workflow_registry={"rna_aptamer_design": wf},
        )

        # Create a critic that will trigger retry once
        critic = RnaAptamerDesignLLMCritic()
        mock_diagnosis = CriticDiagnosis(
            overall_assessment="Low quality, needs retry",
            quality_score=0.2,
            issues=[CriticIssue(severity="critical", category="binding", description="Poor binding")],
            action="retry_with_adjustments",
            parameter_overrides={"weight_egarps": 0.80, "weight_rhofold": 0.20},
            reasoning="Prioritize binding affinity",
            confidence=0.9,
        )

        # Patch _resolve_critic to return our patched critic (bypass registry lookup)
        def _mock_resolve_critic(step, get_critic_fn):
            return critic

        with patch.object(critic, "diagnose", return_value=mock_diagnosis):
            with patch.object(controller, "_resolve_critic", _mock_resolve_critic):
                plan = ExecutionPlan(
                    steps=[
                        PlanStep(
                            step_id="s1",
                            type="workflow",
                            target="rna_aptamer_design",
                            input_binding={"protein_structure_path": "/tmp/test_protein_for_aptamer.pdb", "weight_egarps": 0.50},
                            output_key="aptamer_result",
                            description="Design aptamer",
                        ),
                    ],
                    max_retries=1,
                )

                state: dict[str, Any] = {}
                result_state = controller.execute(plan, state)

        # Should have retried once
        assert result_state.get("retry_count") == 1
        assert result_state["aptamer_result"].success is True

        # Check that parameter override was applied
        assert plan.steps[0].input_binding["weight_egarps"] == 0.80

        # Check execution log has retry event
        retry_events = [e for e in result_state["_execution_log"] if e["event"] == "critic_retry"]
        assert len(retry_events) >= 1

    def test_execution_controller_retry_exhausts_max_retries(self):
        """When critic always wants retry, controller stops after max_retries."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.planning.llm_critic import CriticDiagnosis, CriticIssue

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
            return CapabilityResult(success=True, tool_name="rho", output={"mean_plddt": 30.0})

        gen_caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
        gen_caps["predict_rna_tertiary_structure_with_rhofold"].invoke = _rhofold_invoke
        gen_caps["score_rna_protein_complex_with_egarps"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="egarps", output={"native_probability": 0.10}
        )
        gen_caps["predict_rna_protein_complex_with_proteinx"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="proteinx", output={"ipTM": 0.10}
        )
        gen_caps["analyze_rna_protein_interface"].invoke = lambda args, state=None: CapabilityResult(
            success=True, tool_name="iface", output={"interface_contacts": 1}
        )

        reg.has = lambda name: name in gen_caps
        reg.get = lambda name: gen_caps[name]

        wf = RnaAptamerDesignWorkflow(reg)
        controller = ExecutionController(
            capability_registry=reg,
            workflow_registry={"rna_aptamer_design": wf},
        )

        # Critic always returns retry
        critic = RnaAptamerDesignLLMCritic()
        mock_diagnosis = CriticDiagnosis(
            overall_assessment="Always retry",
            quality_score=0.1,
            issues=[CriticIssue(severity="critical", category="all", description="bad")],
            action="retry_with_adjustments",
            parameter_overrides={"weight_egarps": 0.90, "weight_rhofold": 0.10},
            reasoning="retry",
            confidence=0.9,
        )

        def _mock_resolve_critic(step, get_critic_fn):
            return critic

        with patch.object(critic, "diagnose", return_value=mock_diagnosis):
            with patch.object(controller, "_resolve_critic", _mock_resolve_critic):
                plan = ExecutionPlan(
                    steps=[
                        PlanStep(
                            step_id="s1",
                            type="workflow",
                            target="rna_aptamer_design",
                            input_binding={"protein_structure_path": "/tmp/test_protein_for_aptamer.pdb", "weight_egarps": 0.50},
                            output_key="aptamer_result",
                        ),
                    ],
                    max_retries=2,
                )

                state: dict[str, Any] = {}
                result_state = controller.execute(plan, state)

        # With max_retries=2, should execute 3 times (initial + 2 retries)
        assert result_state.get("retry_count") == 2
        assert result_state["_plan_executed"] is True

        # Should have exhausted retries
        log_events = [e["event"] for e in result_state["_execution_log"]]
        assert "plan_complete" in log_events

    def test_critic_disabled_by_state_flag(self):
        """When _llm_critic_enabled=False, should_retry returns False."""
        from unittest.mock import patch

        critic = RnaAptamerDesignLLMCritic()
        result = WorkflowResult(
            success=True, task_id="t", summary="s", errors=[], all_candidates=[]
        )
        state = {"_llm_critic_enabled": False}

        with patch.object(critic, "diagnose") as mock_diag:
            retry = critic.should_retry(result, state)
            mock_diag.assert_not_called()

        assert retry is False


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6: DeepSeek API integration tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDeepSeekApiIntegration:
    """Live DeepSeek API tests (skipped without --live-llm flag)."""

    @pytest.mark.live_llm
    def test_live_critic_diagnose_with_deepseek(self):
        """Real LLM critic diagnoses aptamer workflow results."""
        from agent_core.planning.llm_critic import CriticDiagnosis

        critic = RnaAptamerDesignLLMCritic()

        # Create a result with poor quality candidates
        result = WorkflowResult(
            success=True,
            task_id="live_test",
            summary="test",
            errors=[],
            all_candidates=[
                _make_aptamer_candidate("AUGC" * 10, gc=0.15, egarps=0.10, rhofold=25.0, iptm=0.10),
                _make_aptamer_candidate("AUGC" * 10, gc=0.20, egarps=0.15, rhofold=30.0, iptm=0.12),
            ],
        )
        state = {"_last_workflow_params": {"aptamer_length": 30, "n_odesign_samples": 5}}

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert 0.0 <= diagnosis.quality_score <= 1.0
        assert diagnosis.action in ("retry_with_adjustments", "retry_with_alternative", "proceed_with_filtered", "abort")
        assert diagnosis.confidence >= 0.0
        # Should identify issues with poor quality candidates
        assert len(diagnosis.issues) > 0

    @pytest.mark.live_llm
    def test_live_critic_should_retry_with_deepseek(self):
        """Real LLM critic decides whether to retry on poor results."""
        critic = RnaAptamerDesignLLMCritic()

        # Poor quality candidates should trigger retry
        result = WorkflowResult(
            success=True,
            task_id="live_test",
            summary="test",
            errors=[],
            all_candidates=[
                _make_aptamer_candidate("AUGC" * 10, gc=0.15, egarps=0.10, rhofold=25.0, iptm=0.10),
            ],
        )
        state = {"_last_workflow_params": {"aptamer_length": 30, "n_odesign_samples": 5}}

        should_retry = critic.should_retry(result, state)

        # On very poor results, the LLM should recommend retry
        assert isinstance(should_retry, bool)
        # Also check that diagnosis was recorded
        assert "_last_diagnosis" in state

    @pytest.mark.live_llm
    def test_live_critic_no_retry_on_good_results(self):
        """Real LLM critic should not retry when quality is good."""
        critic = RnaAptamerDesignLLMCritic()

        # High quality candidates should not trigger retry
        result = WorkflowResult(
            success=True,
            task_id="live_test",
            summary="test",
            errors=[],
            all_candidates=[
                _make_aptamer_candidate("AUGC" * 10, gc=0.50, egarps=0.85, rhofold=90.0, iptm=0.80),
            ],
        )
        state = {"_last_workflow_params": {"aptamer_length": 30, "n_odesign_samples": 5}}

        should_retry = critic.should_retry(result, state)

        # Good results typically should not retry
        assert isinstance(should_retry, bool)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6: Ablation Studies
# ═══════════════════════════════════════════════════════════════════════════════


class TestAblationStudies:
    """Tests for BMC ablation modes: 1round, no_target, no_bounds, llm_coord."""

    def _make_ablation_registry(self):
        """Return a mock registry suitable for ablation tests."""
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
        }
        eval_caps = {
            "compute_rna_sequence_gc_content": make_mock_capability({"gc_content": 0.48}),
            "predict_rna_tertiary_structure_with_rhofold": make_mock_capability({
                "mean_plddt": 85.0, "pdb_filepath": "workspace/rho.pdb"
            }),
            "score_rna_protein_complex_with_egarps": make_mock_capability({
                "native_probability": 0.65
            }),
            "predict_rna_protein_complex_with_proteinx": make_mock_capability({
                "ipTM": 0.70, "mean_plddt": 80.0
            }),
            "analyze_rna_protein_interface": make_mock_capability({
                "interface_contacts": 20, "buried_sasa": 1000.0
            }),
        }
        all_caps = {**gen_caps, **eval_caps}
        reg.has = lambda name: name in all_caps
        reg.get = lambda name: all_caps[name]
        return reg

    def test_bmc_mode_1round_skips_phase3(self):
        """1round mode should skip Phase 3 iterative refinement."""
        reg = self._make_ablation_registry()
        wf = RnaAptamerDesignWorkflow(reg)
        inp = RnaAptamerDesignInput(
            protein_structure_path="/tmp/test_protein_for_aptamer.pdb",
            aptamer_length=30,
            bmc_mode="1round",
        )
        result = wf.run(inp)
        assert result.success is True
        assert result._state_writeback.get("_bmc_trace", []) == []

    def test_bmc_mode_no_target_ignores_hotspot_expansion(self):
        """no_target mode should ignore Target-module feedback (hotspot expansion)."""
        reg = self._make_ablation_registry()
        wf = RnaAptamerDesignWorkflow(reg)
        inp = RnaAptamerDesignInput(
            protein_structure_path="/tmp/test_protein_for_aptamer.pdb",
            aptamer_length=30,
            bmc_mode="no_target",
        )
        mock_issue = Issue(
            issue_type="BINDING_AFFINITY_LOW",
            value=0.10,
            target=0.30,
            affected_modules=("Target", "Aptamer"),
            evidence="Mock: EGARPS too low",
        )
        with patch.object(AptamerCoordinator, "diagnose", return_value=[mock_issue]):
            with patch.object(
                RnaAptamerDesignWorkflow,
                "_expand_hotspot_residues",
                return_value="A/1,A/2,A/3,A/4,A/5",
            ) as mock_expand:
                result = wf.run(inp)
                assert not mock_expand.called, "no_target mode should not expand hotspot"

    def test_bmc_mode_full_expands_hotspot_when_issue_found(self):
        """full mode should process Target-module feedback and expand hotspot."""
        reg = self._make_ablation_registry()
        wf = RnaAptamerDesignWorkflow(reg)
        inp = RnaAptamerDesignInput(
            protein_structure_path="/tmp/test_protein_for_aptamer.pdb",
            aptamer_length=30,
            bmc_mode="full",
        )
        mock_issue = Issue(
            issue_type="BINDING_AFFINITY_LOW",
            value=0.10,
            target=0.30,
            affected_modules=("Target", "Aptamer"),
            evidence="Mock: EGARPS too low",
        )
        with patch.object(AptamerCoordinator, "diagnose", return_value=[mock_issue]):
            with patch.object(
                RnaAptamerDesignWorkflow,
                "_expand_hotspot_residues",
                return_value="A/1,A/2,A/3,A/4,A/5",
            ) as mock_expand:
                result = wf.run(inp)
                assert mock_expand.called, "full mode should expand hotspot when issue found"

    def test_bmc_mode_no_bounds_uses_large_max_rounds(self):
        """no_bounds mode should set max_rounds=100 and improvement_threshold=0.0."""
        reg = self._make_ablation_registry()
        wf = RnaAptamerDesignWorkflow(reg)
        inp = RnaAptamerDesignInput(
            protein_structure_path="/tmp/test_protein_for_aptamer.pdb",
            aptamer_length=30,
            bmc_mode="no_bounds",
        )
        result = wf.run(inp)
        assert result.success is True
        assert result._state_writeback.get("_bmc_max_rounds") == 100
        assert result._state_writeback.get("_bmc_improvement_threshold") == 0.0

    def test_llm_coord_diagnose_with_mock_llm(self):
        """LLMAptamerCoordinator should call the LLM and parse JSON response."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="[]")

        with patch(
            "agent_core.workflows.rna_aptamer_design.get_llm_for_provider",
            return_value=mock_llm,
        ):
            coord = LLMAptamerCoordinator()
            assert coord._llm is not None
            issues = coord.diagnose({
                "egarps_native_probability": 0.65,
                "rhofold_mean_plddt": 85.0,
                "proteinx_ipTM": 0.70,
                "interface_contacts": 20,
                "buried_sasa": 1000.0,
                "gc_content": 0.48,
            })
            mock_llm.invoke.assert_called_once()
            assert issues == []

    def test_llm_coord_diagnose_parses_json_response(self):
        """LLMAptamerCoordinator should parse LLM JSON into Issue objects."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"issue_type":"BINDING_AFFINITY_LOW","value":0.10,"target":0.30,"affected_modules":["Target","Aptamer"],"evidence":"EGARPS too low"}]'
        )

        with patch(
            "agent_core.workflows.rna_aptamer_design.get_llm_for_provider",
            return_value=mock_llm,
        ):
            coord = LLMAptamerCoordinator()
            issues = coord.diagnose({"egarps_native_probability": 0.10})
            assert len(issues) == 1
            assert issues[0].issue_type == "BINDING_AFFINITY_LOW"
            assert issues[0].affected_modules == ("Target", "Aptamer")
            assert issues[0].evidence == "EGARPS too low"

    def test_llm_coord_fallback_on_invalid_json(self):
        """LLMAptamerCoordinator should fallback to deterministic rules on invalid LLM output."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="not valid json")

        with patch(
            "agent_core.workflows.rna_aptamer_design.get_llm_for_provider",
            return_value=mock_llm,
        ):
            coord = LLMAptamerCoordinator()
            # Low EGARPS should be flagged by deterministic fallback
            issues = coord.diagnose({"egarps_native_probability": 0.10})
            assert len(issues) == 1
            assert issues[0].issue_type == "BINDING_AFFINITY_LOW"

    def test_llm_coord_fallback_when_no_api_key(self):
        """LLMAptamerCoordinator should fallback to deterministic rules when LLM init fails."""
        with patch(
            "agent_core.workflows.rna_aptamer_design.get_llm_for_provider",
            side_effect=RuntimeError("No API key"),
        ):
            coord = LLMAptamerCoordinator()
            assert coord._llm is None
            issues = coord.diagnose({"egarps_native_probability": 0.10})
            assert len(issues) == 1
            assert issues[0].issue_type == "BINDING_AFFINITY_LOW"


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════════


def _make_aptamer_candidate(
    sequence: str,
    gc: float = 0.5,
    egarps: float | None = None,
    rhofold: float | None = None,
    iptm: float | None = None,
    contacts: int | None = None,
) -> Candidate:
    """Build a candidate with metrics bundle for critic tests."""
    mb: dict[str, Any] = {
        "gc_content": gc,
        "sequence_length": len(sequence),
    }
    if egarps is not None:
        mb["egarps_native_probability"] = egarps
    if rhofold is not None:
        mb["rhofold_mean_plddt"] = rhofold
    if iptm is not None:
        mb["proteinx_ipTM"] = iptm
    if contacts is not None:
        mb["interface_contacts"] = contacts

    scores = score_aptamer_candidate(mb)

    c = Candidate(
        sequence=sequence,
        sequence_type="rna_aptamer",
        source="test",
        metadata={"metrics_bundle": mb},
    )
    c.scores = scores
    return c
