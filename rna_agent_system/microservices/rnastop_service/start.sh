#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 确保以下运行资源已在 Linux 服务器就位:
#    - ../../external_repos/RNASTOP
#    - ../../external_repos/RNASTOP/models/best_model_weights
#      或 ../../external_repos/RNASTOP/models/best_model_weights_withoutDNABERT
#    - ../../external_repos/RNASTOP/RNA-FM-main/pretrained/RNA-FM_pretrained.pth
#    - ../../external_repos/RNASTOP/DNABERT6/   (如果使用 best_model_weights)
# 3. 可选环境变量:
#    export RNASTOP_DEVICE=cuda:0
#    export RNASTOP_CHECKPOINT_PATH=/absolute/path/to/best_model_weights
#    export RNASTOP_RNAFM_PATH=/absolute/path/to/RNA-FM_pretrained.pth
#    export RNASTOP_DNABERT_PATH=/absolute/path/to/DNABERT6
# 4. 说明:
#    - 服务优先从本地 RNA-FM checkpoint 加载, 不依赖首次联网下载
#    - `best_model_weights_withoutstrloopdnabert` 不用于这个稳定性预测服务
#    - 本服务只封装 RNA 稳定性/降解预测, 不包含优化流程
# 5. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rnastop_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8009
