# RNA-BioBench-Platform 最终实验报告

> 生成时间：2026-06-03  
> 数据来源：`experiments/results/platform_coverage.jsonl`（216 条去重记录）  
> 图表输出：`experiments/results/figures/figure_2_1_panel_e.{pdf,png}`

---

## 一、实验概述

本次实验运行了 RNA 多智能体系统的 **11 个 Workflow**，共计 **216 条 benchmark 任务**，用于生成 **Figure 2.1 Panel e**（Trace Completeness  stacked bar chart）。

| 指标 | 数值 |
|------|------|
| 总任务数 | 216 |
| 成功 | **170** (78.7%) |
| 失败 | **46** (21.3%) |
| Trace Complete | **67** (31.0%) |
| Trace Partial | **11** (5.1%) |
| Trace None | **138** (63.9%) |

---

## 二、各 Workflow 详细结果

| Workflow | 任务数 | 成功 | 成功率 | Trace Complete | Trace Partial | Trace None |
|----------|--------|------|--------|----------------|---------------|------------|
| `sgrna_design` | 30 | 30 | **100.0%** | 30 | 0 | 0 |
| `sirna_design` | 22 | 22 | **100.0%** | 1 | 0 | 21 |
| `mrna_sequence_scoring` | 13 | 13 | **100.0%** | 0 | 0 | 13 |
| `rna_secondary_structure_design` | 25 | 24 | **96.0%** | 2 | 0 | 23 |
| `rna_small_molecule_interaction` | 15 | 14 | **93.3%** | 1 | 0 | 14 |
| `aso_target_screening` | 14 | 13 | **92.9%** | 0 | 0 | 14 |
| `mrna_cds_design` | 19 | 17 | **89.5%** | 2 | 2 | 15 |
| `rna_tertiary_structure_design` | 18 | 14 | **77.8%** | 14 | 0 | 4 |
| `full_length_mrna_design` | 22 | 16 | **72.7%** | 17 | 2 | 3 |
| `ires_prediction` | 12 | 6 | **50.0%** | 0 | 2 | 10 |
| `rna_aptamer_design` | 26 | 1 | **3.8%** | 0 | 5 | 21 |

### 说明
- **Trace Complete**：任务成功且所有预期工具均被调用。
- **Trace Partial**：任务失败但记录了部分工具调用，或成功但遗漏了某些预期工具。
- **Trace None**：任务完全失败且未记录任何工具调用。

> **注意**：`mrna_sequence_scoring`、`sirna_design`、`aso_target_screening` 等 workflow 的 Trace Complete 为 0，是因为它们主要使用 Capability-based 执行路径，不通过 `ToolCallRecord` 记录调用链。`run_single_task.py` 已增加 `_extract_invoked_tools()` 从 `state["tool_results"]` 回溯，但仍有部分 workflow 未在 state 中留存工具名。

---

## 三、失败原因分析

### 3.1 按错误类型统计

| 错误类型 | 次数 | 说明 |
|----------|------|------|
| `task_not_executed` | 26 | 任务被标记为未执行（runner 被中断导致） |
| `empty_candidate_list` | 12 | 候选列表为空 |
| `candidate_generation_failed` | 4 | 候选生成阶段失败 |
| *(空字符串)* | 3 | 未明确分类的错误 |
| `worker_exitcode_-15` | 2 | 子进程被 SIGTERM 终止（疑似 OOM） |
| `all_scoring_tools_failed` | 1 | 所有评分工具失败 |
| `worker_exitcode_-9` | 1 | 子进程被 SIGKILL 终止（疑似 OOM） |

### 3.2 重点 Workflow 失败分析

#### 1. `rna_aptamer_design`（26 任务，仅 1 成功）

这是本次实验中最薄弱的 workflow，失败分为两类：

**A. 已尝试但失败的 5 个任务（001–005）**
- **根本原因**：`agent_core/workflows/rna_aptamer_design.py` 第 946 行调用 ODesign 时使用了错误的参数名 `input_json_path`，而工具 `run_odesign_inference` 的 Pydantic schema 要求的是 `input_json_filepath`。
- **后果**：ODesign 推理在 Pydantic validation 阶段直接失败，导致 `candidate_generation_failed`。
- **耗时**：322–766 秒（ODesign 服务启动了子进程，但在参数校验时被拒）。

**B. 从未执行的 21 个任务（006–026）**
- **原因**：先前的 benchmark runner 在完成任务 005 后被中断（kill），后续任务被标记为 `task_not_executed`（elapsed=0.0s）。

**C. 修复后成功重跑的 1 个任务（001_basic）**
- 修复参数名 bug + CIF B-factor 解析 bug 后，任务 001 成功完成全部 pipeline：
  - ProteinX 结构预测（~30 min）
  - Hotspot 识别
  - ODesign JSON 构建
  - ODesign 推理（~6 min）
  - CIF 序列提取（修复后成功）
  - RhoFold 评分
  - ProteinX 复合物预测
  - 界面分析
- **总耗时**：2089.5 秒（~35 分钟）
- **成功调用工具**：9/10（仅 `score_rna_protein_complex_with_egarps` 因最佳努力策略跳过）

> **结论**：aptamer workflow 的核心 bug 已修复，理论上剩余 25 个任务均可成功，但每个任务需 30–60 分钟（ProteinX + ODesign + 评分），总耗时约 12–25 小时。

#### 2. `full_length_mrna_design`（22 任务，16 成功）

