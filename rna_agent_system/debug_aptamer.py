#!/usr/bin/env python3
"""Debug script for rna_aptamer_design workflow."""
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry
from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput, RnaAptamerDesignWorkflow

print("Building executor...")
executor = build_default_tool_registry(include_demo=False)
tool_exec = ToolExecutor(executor)

print("Building capability registry...")
cap_reg = build_default_capability_registry(tool_exec)

inp_dict = {
    "protein_sequence": "KETAAAKFERQHMDSSTSAASSSNYCNQMMKSRNLTKDRCKPVNTFVHESLADVQAVCSQKNVACKNGQTNCYQSYSTMSITDCRETGSSKYPNCAYKTTQANKHIIVACEGNPYVPVHFDASV",
    "chain_id": "A",
    "aptamer_length": 30,
    "hotspot_residues": None,
    "n_odesign_samples": 1,
    "odesign_seeds": [42],
    "weight_egarps": 0.5,
    "weight_rhofold": 0.5,
}

print("Creating input object...")
inp_obj = RnaAptamerDesignInput(**inp_dict)

print("Creating workflow...")
wf = RnaAptamerDesignWorkflow(cap_reg)

print("Running workflow...")
try:
    result = wf.run(inp_obj)
    print(f"\n=== RESULT ===")
    print(f"success: {result.success}")
    print(f"errors: {result.errors}")
    print(f"candidates: {len(result.all_candidates)}")
    for i, cand in enumerate(result.all_candidates):
        print(f"  Candidate {i}: {cand.sequence[:50]}...")
except Exception as e:
    print(f"\n=== EXCEPTION ===")
    print(f"{type(e).__name__}: {e}")
    traceback.print_exc()
