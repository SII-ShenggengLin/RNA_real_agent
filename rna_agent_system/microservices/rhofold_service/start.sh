#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 激活环境后，确保 RhoFold 包已安装:
#    cd ../../external_repos/RhoFold && python setup.py install
# 3. 确保以下任一 checkpoint 路径存在（微服务会按优先级自动查找，不会自动下载）:
#    ../../external_repos/RhoFold/pretrained/RhoFold_pretrained.pt
#    ../../external_repos/RhoFold/pretrained/rhofold_pretrained_params.pt
#    ../../external_repos/RhoFold/pretrained/model_20221010_params.pt
# 4. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rhofold_service_env

cd ../../external_repos/RhoFold
python setup.py install

cd ../../microservices/rhofold_service
python -m uvicorn main:app --host 0.0.0.0 --port 8005
