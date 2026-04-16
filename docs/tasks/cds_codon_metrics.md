# 任务：`cds_codon_metrics`

## 任务目标

对 CDS 计算密码子使用指标（CAI/Fop/CBI/ENC 等）并输出可审计的 JSON 明细。

## 输入 / 输出

- **输入**：CDS 序列文件路径（应为 in-frame CDS）
- **输出**：`cai_score/enc/fop/cbi` + `metrics_json_filepath`

## 前置条件

- codonw-slim 微服务（端口 8018）

## 工具

- `analyze_cds_codon_metrics_with_codonw_slim`

## 标准工具链

见 `docs/workflows/cds_codon_metrics_workflow.md`。

