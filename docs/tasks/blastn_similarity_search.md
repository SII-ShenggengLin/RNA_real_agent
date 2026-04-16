# 任务：`blastn_similarity_search`

## 任务目标

对 query 序列执行 blastn 相似性搜索，输出 hit 数与 tabular TSV 结果。

## 输入 / 输出

- **输入**：query 文件路径 + subject（`subject_fasta_path` 或 `subject_db` 二选一）
- **输出**：`hit_count`、`tabular_tsv_filepath`、审计命令字段

## 前置条件

- BLAST+ 微服务（端口 8019）与服务器侧 BLAST+ 可执行文件可用

## 工具

- `run_blastn_similarity_search`

## 标准工具链

见 `docs/workflows/blastn_similarity_search_workflow.md`。

