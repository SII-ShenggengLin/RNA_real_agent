# Full-Length mRNA Design Workflow

## 当前实现

文件: `rna_agent_system/agent_core/workflows/full_length_mrna_design.py`

### 架构

```
Protein sequence
    │
    ▼
MrnaCdsDesignWorkflow.run()  ──→ 已评估的 CDS 候选（带 MFE/CAI/GC/scores）
    │
    ▼
为每条 CDS 附加 3×3 UTR 组合（GEMORNA short/medium/long）
    │
    ▼
增量评估（仅全长 + UTR 指标）
    │
    ▼
Borda Count 排序（cds_component + utr5_mrl + utr3_stability）
    │
    ▼
WorkflowResult
```

### 生成策略

**Strategy C: CDS-only baseline + UTR append**（唯一实现）

- `generate_candidates()` 调用 `MrnaCdsDesignWorkflow.run()` 复用 CDS 生成与评估
- 每条已评估的 CDS 与 3×3 UTR 组合搭配
- 最多 6 条唯一 CDS × 9 种 UTR = 54 条全长候选
- 拼接规则: `full = utr5 + cds + utr3`，CDS 长度必须是 3 的倍数

### 增量评估（evaluate）

CDS 指标直接从 `MrnaCdsDesignWorkflow` 的评估结果复用，不再重新计算：

| 指标 | 来源 |
|------|------|
| `cds_mfe` | 复用 CDS workflow (`metrics_bundle.mfe_kcal_per_mol`) |
| `cds_cai` | 复用 CDS workflow (`metrics_bundle.cai_score`) |
| `cds_gc`  | 复用 CDS workflow (`metrics_bundle.gc_content`) |

全长 workflow 只计算以下增量指标：

1. **全长二级结构** — `predict_rna_secondary_structure` (ViennaRNA → LinearFold fallback)
2. **5'UTR IRES** — `predict_putative_ires_with_iresfinder`（长度 ≥ 30 时）
3. **5'UTR 折叠** — `predict_rna_secondary_structure`（长度 ≥ 10 时）
4. **5'UTR MRL** — `predict_5utr_mrl_with_gemorna`
5. **3'UTR 稳定性** — `predict_3utr_stability_with_gemorna`
6. **全长 RNASTOP** — `predict_mrna_stability_with_rnastop`

**不调用 CodonW**。

### 评分 — Borda Count

三个模块独立排名（降序，第 1 名最好），排名相加：

```
total_rank = cds_rank(cds_component) + utr5_rank(utr5_mrl) + utr3_rank(utr3_stability)
```

按 `total_rank` **升序**排列（越小越好）。

缺失值处理：某模块无分数的候选获得 `penalty_rank = 有分数人数 + 1`；若该模块所有人都无分数，则全部 rank = 1（平手，不影响排序）。

### Critic

仅过滤 5'UTR IRES 潜力。阈值 `0.5`，当通过过滤的候选数 `< 5` 时触发重试。

### 注册

- `rna_agent_system/agent_core/workflows/__init__.py` — 导出
- `rna_agent_system/agent_core/runner.py` — `workflow_registry` 注册