- **主要失败原因**：
  - `empty_candidate_list`（3 次）：LinearDesign 未返回有效候选
  - 空错误字符串（3 次）：未明确分类的内部异常
  - `worker_exitcode_-15`（2 次）：子进程被 SIGTERM 终止，疑似内存不足（OOM）导致系统 kill
- **平均耗时**：327.7 秒（最慢 836.4 秒）

#### 3. `ires_prediction`（12 任务，6 成功）

- **失败原因**：`empty_candidate_list`（6 次）
- 该 workflow 在候选生成阶段对输入序列的 IRES 特征要求较严格，部分 edge case 无法产生有效候选。

#### 4. `rna_tertiary_structure_design`（18 任务，14 成功）

- **失败原因**：`task_not_executed`（4 次）
- 这 4 个任务与 aptamer 任务一样，因 runner 中断而未被实际执行。

#### 5. `rna_secondary_structure_design`（25 任务，24 成功）

- **失败原因**：`task_not_executed`（1 次）
- 同样是 runner 中断导致。

---

## 四、已修复的关键 Bug

### 4.1 `rna_aptamer_design` 参数名错误
- **文件**：`agent_core/workflows/rna_aptamer_design.py`
- **问题**：调用 `run_odesign_inference` 时传入 `input_json_path`，但工具 schema 要求 `input_json_filepath`。
- **修复**：将 `"input_json_path"` 改为 `"input_json_filepath"`（第 946 行）。

### 4.2 `extract_rna_sequence_from_cif` 无法解析 ODesign CIF
- **文件**：`agent_core/tools.py`
- **问题**：ODesign 输出的 CIF 文件缺少 `_atom_site.B_iso_or_equiv` 列，biopython 的 `MMCIFParser` 直接崩溃（`KeyError` → `PDBConstructionException`）。
- **修复**：新增 `_ensure_cif_has_b_iso_or_equiv()` 辅助函数，在解析前自动注入 dummy B-factor 列（值为 `0.0`）。

### 4.3 `tools.py` 缺少 `os` 导入
- **文件**：`agent_core/tools.py`
- **问题**：上述 CIF 修复使用了 `os.fdopen`，但文件顶部未导入 `os`。
- **修复**：在 imports 段增加 `import os`。

### 4.4 Trace Completeness 提取逻辑（历史修复）
- **文件**：`experiments/run_single_task.py`
- **问题**：Capability-based workflow 的结果只写入 `state["tool_results"]`，不生成 `ToolCallRecord`，导致 `trace_length=0`。
- **修复**：增加 `_extract_invoked_tools()` 从 `result.trace`、`result._state_writeback["tool_results"]` 和 candidate metadata 中提取工具名。

---

## 五、Figure 2.1 Panel e

图表已生成：
- **PDF**：`experiments/results/figures/figure_2_1_panel_e.pdf`
- **PNG**：`experiments/results/figures/figure_2_1_panel_e.png`

图表展示了每个 workflow 的 Trace Completeness 分布（Complete / Partial / None）。

**关键观察**：
- `sgrna_design`、`rna_tertiary_structure_design`、`full_length_mrna_design` 的 Complete 比例较高，说明这些 workflow 的工具调用链记录较完整。
- `rna_aptamer_design` 的 None 比例极高（21/26），其中 21 个是 `task_not_executed`，5 个是 `candidate_generation_failed`（修复后可转为 Complete/Partial）。
- 大量 workflow 的 Complete 比例为 0，主要因为 Capability-based 执行不经过 `ToolCallRecord`，需要进一步改进 trace 捕获机制。

---

## 六、未完成的工作与建议

### 6.1 aptamer 任务重跑
- **状态**：25/26 尚未成功（21 个未执行，4 个因旧 bug 失败）。
- **预计耗时**：每任务 30–60 分钟，总计约 12–25 小时。
- **建议**：可在后台启动 `run_workflow_sequential.py rna_aptamer_design` 过夜运行。

### 6.2 ProteinX 服务阻塞问题
- **现状**：ProteinX 服务使用 `async def` + 同步 `subprocess.run`，导致预测期间整个服务无响应（health check 也会超时）。
- **影响**：aptamer 任务在等待 ProteinX 时，runner 误判服务 unhealthy。
- **建议**：将 `subprocess.run` 改为 `asyncio.create_subprocess_exec` 或放入线程池执行。

### 6.3 ODesign 外部仓库 Bug
- **文件**：`external_repos/ODesign/src/utils/inference/inference_utils.py:246`
- **问题**：`struc.to_sequence()` 返回空列表时，`chain_sequence[0][0]` 触发 `IndexError`。
- **影响**：部分蛋白质结构（如含非标准残基链）会导致 ODesign 崩溃。
- **建议**：在 ODesign 外部仓库提交 PR 或本地打补丁。

### 6.4 数据文件损坏
- **现象**：`platform_coverage.jsonl` 在实验过程中曾丢失 26 条 aptamer 记录和 5 条结构类记录，被 `task_not_executed` 占位。
- **根因**：runner 被 kill 后，未完成的批次可能写入了占位记录，或并发写导致文件损坏。
- **建议**：未来运行 benchmark 时避免并发写同一个 jsonl 文件，或使用 SQLite/数据库替代。

---

## 七、附录：原始数据文件

| 文件 | 说明 |
|------|------|
| `experiments/results/platform_coverage.jsonl` | 最终 216 条去重记录 |
| `experiments/results/platform_coverage.jsonl.backup` | 05:01 备份（221 条含重复） |
| `experiments/results/figures/figure_2_1_panel_e.pdf` | Panel e PDF 输出 |
| `experiments/results/figures/figure_2_1_panel_e.png` | Panel e PNG 输出 |
