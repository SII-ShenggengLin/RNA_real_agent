#!/bin/bash
set -e

# 1. 创建独立 GPU 环境:
#    conda env create -f environment.gpu.yml
# 2. 安装与 torch 2.1 + cu118 匹配的 PyG wheel:
#    conda activate rnasmol_service_gpu_env
#    pip install --no-cache-dir pyg_lib torch_scatter torch_sparse torch_cluster torch_spline_conv \
#      -f https://data.pyg.org/whl/torch-2.1.0+cu118.html
#    pip install --no-cache-dir torch-geometric==2.5.0
# 3. 指定 GPU 设备:
#    export RNASMOL_DEVICE=cuda:0
# 4. 如需指定 checkpoint:
#    export RNASMOL_CHECKPOINT_PATH=/absolute/path/to/model.pt
# 5. 启动服务:
#    bash start_gpu.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rnasmol_service_gpu_env
export RNASMOL_DEVICE="${RNASMOL_DEVICE:-cuda:0}"
python -m uvicorn main:app --host 0.0.0.0 --port 8007
