#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 确保以下运行资源已在 Linux 服务器就位:
#    - ../../external_repos/RNASTOP
#    - ../../external_repos/RNASTOP/models/best_model_weights_withoutDNABERT
#      或设置 RNASTOP_CHECKPOINT_PATH 指向作者下载的权重
# 3. 可选环境变量:
#    export RNASTOP_DEVICE=cuda:0
#    export RNASTOP_CHECKPOINT_PATH=/absolute/path/to/best_model_weights_withoutDNABERT
# 4. 说明:
#    - 首次启动 RNA-FM 可能需要联网下载其缓存
#    - 本服务只封装 RNA 稳定性/降解预测, 不包含优化流程
# 5. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rnastop_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8009
