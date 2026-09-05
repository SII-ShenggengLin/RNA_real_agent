#!/bin/bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/microservices/odesign_service
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate odesign_service_env
exec python -m uvicorn resident_main:app --host 0.0.0.0 --port ${1:-18112}
