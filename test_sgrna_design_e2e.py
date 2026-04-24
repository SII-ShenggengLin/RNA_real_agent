#!/usr/bin/env python3
"""End-to-end test for sgrna_design tool wrapper and GPU verification."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system")
from agent_core.tools import design_sgrna_handle_with_crgpt


def get_gpu_processes():
    """Return list of python processes on GPU via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        return lines
    except Exception:
        return []


def check_service_pid_on_gpu(service_pid):
    """Check if a specific PID is using GPU."""
    procs = get_gpu_processes()
    for line in procs:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3 and parts[0] == str(service_pid):
            return True, line
    return False, None


def test_mcmc_mode():
    print("=" * 60)
    print("TEST 1: MCMC mode (default)")
    print("=" * 60)

    result = design_sgrna_handle_with_crgpt.func(
        seed_sequence="GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
        n_samples=5,
        mutation_number=22,
        temperature=20.0,
        max_overlap=21,
        sampling_mode="mcmc",
        device="cuda:0",
    )

    print(f"generated_count: {result['generated_count']}")
    print(f"best_sequence: {result['best_sequence']}")
    print(f"best_nn_score: {result['best_nn_score']}")
    print(f"best_log_likelihood: {result.get('best_log_likelihood')}")
    print(f"best_mutation_count: {result['best_mutation_count']}")
    print(f"sampling_mode: {result['sampling_mode']}")
    print(f"has_vienna_rna: {result['has_vienna_rna']}")
    print(f"output_fasta_filepath: {result['output_fasta_filepath']}")
    print(f"output_ali_filepath: {result['output_ali_filepath']}")
    print(f"summary_json_filepath: {result['summary_json_filepath']}")

    assert result["generated_count"] > 0, "MCMC mode should generate at least 1 candidate"
    assert result["sampling_mode"] == "mcmc"
    assert result["has_vienna_rna"] is True
    assert result["best_sequence"], "best_sequence should not be empty"
    assert result["best_nn_score"] != 0.0 or result["generated_count"] > 0
    assert Path(result["output_fasta_filepath"]).exists(), "FASTA output should exist"
    assert Path(result["summary_json_filepath"]).exists(), "JSON summary should exist"
    # MCMC mode should produce .ali alignment file
    assert result["output_ali_filepath"], "MCMC mode should produce .ali file"
    assert Path(result["output_ali_filepath"]).exists(), "ALI output should exist"

    print("\nMCMC mode test PASSED")
    return result


def test_naive_mode():
    print("\n" + "=" * 60)
    print("TEST 2: Naive mode")
    print("=" * 60)

    result = design_sgrna_handle_with_crgpt.func(
        seed_sequence="GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
        n_samples=5,
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
    print(f"best_mutation_count: {result['best_mutation_count']}")
    print(f"sampling_mode: {result['sampling_mode']}")
    print(f"output_fasta_filepath: {result['output_fasta_filepath']}")
    print(f"output_ali_filepath: {result['output_ali_filepath']!r}")

    assert result["generated_count"] > 0, "Naive mode should generate at least 1 candidate"
    assert result["sampling_mode"] == "naive"
    assert result["best_sequence"], "best_sequence should not be empty"
    assert Path(result["output_fasta_filepath"]).exists(), "FASTA output should exist"
    assert Path(result["summary_json_filepath"]).exists(), "JSON summary should exist"
    # Naive mode does not produce .ali file
    assert not result["output_ali_filepath"], f"Naive mode should NOT produce .ali file, got {result['output_ali_filepath']!r}"

    print("\nNaive mode test PASSED")
    return result


def test_filepath_input():
    print("\n" + "=" * 60)
    print("TEST 3: Filepath input mode")
    print("=" * 60)

    # Create a temp fasta file
    tmp_fasta = Path("/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/workspace/test_seed.fasta")
    tmp_fasta.write_text(
        ">seed\nGTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG\n"
    )

    result = design_sgrna_handle_with_crgpt.func(
        filepath=str(tmp_fasta),
        n_samples=3,
        mutation_number=15,
        temperature=20.0,
        sampling_mode="mcmc",
        device="cuda:0",
    )

    print(f"seed_sequence resolved: {result['seed_sequence']}")
    print(f"input_filepath: {result['input_filepath']}")
    print(f"generated_count: {result['generated_count']}")

    assert result["seed_sequence"] == "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG"
    assert result["input_filepath"] == str(tmp_fasta)
    assert result["generated_count"] > 0

    tmp_fasta.unlink(missing_ok=True)
    print("\nFilepath input test PASSED")
    return result


def test_score_endpoint():
    print("\n" + "=" * 60)
    print("TEST 4: Score endpoint")
    print("=" * 60)

    from agent_core.tools import score_sgrna_handle_with_crgpt
    result = score_sgrna_handle_with_crgpt.func(
        sequence="GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
        device="cuda:0",
    )

    print(f"normalized_sequence: {result['normalized_sequence']}")
    print(f"nn_score: {result['nn_score']}")
    print(f"log_likelihood: {result['log_likelihood']}")
    print(f"constraint_mutation_count: {result['constraint_mutation_count']}")

    assert result["nn_score"] > 0
    assert result["log_likelihood"] != 0.0
    assert result["constraint_mutation_count"] == 0
    print("\nScore endpoint test PASSED")
    return result


def test_gpu_usage():
    print("\n" + "=" * 60)
    print("TEST 5: GPU usage verification")
    print("=" * 60)

    # Find the service PID
    try:
        pgrep = subprocess.run(
            ["pgrep", "-f", "sgrna_design_service"],
            capture_output=True, text=True, timeout=5
        )
        pids = [p.strip() for p in pgrep.stdout.strip().split("\n") if p.strip()]
        print(f"Service PIDs: {pids}")
    except Exception as e:
        print(f"Could not find service PID: {e}")
        pids = []

    gpu_procs = get_gpu_processes()
    print(f"GPU processes: {gpu_procs}")

    # Check if any python process is on GPU
    python_on_gpu = any("python" in line.lower() for line in gpu_procs)
    print(f"Python process on GPU: {python_on_gpu}")

    # Also run nvidia-smi full output for device info
    try:
        smi = subprocess.run(
            ["nvidia-smi"],
            capture_output=True, text=True, timeout=10
        )
        print("\nnvidia-smi output:")
        print(smi.stdout)
    except Exception as e:
        print(f"nvidia-smi failed: {e}")

    assert python_on_gpu, "Expected a Python process running on GPU"
    print("\nGPU usage verification PASSED")


def main():
    print("Starting comprehensive sgrna_design end-to-end tests...")
    print(f"Project root: /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    test_mcmc_mode()
    test_naive_mode()
    test_filepath_input()
    test_score_endpoint()
    test_gpu_usage()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
