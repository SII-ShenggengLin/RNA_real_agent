#!/bin/bash
set -e

# 1. 在 Linux + NVIDIA GPU 服务器上创建环境:
#    conda env create -f environment.yml
# 2. 激活环境后安装与实际 torch/CUDA 版本匹配的 PyG wheel。
#    RNAsmol 官方依赖版本可参考:
#      torch-scatter==2.0.7
#      torch-sparse==0.6.9
#      torch-cluster==1.5.9
#      torch-spline-conv==1.2.1
#      torch-geometric==2.1.0
#    建议使用 https://data.pyg.org/ 对应的 wheel 源，而不是让 pip 回退到源码构建。
# 3. 准备 RNAsmol checkpoint:
#    - 默认放到 ../../external_repos/RNAsmol/saved_model/*.pt
#    - 或设置环境变量 RNASMOL_CHECKPOINT_PATH=/absolute/path/to/model.pt
# 4. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rnasmol_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8007
