#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 确保 GEMORNA 权重已拉取:
#    cd ../../external_repos/GEMORNA && git lfs pull
# 3. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gemorna_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8004
