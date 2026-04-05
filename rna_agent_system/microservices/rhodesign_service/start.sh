#!/bin/bash
set -e

# 1. 在 Linux + NVIDIA GPU 服务器上首次创建环境:
#    conda env create -f environment.yml
# 2. 激活环境后单独安装 PyG 预编译 wheel:
#    conda activate rhodesign_service_env
#    pip install --no-cache-dir \
#      torch-scatter==2.1.2 \
#      torch-sparse==0.6.18 \
#      torch-cluster==1.6.3 \
#      torch-spline-conv==1.2.2 \
#      -f https://data.pyg.org/whl/torch-1.12.0+cu113.html
#    pip install --no-cache-dir torch-geometric==2.5.0
# 3. 确认 RhoDesign 权重已就位:
#    ../../external_repos/RhoDesign/checkpoint/ss_apexp_best.pth
#    ../../external_repos/RhoDesign/checkpoint/no_ss_apexp_best.pth
# 4. 如 PyG 安装仍失败，请先执行:
#    python -c "import torch; print(torch.__version__, torch.version.cuda)"
#    再改用与实际版本匹配的 data.pyg.org wheel 地址
# 5. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rhodesign_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8006
