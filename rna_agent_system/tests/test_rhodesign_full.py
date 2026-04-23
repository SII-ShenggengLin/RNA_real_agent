"""End-to-end integration tests for RhoDesign microservice.

Runs both with-2D and without-2D modes against real checkpoints and example data.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import requests

SERVICE_URL = "http://127.0.0.1:8006/design/from-structure"
EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "external_repos" / "RhoDesign" / "example"


class TestRhoDesignEndToEnd(unittest.TestCase):
    """Full inference tests requiring GPU + checkpoints."""

    def _assert_common_response(self, resp: requests.Response, mode: str) -> dict:
        self.assertEqual(resp.status_code, 200, f"{mode} failed: {resp.text}")
        data = resp.json()
        self.assertIn("predicted_sequence", data, f"{mode}: missing predicted_sequence")
        self.assertIn("output_fasta_path", data, f"{mode}: missing output_fasta_path")
        self.assertIn("recovery_rate", data, f"{mode}: missing recovery_rate")
        self.assertTrue(len(data["predicted_sequence"]) > 0, f"{mode}: empty sequence")
        self.assertTrue(
            set(data["predicted_sequence"]).issubset({"A", "U", "G", "C", "X"}),
            f"{mode}: invalid chars in sequence: {data['predicted_sequence']}",
        )
        self.assertEqual(data["model"], "RhoDesign")
        self.assertTrue(Path(data["output_fasta_path"]).exists(), f"{mode}: FASTA not on disk")
        return data

    def test_without_2d_mode(self) -> None:
        """PDB-only mode should use no_ss_apexp_best.pth and default temp=1.0."""
        payload = {
            "pdb_path": str(EXAMPLE_DIR / "2zh6_B.pdb"),
            "device": 0,
            # temperature defaults to 1.0 for without-2D
        }
        resp = requests.post(SERVICE_URL, json=payload, timeout=300)
        data = self._assert_common_response(resp, "without-2D")
        self.assertFalse(data["used_secondary_structure"])
        self.assertIn("no_ss_apexp_best.pth", data["checkpoint_path"])
        print("\n[without-2D] predicted_sequence:", data["predicted_sequence"])
        print("[without-2D] recovery_rate:", data["recovery_rate"])
        print("[without-2D] temperature_used:", data.get("temperature_used"))
        print("[without-2D] output_fasta_path:", data["output_fasta_path"])

    def test_with_2d_mode(self) -> None:
        """PDB + contact-map mode should use ss_apexp_best.pth and default temp=1e-5."""
        payload = {
            "pdb_path": str(EXAMPLE_DIR / "2zh6_B.pdb"),
            "secondary_structure_path": str(EXAMPLE_DIR / "2zh6_B.npy"),
            "device": 0,
            # temperature defaults to 1e-5 for with-2D
        }
        resp = requests.post(SERVICE_URL, json=payload, timeout=300)
        data = self._assert_common_response(resp, "with-2D")
        self.assertTrue(data["used_secondary_structure"])
        self.assertIn("ss_apexp_best.pth", data["checkpoint_path"])
        print("\n[with-2D] predicted_sequence:", data["predicted_sequence"])
        print("[with-2D] recovery_rate:", data["recovery_rate"])
        print("[with-2D] temperature_used:", data.get("temperature_used"))
        print("[with-2D] output_fasta_path:", data["output_fasta_path"])

    def test_with_2d_explicit_temperature(self) -> None:
        """User-supplied temperature should be honored."""
        payload = {
            "pdb_path": str(EXAMPLE_DIR / "2zh6_B.pdb"),
            "secondary_structure_path": str(EXAMPLE_DIR / "2zh6_B.npy"),
            "temperature": 0.5,
            "device": 0,
        }
        resp = requests.post(SERVICE_URL, json=payload, timeout=300)
        data = self._assert_common_response(resp, "with-2D-explicit-temp")
        self.assertAlmostEqual(data["temperature_used"], 0.5, places=5)
        print("\n[with-2D-explicit-temp] temperature_used:", data["temperature_used"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
