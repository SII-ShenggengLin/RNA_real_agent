#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 确保以下运行资源已在 Linux 服务器就位:
#    - ../../external_repos/RNARL
#    - ../../../model_assets/rnarl/checkpoints/
#      例如: homo_mrna.pt, homo_circ.pt, Arabidopsis.pt, EscherichiaColi.pt, PC.pt, CR.pt, TK.pt
#    - ../../../model_assets/rnarl/esm2_t33_650M_UR50D/
# 3. 可选环境变量:
#    export RNARL_DEVICE=cuda:0
#    export RNARL_ESM2_MODEL_PATH=/absolute/path/to/esm2_t33_650M_UR50D
#    export RNARL_ACTOR_CHECKPOINT_PATH=/absolute/path/to/homo_mrna.pt
# 4. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rnarl_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8008
