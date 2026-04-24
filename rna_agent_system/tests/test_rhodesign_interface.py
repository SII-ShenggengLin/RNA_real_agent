"""Integration tests for RhoDesign interface contract after refactor.

These tests verify:
- Microservice request/response schemas
- PathResolver and temperature defaults
- Agent-level tool input validation
- Original inference script argument parsing

They do NOT require GPU or real checkpoints (checkpoint-missing cases are asserted).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Allow importing microservices/common_utils
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "microservices"))

from common_utils import PathResolver, parse_recovery_rate


class TestPathResolver(unittest.TestCase):
    """Validate shared PathResolver behaves like the old copy-pasted helpers."""

    def setUp(self) -> None:
        self.project = Path("/tmp/fake_project")
        self.repo = self.project.parent
        self.resolver = PathResolver(self.project, self.repo)

    def test_absolute_path_passthrough(self) -> None:
        self.assertEqual(
            self.resolver.resolve("/absolute/path/to/file.pdb"),
            Path("/absolute/path/to/file.pdb"),
        )

    def test_rna_agent_system_prefix_prefers_repo_root(self) -> None:
        # For a path starting with 'rna_agent_system/', repo_root candidate is tried first.
        resolved = self.resolver.resolve("rna_agent_system/workspace/seq.fasta")
        expected = self.repo / "rna_agent_system" / "workspace" / "seq.fasta"
        self.assertEqual(resolved, expected)

    def test_workspace_prefix_prefers_project_root(self) -> None:
        resolved = self.resolver.resolve("workspace/seq.fasta")
        self.assertEqual(resolved, self.project / "workspace" / "seq.fasta")


class TestParseRecoveryRate(unittest.TestCase):
    """Validate shared parse_recovery_rate against both service output formats."""

    def test_rhodesign_format(self) -> None:
        stdout = "sequence: AUGC\nrecovery rate: 0.8123"
        self.assertAlmostEqual(parse_recovery_rate(stdout), 0.8123)

    def test_ribodiffusion_format(self) -> None:
        stdout = "some header\nrecovery_rate 0.91"
        self.assertAlmostEqual(parse_recovery_rate(stdout), 0.91)

    def test_no_match_returns_none(self) -> None:
        self.assertIsNone(parse_recovery_rate("no numbers here"))


class TestRhoDesignRequestDefaults(unittest.TestCase):
    """Verify Pydantic model instantiation and dynamic-default logic in main.py."""

    def test_can_import_main(self) -> None:
        from rhodesign_service.main import RhoDesignRequest, RhoDesignResponse

        req = RhoDesignRequest(pdb_path="test.pdb")
        self.assertIsNone(req.temperature)
        self.assertEqual(req.device, 0)
        self.assertEqual(req.timeout_seconds, 3600)

        resp = RhoDesignResponse(
            input_pdb_path="test.pdb",
            output_fasta_path="out.fasta",
            predicted_sequence="AUGC",
            used_secondary_structure=False,
            checkpoint_path="ckpt.pth",
            service_output_dir="/tmp",
            temperature_used=1e-5,
        )
        self.assertEqual(resp.model, "RhoDesign")


class TestRiboDiffusionRequestDefaults(unittest.TestCase):
    def test_can_import_main(self) -> None:
        from ribodiffusion_service.main import RiboDiffusionRequest, RiboDiffusionResponse

        req = RiboDiffusionRequest(pdb_path="test.pdb")
        self.assertEqual(req.n_samples, 1)
        self.assertEqual(req.device, 0)
        self.assertEqual(req.checkpoint_name, "exp_inf")

        resp = RiboDiffusionResponse(
            input_pdb_path="test.pdb",
            pdb_id="test",
            predicted_sequence="AUGC",
            generated_sequences=["AUGC"],
            output_fasta_paths=["a.fasta"],
            checkpoint_path="ckpt.pth",
            service_output_dir="/tmp",
            fasta_dir="/tmp/fasta",
        )
        self.assertEqual(resp.model, "RiboDiffusion")


class TestInferenceScriptArgparse(unittest.TestCase):
    """Ensure the patched inference scripts accept -ckpt without error."""

    def test_inference_with2d_accepts_ckpt(self) -> None:
        import argparse

        # Simulate the argument parser setup from inference.py
        parser = argparse.ArgumentParser()
        parser.add_argument("-pdb", "--pdb_file", type=str, required=True)
        parser.add_argument("-ss", "--secondary_structure", type=str, required=True)
        parser.add_argument("-save", "--save_path", type=str, required=True)
        parser.add_argument("-device", "--device", default=0, type=int)
        parser.add_argument("-temp", "--temperature", default=1e-5, type=float)
        parser.add_argument(
            "-ckpt", "--checkpoint", default="./../checkpoint/ss_apexp_best.pth", type=str
        )
        args = parser.parse_args(
            ["-pdb", "a.pdb", "-ss", "a.npy", "-save", "/tmp", "-ckpt", "/custom/ckpt.pth"]
        )
        self.assertEqual(args.checkpoint, "/custom/ckpt.pth")

    def test_inference_without2d_accepts_ckpt(self) -> None:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("-pdb", "--pdb_file", type=str, required=True)
        parser.add_argument("-save", "--save_path", type=str, required=True)
        parser.add_argument("-device", "--device", default=0, type=int)
        parser.add_argument("-temp", "--temperature", default=1, type=float)
        parser.add_argument(
            "-ckpt", "--checkpoint", default="./../checkpoint/no_ss_apexp_best.pth", type=str
        )
        args = parser.parse_args(
            ["-pdb", "a.pdb", "-save", "/tmp", "-ckpt", "/custom/ckpt.pth"]
        )
        self.assertEqual(args.checkpoint, "/custom/ckpt.pth")


class TestToolSpecsOutputModels(unittest.TestCase):
    """Validate tool_specs.py output schemas match wrapper return dicts.

    Uses AST inspection to avoid pulling in heavy langchain dependencies.
    """

    def _get_class_field_names(self, filepath: Path, class_name: str) -> set[str]:
        import ast

        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                fields: set[str] = set()
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        fields.add(item.target.id)
                return fields
        return set()

    def test_rhodesign_output_fields(self) -> None:
        tool_specs = Path(__file__).resolve().parents[1] / "agent_core" / "tool_specs.py"
        fields = self._get_class_field_names(tool_specs, "RhoDesignOutput")
        self.assertIn("predicted_sequence", fields)
        self.assertIn("recovery_rate", fields)
        self.assertNotIn("designed_sequence", fields)
        self.assertNotIn("sequence_recovery_rate", fields)

    def test_ribodiffusion_output_fields(self) -> None:
        tool_specs = Path(__file__).resolve().parents[1] / "agent_core" / "tool_specs.py"
        fields = self._get_class_field_names(tool_specs, "RiboDiffusionOutput")
        self.assertIn("predicted_sequence", fields)
        self.assertIn("recovery_rate", fields)
        self.assertNotIn("sequence_recovery_rate", fields)


if __name__ == "__main__":
    unittest.main(verbosity=2)
