#!/bin/bash
set -e

# 请先执行: conda env create -f environment.yml
# 再启动本服务:
# bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate viennarna_fold_env
python -m uvicorn main:app --host 0.0.0.0 --port 8003
