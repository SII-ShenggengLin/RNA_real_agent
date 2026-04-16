#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 激活环境后，确保 RhoFold 包已安装:
#    cd ../../external_repos/RhoFold && python setup.py install
# 3. 如果自动下载 checkpoint 失败，请手动下载到:
#    ../../external_repos/RhoFold/pretrained/RhoFold_pretrained.pt
# 4. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rhofold_service_env

cd ../../external_repos/RhoFold
python setup.py install

cd ../../microservices/rhofold_service
python -m uvicorn main:app --host 0.0.0.0 --port 8005
