#!/bin/bash
set -e

# 1. 首次创建环境:
#    conda env create -f environment.yml
# 2. 确保以下资源已在 Linux 服务器就位:
#    - ../../external_repos/CRISOT
#    - `cas-offinder` 已安装并可从 PATH 调用 (off-spec / optimize / rescore 模式需要)
#    - 参考基因组 FASTA 文件已下载到服务器本地 (off-spec / optimize / rescore 模式需要)
#    - trained_models.zip 已解压到 models/ (crisot-fp 模式需要)
# 3. 说明:
#    - 本服务直接调用 CRISOT 底层 `crisot_modules.py`, 绕开上游 CLI 对 `xgboost` 的顶层硬依赖
#    - 可选环境变量:
#      - CRISOT_DEFAULT_REF_GENOME=/absolute/or/repo-relative/path/to/genome.fa
#        用于覆盖默认 hg38.fa（影响 /score 默认参考基因组）
#    - 当前已封装全部 8 个原始 method:
#      - /score     (CRISOT-Score 单对打分)
#      - /scores    (CRISOT-Score 批量打分)
#      - /spec      (CRISOT-Spec CSV 特异性)
#      - /off-spec  (Cas-OFFinder 基因组搜索 + 特异性)
#      - /rescore   (基因组范围重新评分排序)
#      - /optimize  (CRISOT-Opti sgRNA 优化)
#      - /crisot-fp (CRISOT-FP XGBoost 预测)
#      - /gen-fp    (生成分子指纹编码)
#    - `/off-spec`, `/rescore`, `/optimize` 都需要 `cas-offinder` 和参考基因组 FASTA
# 4. 启动服务:
#    bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate crisot_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8011
