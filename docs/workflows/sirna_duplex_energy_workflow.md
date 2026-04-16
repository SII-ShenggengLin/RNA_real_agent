# 工作流：`sirna_duplex_energy`

## 基础链（最稳）

### Step 1：输入校验

- **工具/模块**：`agent_core/tools.py` duplex 解析逻辑（sense/antisense FASTA 或两行序列）
- **校验点**：必须能解析出两条链；字符集应为 A/U/G/C（允许 T 会在部分路径归一化）

### Step 2：预处理

- **无**

### Step 3：候选生成

- **无**（本任务假设候选链已给定）

### Step 4：结构/能量评估

- **工具**：`compute_sirna_duplex_binding_vienna`
- **关键输入参数**：`filepath`
- **关键输出字段**：`mfe_kcal_per_mol`、`structure`

### Step 5：过滤

- **无**（过滤阈值由上层任务定义）

### Step 6：排序

- **规则示例**：按 `mfe_kcal_per_mol` 升序（更负更优）

### Step 7：结果格式化

- **模块**：上层调用方（或 agent 最终报告）将关键字段写入最终输出

