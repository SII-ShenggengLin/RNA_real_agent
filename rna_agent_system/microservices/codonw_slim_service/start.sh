#!/bin/bash
set -e

# 请先执行: conda env create -f environment.yml
# 并确保子模块 rna_agent_system/external_repos/codonw-slim 已检出（含 C 源码）
# 再启动本服务:
#   bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate codonw_slim_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8018
