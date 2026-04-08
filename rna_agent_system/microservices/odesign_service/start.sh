#!/bin/bash
set -e

# 1. 首次创建基础环境:
#    conda env create -f environment.yml
# 2. 安装 ODesign 主依赖（Linux + CUDA 12.1）:
#    conda activate odesign_service_env
#    pip install -r ../../external_repos/ODesign/requirements.txt \
#      -f https://data.pyg.org/whl/torch-2.3.1+cu121.html
# 3. 准备运行时资源:
#    - ../../external_repos/ODesign/ckpt/odesign_base_na_rigid.pt
#    - ../../external_repos/ODesign/ckpt/oinvfold_rna.ckpt
#    - ../../external_repos/ODesign/data/components.v20240608.cif
#    - ../../external_repos/ODesign/data/components.v20240608.cif.rdkit_mol.pkl
# 4. 如需覆盖默认路径，可在启动前设置:
#    export ODESIGN_CKPT_ROOT=/absolute/path/to/ckpt
#    export ODESIGN_DATA_ROOT=/absolute/path/to/data
#    export ODESIGN_CUDA_VISIBLE_DEVICES=0
# 5. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate odesign_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8012
