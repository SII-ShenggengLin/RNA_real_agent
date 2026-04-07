#!/bin/bash
set -e

# 1. 在 Linux 服务器创建 GPU 环境:
#    conda env create -f environment.yml
# 2. 激活后安装 CUDA 版 PyG wheel:
#    conda activate gernabind_service_env
#    bash install_pyg_gpu.sh
#    不建议让 pip 回退到源码构建。
# 3. 准备 GerNA-Bind affinity checkpoint:
#    bash ../../external_repos/GerNA-Bind/Model/get_weights.sh
# 4. 如果要启用 binding-site 端点, 还需要额外准备:
#    ../../external_repos/GerNA-Bind/Model/Hariboss_Model_baseline.pth
#    或设置 GERNABIND_BINDING_SITE_CHECKPOINT_PATH=/absolute/path/to/Hariboss_Model_baseline.pth
# 5. 确保 RhoFold 微服务已经启动:
#    默认使用 http://127.0.0.1:8005/predict
#    如有需要可设置 GERNABIND_RHOFOLD_URL 覆盖
# 6. 可选环境变量:
#    export GERNABIND_DEVICE=cuda:0
#    export GERNABIND_AFFINITY_CHECKPOINT_PATH=/absolute/path/to/Robin_random.pth
#    export GERNABIND_BINDING_SITE_CHECKPOINT_PATH=/absolute/path/to/Hariboss_Model_baseline.pth
#    export GERNABIND_RHOFOLD_URL=http://127.0.0.1:8005/predict
# 7. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gernabind_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8010
