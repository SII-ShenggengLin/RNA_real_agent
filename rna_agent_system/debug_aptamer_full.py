#!/usr/bin/env python3
"""Debug script: simulate _generate_aptamer_module with existing ODesign output."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry

print("Building executor...")
executor = build_default_tool_registry(include_demo=False)
tool_exec = ToolExecutor(executor)

print("Building capability registry...")
cap_reg = build_default_capability_registry(tool_exec)

# Simulate what _run_odesign_inference returns
# Use an existing ODesign JSON that was already run
json_path = "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/workspace/odesign_aptamer_input_bb2d4f8cf6.json"

print(f"\n=== Step 1: run_odesign_inference ===")
cap = cap_reg.get("run_odesign_inference")
cap_result = cap.invoke(
    {
        "input_json_filepath": json_path,
        "design_modality": "rna",
        "seeds_json": "[42]",
        "n_sample": 1,
        "infer_model_name": "odesign_base_na_rigid",
    },
)

print(f"success: {cap_result.success}")
print(f"error: {cap_result.error}")

if cap_result.success:
    prediction_paths = cap_result.output.get("prediction_filepaths", [])
    print(f"prediction_filepaths: {prediction_paths}")
    print(f"prediction_count: {cap_result.output.get('prediction_count', 0)}")
    
    print(f"\n=== Step 2: extract sequences ===")
    from agent_core.tools import extract_rna_sequence_from_cif
    
    sequences = []
    for path in prediction_paths:
        if not path:
            continue
        abs_path = Path(path)
        if not abs_path.is_absolute():
            abs_path = PROJECT_ROOT / path
        print(f"Extracting from: {abs_path}")
        
        try:
            result = extract_rna_sequence_from_cif.func(str(abs_path))
            seq = result.get("sequence", "")
            if seq:
                sequences.append(seq)
                print(f"  -> sequence: {seq}")
            else:
                print(f"  -> empty sequence")
        except Exception as e:
            print(f"  -> ERROR: {type(e).__name__}: {e}")
    
    print(f"\nTotal sequences: {len(sequences)}")
else:
    print("\nODesign inference failed - cannot extract sequences")
