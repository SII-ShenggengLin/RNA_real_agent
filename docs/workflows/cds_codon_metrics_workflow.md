# 工作流：`cds_codon_metrics`

## 基础链（最稳）

- **Step 1 输入校验**：CDS 文件可读；序列为 DNA/RNA 字母；建议调用方确保 in-frame
- **Step 2 预处理**：无
- **Step 3 候选生成**：无
- **Step 4 评估**：`analyze_cds_codon_metrics_with_codonw_slim`
- **Step 5 过滤**：无
- **Step 6 排序**：可按 `cai_score` 降序（若用于对比多个 CDS）
- **Step 7 格式化**：输出指标摘要 + `metrics_json_filepath`

