#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 确保以下资源已在 Linux 服务器就位:
#    - ../../external_repos/CRISOT
#    - `cas-offinder` 已安装并可从 PATH 调用 (off-spec 模式需要)
#    - 参考基因组 FASTA 文件已下载到服务器本地 (off-spec 模式需要)
# 3. 说明:
#    - 本服务直接调用 CRISOT 底层 `crisot_modules.py`, 绕开上游 CLI 对 `xgboost` 的顶层硬依赖
#    - 可选环境变量:
#      - CRISOT_DEFAULT_REF_GENOME=/absolute/or/repo-relative/path/to/genome.fa
#        用于覆盖默认 hg38.fa（影响 /score 默认参考基因组）
#    - 当前已封装:
#      - /score
#      - /spec
#      - /off-spec
#      - /optimize
#    - `/off-spec` 和 `/optimize` 都需要 `cas-offinder` 和参考基因组 FASTA
#    - `crisot_fp` 暂未封装, 如需启用再单独补 `xgboost` 与训练模型
# 4. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate crisot_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8011
