# Exp 28 关机保存点（2026-09-03 03:2x，用户指示关机）

## 当前进度
- **生产系统修复已落地并全绿**：`gennav_mrna_lambda.py` v2.4（预算 35 = 预算匹配规则臂
  35 次原始生成调用；λ 网格 35 值；带参数全部对齐注册矩阵——CAI 下限 0.80=CAI_MIN
  （含 stability 带）、茎 ≤30bp=C7、GC 窗 [0.30,0.80]=C1 滑窗界、同聚物 <14=C2；
  同义多样化扩展器 = legacy E6 组件 3 从 git `1b45138~1` 恢复（密度 0.15、每带 30 上限、
  ≤6 遍）；CDS 级 D1 门槛 0.03 = legacy P3 标定值；并行探测（>800aa 自适应 2 线程）。
  护栏测试 25 + mRNA 片 110 全绿。
- **exp28 驱动就绪**：`experiments/exp28_gennav_mrna_endpoint_v2.py`（import exp27 判据；
  预算匹配断言；约束优先组合；LPT 分靶；RetryInstrument 90s 单次重试）。
- **pilot 完成**：Insulin C=2/3（A=0/3）、OTC 3/3 双方 → b:c=2:0；`--verify` 逐字节一致。
- **全量 18/20 完成、零失败**（记录在 `full/runs_worker*.jsonl`，18 条）。
  当前累计 **b:c = 14:6**（导航净领先；c 的 3 格来自 GFP 历史难靶）。
- **中断丢失**：HER2（w1，~5.3h 导航）与 Spike（w0，~5.4h 导航）两个 cell 未写盘即被
  停止——重启后这两个靶**从头重跑**（池折叠/GEMORNA 缓存已在 worker 缓存目录，池构建
  会快；导航 35 次串行调用 ~4-5.5h/靶是主要耗时）。两个靶可并行（各占一 worker）。

## 恢复步骤（重启后）
```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system
# 1) 起服务（GPU 0/1/2）
PYTHONPATH="$(pwd):$PYTHONPATH" bash experiments/exp1_bring_up_services.sh
# 2) 续跑全量（resume 会自动识别 18 个已完成靶，只跑 HER2 + Spike；LPT 2 worker 即可）
PYTHONPATH="$(pwd):$PYTHONPATH" nohup python3 experiments/exp28_gennav_mrna_endpoint_v2.py \
    full --resume --workers 2 > experiments/results/exp28_run2.log 2>&1 &
# 3) 完成后：--verify、重画图 5b/5c（脚本已就绪：experiments/plots/fig5b_gennav_mcnemar.py
#    与 fig5c_delivery_mosaic.py 指向 exp28 需改 RESULTS 路径——见下）、同步论文/文档。
```

## 图脚本注意
`experiments/plots/fig5b_gennav_mcnemar.py` / `fig5c_delivery_mosaic.py` 目前仍读
`exp27_gennav_mrna_endpoint/full/`（Exp 27 的反转结果）。Exp 28 定稿时需把两脚本的
RESULTS 路径改到 `exp28_gennav_mrna_endpoint_v2/full/` 再渲染（panel 语义不变，
数字自动更新）。

## 待办（全量完成后）
1. `--verify full`；2. 改图脚本路径→渲染 fig5b/5c→raster QA；3. 论文改基到 Exp 28
   （描述最终修复系统：预算匹配 + 注册锚带参数 + 多样化扩展器；Exp 27 降为内部登记）；
   4. FACT_SHEET/FIGURE_PLAN/MANUSCRIPT/MODEL_API_USAGE/CHANGELOG/AGENTS 同步；
   5. `git commit`（用户确认后）。

## 关键文件
- 驱动：`experiments/exp28_gennav_mrna_endpoint_v2.py`（docstring = 最终系统描述）
- 生产修复：`agent_core/generation/gennav_mrna_lambda.py`、
  `agent_core/workflows/mrna_cds_design.py`（v2.4 + 并行探测 + Phase 2.5 扩展）
- 测试：`tests/test_gennav_mrna_core.py`（25 绿）、`tests/test_mrna_cds_gennav.py`
- 记录：`experiments/results/exp28_gennav_mrna_endpoint_v2/{pilot,full,caches}/`
- Exp 27（内部登记）：`experiments/results/exp27_gennav_mrna_endpoint/`
