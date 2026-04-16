# 工作流：`sirna_design_evitar`

## 基础链（最稳）

### Step 1：输入校验

- **模块**：`agent_core/tools.py` + Evitar 服务端 Pydantic 校验
- **校验点**：`filepath` 指向可读 FASTA；`mode/predict` 合法；`existing` 模式需 `strains_path`

### Step 2：预处理

- **无**（由 Evitar 服务端处理）

### Step 3：候选生成

- **工具**：`design_sirna_with_evitar`

### Step 4：评估

- **无**（本仓库未接入生产级 efficacy/off-target 评估工具链）

### Step 5：过滤

- **无**（可基于 Evitar 输出列做后处理）

### Step 6：排序

- **无**（排序由 Evitar 输出或调用方规则决定）

### Step 7：结果格式化

- **模块**：`agent_core/nodes.py` 将 `output_filepath/top_results/result_count` 写回 state

