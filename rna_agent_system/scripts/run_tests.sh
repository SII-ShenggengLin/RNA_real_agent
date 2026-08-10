#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Tiered test runner for RNA Agent System
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

MODE="${1:-fast}"

# Common markers excluded by default in pytest.ini:
#   integration, live_llm, slow, known_issue
# This script layers on top of those defaults.

case "${MODE}" in
  fast)
    # Core unit tests: < 5 seconds
    # Layer 0 CPU tools + specs + registry + models + routing + memory
    echo "=== FAST tests (core unit tests) ==="
    python -m pytest \
      tests/test_compute_*.py \
      tests/test_tool_specs_output_models.py \
      tests/test_tool_registry_executor.py \
      tests/test_session_memory.py \
      tests/test_workspace_manager.py \
      tests/test_workflow_models.py \
      tests/test_file_manager_session.py \
      tests/test_partial_retry.py \
      tests/test_shuffle_cds_junction_codons.py \
      tests/test_viennarna_wrapper_output.py \
      tests/test_mrna_workflow.py \
      tests/test_sirna_design_workflow.py \
      -q --tb=short
    ;;

  medium)
    # Core + selected workflow / mock BMC / aptamer / rhodesign interface
    # Target: < 30 seconds
    echo "=== MEDIUM tests (fast + workflow mocks + interfaces) ==="
    python -m pytest \
      tests/test_compute_*.py \
      tests/test_tool_specs_output_models.py \
      tests/test_tool_registry_executor.py \
      tests/test_session_memory.py \
      tests/test_workspace_manager.py \
      tests/test_workflow_models.py \
      tests/test_file_manager_session.py \
      tests/test_partial_retry.py \
      tests/test_shuffle_cds_junction_codons.py \
      tests/test_viennarna_wrapper_output.py \
      tests/test_mrna_workflow.py \
      tests/test_sirna_design_workflow.py \
      tests/test_rna_aptamer_design.py \
      tests/test_bmc_workflow_e2e_mock.py \
      tests/test_mrna_cds_design.py \
      tests/test_full_length_mrna_design.py \
      tests/test_workflow_baseline_eval.py \
      tests/test_workflow_observability.py \
      tests/test_rhodesign_interface.py \
      -q --tb=short
    ;;

  full)
    # All tests except integration, live_llm, slow, known_issue
    # May take 2-5 minutes depending on hardware
    echo "=== FULL tests (all non-integration/non-live_llm) ==="
    python -m pytest tests/ -q --tb=short
    ;;

  gpu)
    # Tests that exercise GPU microservices (requires GPU + services up)
    echo "=== GPU tests (RhoDesign, CRGPT, etc.) ==="
    python -m pytest tests/ -m "gpu or slow" -q --tb=short
    ;;

  integration)
    # All tests including integration and slow
    # Requires all microservices + DeepSeek API balance
    echo "=== INTEGRATION tests (everything) ==="
    python -m pytest tests/ -m "integration or slow or live_llm or known_issue" -q --tb=short
    ;;

  *)
    echo "Usage: bash scripts/run_tests.sh [fast|medium|full|gpu|integration]"
    echo ""
    echo "  fast        – Core unit tests (~2s, 160+ tests)"
    echo "  medium      – + workflow mocks + interfaces (~30s, 250+ tests)"
    echo "  full        – All non-integration tests (~2-5min)"
    echo "  gpu         – GPU-dependent service tests"
    echo "  integration – Full suite including live services + LLM"
    exit 1
    ;;
esac
