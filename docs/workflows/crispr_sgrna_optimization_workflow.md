# 工作流：`crispr_sgrna_optimization`

## 基础链（最稳）

- **Step 1 输入校验**：sgRNA 文件可读；`genome_path` 可读；参数范围合法
- **Step 2 预处理**：无
- **Step 3 候选生成**：`optimize_sgrna_with_crisot`（服务端生成并评估候选）
- **Step 4 评估**：已包含在 optimize 输出（best score/spec/delta）
- **Step 5 过滤**：`optimized_available` 为 false 时直接判定无优化结果
- **Step 6 排序**：无（输出已为 best）
- **Step 7 格式化**：输出 best sgrna 与 CSV/FASTA 产物路径

