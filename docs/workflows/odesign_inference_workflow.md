# 工作流：`odesign_inference`

## 基础链（最稳）

- **Step 1 输入校验**：`input_json_filepath` 可读且为合法 JSON
- **Step 2 预处理**：无
- **Step 3 候选生成**：`run_odesign_inference`（此步产生预测文件集合）
- **Step 4 评估**：无（可按任务自定义后处理）
- **Step 5 过滤**：无
- **Step 6 排序**：无（由上游 JSON/模型决定）
- **Step 7 格式化**：输出 `prediction_filepaths` 与日志路径

