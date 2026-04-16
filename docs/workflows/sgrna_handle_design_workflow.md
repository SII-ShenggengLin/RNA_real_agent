# 工作流：`sgrna_handle_design`

## 基础链（最稳）

- **Step 1 输入校验**：seed 文件可读；长度与字符集满足服务/ wrapper 要求
- **Step 2 预处理**：wrapper 归一化到 DNA 字母表（U→T）
- **Step 3 候选生成**：`design_sgrna_handle_with_crgpt`
- **Step 4 评估**：服务端 NN score（输出字段）/ overlap 约束（服务端/调用方）
- **Step 5 过滤**：无
- **Step 6 排序**：按 `best_nn_score`（越高越好）
- **Step 7 格式化**：输出 FASTA 与 summary JSON 路径

