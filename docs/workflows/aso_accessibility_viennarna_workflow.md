# 工作流：`aso_accessibility_viennarna`

## 基础链（最稳）

- **Step 1 输入校验**：`filepath` 可读；`region_start/region_end` 合法且在序列长度内
- **Step 2 预处理**：无
- **Step 3 候选生成**：无
- **Step 4 评估**：`compute_aso_target_accessibility_vienna`
- **Step 5 过滤**：无（阈值由调用方定义）
- **Step 6 排序**：可按 `mean_unpaired_prob_single_nt` 降序（越可及越高）
- **Step 7 格式化**：输出区域可及性摘要字段

