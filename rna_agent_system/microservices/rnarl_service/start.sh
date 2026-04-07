#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 确保以下运行资源已在 Linux 服务器就位:
#    - ../../external_repos/RNARL
#    - ../../external_repos/RNARL/actor.pt
#    - ../../external_repos/RNARL/esm2_model_t33_650M_UR50D/
# 3. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rnarl_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8008
