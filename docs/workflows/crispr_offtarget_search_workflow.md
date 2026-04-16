# 工作流：`crispr_offtarget_search`

## 基础链（最稳）

- **Step 1 输入校验**：sgRNA 文件可读；`genome_path` 可读；序列归一化后长度=23
- **Step 2 预处理**：无
- **Step 3 候选生成**：无
- **Step 4 评估**：`search_crispr_off_targets_with_crisot`（服务端调用 Cas-OFFinder + CRISOT）
- **Step 5 过滤**：可按 `off_target_count` 阈值
- **Step 6 排序**：按 `crisot_spec` 或多指标
- **Step 7 格式化**：输出 scored CSV 与 off-target 计数

