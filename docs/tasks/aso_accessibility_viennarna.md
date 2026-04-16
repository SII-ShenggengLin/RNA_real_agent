# 任务：`aso_accessibility_viennarna`

## 任务目标

估计目标 RNA 指定区间对 ASO 结合的局部可及性（RNAplfold 摘要指标）。

## 输入 / 输出

- **输入**：目标 RNA 文件路径 + `region_start/region_end`（1-based）等参数
- **输出**：区域平均 unpaired 概率与 joint 概率（若可计算）

## 前置条件

- ViennaRNA 微服务（端口 8003）

## 工具

- `compute_aso_target_accessibility_vienna`

## 标准工具链

见 `docs/workflows/aso_accessibility_viennarna_workflow.md`。

