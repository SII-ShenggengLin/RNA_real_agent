# 工作流：`blastn_similarity_search`

## 基础链（最稳）

- **Step 1 输入校验**：query 文件可读；`subject_fasta_path` 与 `subject_db` 二选一
- **Step 2 预处理**：无（服务端会把 U→T 归一化用于 blastn）
- **Step 3 候选生成**：无
- **Step 4 评估**：`run_blastn_similarity_search`
- **Step 5 过滤**：可按 `hit_count==0` 或 `perc_identity` 等规则
- **Step 6 排序**：无（单次查询）；或按 hits 字段做下游排序
- **Step 7 格式化**：输出 `tabular_tsv_filepath` 与审计命令字段

