#!/usr/bin/env python3
"""Final end-to-end test for sgrna_design tool wrapper."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system")
from agent_core.tools import design_sgrna_handle_with_crgpt


def get_gpu_processes():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        return [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
    except Exception:
        return []


def test_naive_mode():
    print("=" * 60)
    print("TEST 1: Naive mode via Python tool wrapper")
    print("=" * 60)

    result = design_sgrna_handle_with_crgpt.func(
        seed_sequence="GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
        n_samples=3,
        mutation_number=22,
        temperature=1.0,
        max_overlap=21,
        sampling_mode="naive",
        device="cuda:0",
    )

    print(f"generated_count: {result['generated_count']}")
    print(f"best_sequence: {result['best_sequence']}")
    print(f"best_nn_score: {result['best_nn_score']}")
    print(f"best_log_likelihood: {result.get('best_log_likelihood')}")
    print(f"sampling_mode: {result['sampling_mode']}")
    print(f"device: {result['device']}")
    print(f"output_fasta: {result['output_fasta_filepath']}")
    print(f"output_ali: {result['output_ali_filepath']!r}")

    assert result["generated_count"] == 3
    assert result["sampling_mode"] == "naive"
    assert result["best_sequence"]
    # workspace paths are relative to rna_agent_system; also check raw paths
    fasta_ok = Path(result["output_fasta_filepath"]).exists() or (Path("/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system") / result["output_fasta_filepath"]).exists()
    summary_ok = Path(result["summary_json_filepath"]).exists() or (Path("/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system") / result["summary_json_filepath"]).exists()
    assert fasta_ok, f"FASTA not found: {result['output_fasta_filepath']}"
    assert summary_ok, f"Summary not found: {result['summary_json_filepath']}"
    assert not result["output_ali_filepath"], f"naive mode has no .ali, got {result['output_ali_filepath']!r}"
    print("PASSED")


def test_filepath_input():
    print("\n" + "=" * 60)
    print("TEST 2: Filepath input mode")
    print("=" * 60)

    tmp = Path("/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/workspace/test_seed.fasta")
    tmp.write_text(">seed\nGTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG\n"
    )

    result = design_sgrna_handle_with_crgpt.func(
        filepath=str(tmp),
        n_samples=2,
        mutation_number=15,
        temperature=1.0,
        sampling_mode="naive",
        device="cuda:0",
    )

    print(f"seed_sequence: {result['seed_sequence']}")
    print(f"input_filepath: {result['input_filepath']}")
    print(f"generated_count: {result['generated_count']}")

    assert result["seed_sequence"] == "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG"
    assert result["input_filepath"] == str(tmp)
    assert result["generated_count"] == 2
    fasta_ok = Path(result["output_fasta_filepath"]).exists() or (Path("/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system") / result["output_fasta_filepath"]).exists()
    assert fasta_ok, f"FASTA not found: {result['output_fasta_filepath']}"
    tmp.unlink(missing_ok=True)
    print("PASSED")


def test_mcmc_via_curl():
    print("\n" + "=" * 60)
    print("TEST 3: MCMC mode via direct HTTP API (curl)")
    print("=" * 60)

    payload = {
        "seed_sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
        "n_samples": 3,
        "mutation_number": 22,
        "temperature": 20.0,
        "max_overlap": 21,
        "sampling_mode": "mcmc",
        "device": "cuda:0",
    }

    result = subprocess.run(
        ["curl", "-s", "-X", "POST", "http://127.0.0.1:8017/design",
         "-H", "Content-Type: application/json", "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=300
    )

    data = json.loads(result.stdout)
    print(f"generated_count: {data['generated_count']}")
    print(f"sampling_mode: {data['sampling_mode']}")
    print(f"has_vienna_rna: {data['has_vienna_rna']}")
    print(f"output_ali_path: {data.get('output_ali_path')}")

    assert data["generated_count"] > 0
    assert data["sampling_mode"] == "mcmc"
    assert data["has_vienna_rna"] is True
    assert data.get("output_ali_path")
    assert Path(data["output_fasta_path"]).exists()
    print("PASSED")


def test_gpu_usage():
    print("\n" + "=" * 60)
    print("TEST 4: GPU usage verification")
    print("=" * 60)

    gpu_procs = get_gpu_processes()
    print("GPU processes:")
    for p in gpu_procs:
        print(f"  {p}")

    sgrna_on_gpu = any("sgrna" in p.lower() or "sgrna_design_service_env" in p for p in gpu_procs)
    python_on_gpu = any("python" in p.lower() for p in gpu_procs)

    print(f"\nPython process on GPU: {python_on_gpu}")
    print(f"sgrna_design_service on GPU: {sgrna_on_gpu}")

    assert python_on_gpu, "Expected Python process on GPU"
    print("PASSED")


def test_score_via_curl():
    print("\n" + "=" * 60)
    print("TEST 5: Score endpoint via curl")
    print("=" * 60)

    payload = {
        "sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
        "device": "cuda:0",
    }
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", "http://127.0.0.1:8017/score",
         "-H", "Content-Type: application/json", "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=60
    )
    data = json.loads(result.stdout)
    print(f"nn_score: {data['nn_score']}")
    print(f"log_likelihood: {data['log_likelihood']}")
    print(f"constraint_mutation_count: {data['constraint_mutation_count']}")

    assert "nn_score" in data
    assert "log_likelihood" in data
    assert data["constraint_mutation_count"] == 0
    print("PASSED")


def main():
    print(f"Starting sgrna_design comprehensive tests at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Service URL: http://127.0.0.1:8017")
    print()

    test_naive_mode()
    test_filepath_input()
    test_mcmc_via_curl()
    test_score_via_curl()
    test_gpu_usage()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
