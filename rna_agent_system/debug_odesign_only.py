#!/usr/bin/env python3
"""Debug script: test ODesign inference + sequence extraction directly."""
import sys
import json
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

# Use an existing ODesign JSON
json_path = "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/workspace/odesign_aptamer_input_bb2d4f8cf6.json"

print(f"\n=== Testing run_odesign_inference ===")
print(f"JSON path: {json_path}")

cap = cap_reg.get("run_odesign_inference")
cap_result = cap.invoke(
    {
        "input_json_filepath": json_path,
        "design_modality": "rna",
        "seeds_json": json.dumps([42]),
        "n_sample": 1,
        "infer_model_name": "odesign_base_na_rigid",
    },
)

print(f"cap_result.success: {cap_result.success}")
print(f"cap_result.error: {cap_result.error}")
print(f"cap_result.output keys: {cap_result.output.keys() if cap_result.output else 'None'}")

if cap_result.success and cap_result.output:
    prediction_paths = cap_result.output.get("prediction_filepaths", [])
    print(f"prediction_filepaths: {prediction_paths}")
    print(f"prediction_count: {cap_result.output.get('prediction_count', 0)}")
    
    if prediction_paths:
        print(f"\n=== Testing extract_rna_sequence_from_cif ===")
        for path in prediction_paths:
            abs_path = Path(path)
            if not abs_path.is_absolute():
                abs_path = PROJECT_ROOT / path
            print(f"Testing path: {abs_path}")
            
            cap2 = cap_reg.get("extract_rna_sequence_from_cif")
            cap2_result = cap2.invoke({"cif_filepath": str(abs_path)})
            print(f"  success: {cap2_result.success}")
            print(f"  error: {cap2_result.error}")
            print(f"  sequence: {cap2_result.output.get('sequence', 'N/A') if cap2_result.output else 'N/A'}")
