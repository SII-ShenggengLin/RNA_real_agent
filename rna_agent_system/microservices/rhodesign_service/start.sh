#!/bin/bash
set -e

# 1. 在 Linux + NVIDIA GPU 服务器上首次创建环境:
#    conda env create -f environment.yml
# 2. 确认 RhoDesign 权重已就位:
#    ../../external_repos/RhoDesign/checkpoint/ss_apexp_best.pth
#    ../../external_repos/RhoDesign/checkpoint/no_ss_apexp_best.pth
# 3. 如 torch-geometric 相关包安装失败，请按服务器上的 PyTorch/CUDA 版本
#    重新安装与其匹配的 torch-scatter / torch-sparse / torch-cluster / torch-geometric
# 4. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rhodesign_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8006
