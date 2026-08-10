# 交接提示词（新会话专用，2026-07-30 终版）

> **⚠️ 2026-08-03 起主线已转向试点验证：新会话请先读 [`HANDOFF_2026-08-03_PIVOT.md`](HANDOFF_2026-08-03_PIVOT.md)，本文件作为历史背景与血泪教训（§5 全部仍有效）参考。**

> 用法：新开会话后，先让它完整阅读本文件 + `rna_agent_system/docs/MANUSCRIPT.md` + `rna_agent_system/experiments/results/RESUME_CHECKPOINT.md`，再继续工作。

## 1. 项目与你现在的任务

这是 **RNADesignAgent** 项目（RNA 设计多智能体系统，目标投稿 *Nature Methods*）。代码库在 `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程目录是 `rna_agent_system/`（所有命令都在此目录下执行，统一带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。项目规范见根目录 `AGENTS.md`。

**当前状态：图 2–7 全部实验、统计、绘图均已完成，无在跑任务，无需监控 cron。** 后续工作是论文写作与可选数据尾巴（§4，启动前先问用户）。

## 2. 已完成（勿重跑）

| 内容 | 文件 | 备注 |
|------|------|------|
| 图 2 全套 | `fig2_summary.json`、`plots/fig2.png` | 209/210（1 个 QualityAgent 正确中止） |
| 图 3 Type-I + 3d 引导 + 3e trace + 锚点 | `fig3_type1_shard_{a,b}.jsonl`（240/240）、`fig3_steering.jsonl`（18/18）、`fig3_anchors.json`、`plots/fig3.png` | 主效应靶点依赖；引导精确 |
| 图 4 Type-II + 4c/d 已知适配体 | `fig4_type2_shard_{a,b}.jsonl`（228/240 + 边界）、`fig4_known_aptamers.jsonl`（7/7）、`plots/fig4.png` | egarps/超体积显著 |
| 图 5 机制消融 | `fig5_ablations.jsonl`（141 + 12 边界）、`fig5_summary.json`、`plots/fig5.png` | b/c 全 NS、e1/e2 阴性对照成立、d 有界性实证 |
| 图 6 智能体层 | `fig6_quality_ablation.jsonl`（38/38）、`fig6_backends.jsonl`（deepseek 19/19）、`plots/fig6.png` | LLM 纯顾问；claude 臂 Kimi 网关 404 错配 |
| 图 7 案例 | `fig7_cases/{A,B,C}/case_summary.json`、`plots/fig7.png` | A 85 min / B 47 min / C 73 s；无损 resume 修复 |
| 统计/分类学 | `fig{3,4,5}_summary.json`、`failure_taxonomy.json` | bh_q/median_delta/ASF 核实健康 |
| 坑固化 | 代码注释 + `docs/CHANGELOG.md` 2026-07-30 条目 | pytest 507 passed, 1 skipped 基线 |

## 3. 关键统计结论（论文叙事骨架，勿推翻重算）

- **图 3 Type-I**：BMC 主效应**靶点依赖**——硬靶点显著改善（HER2 0.165→0.051、Beta_gal 0.106→0.026、Influenza 0.139→0.030），易靶点≈串行。H3.1 重构为"冲突条件依赖"。
- **图 3d**：参考点引导精确（translation-first 推高 utr5_mrl 牺牲 utr3；stability-first 反之；balanced 双高）。H3.3 成立。
- **图 4 Type-II**：**主效应显著**——egarps 分量 BMC×1 p=2.1e-4（δ=+0.46）；超体积 12 项比较全显著（hv3d p≈2.6e-4，δ≈+0.27）；固定 ASF 边缘显著（p=0.073，δ=−0.24）。
- **图 5**：反馈模式（b）与参考点形式（c）均不显著——BMC 增益载体是有界多轮协调本身；e1/e2 阴性对照成立（无冲突时 BMC≈串行）；λ=18 极端起点被钳回 [0,20]。
- **图 6**：QualityAgent 两臂成功率一致（19/19）+ DeepSeek 全后端矩阵单臂全绿——"LLM 是顾问不是承重墙"。
- **图 7**：Case A 设计候选 CAI 0.946 vs BNT162b2 0.952（IRES 0 命中，AUG 掩埋与获批疫苗同型=软指标）；Case B 首选 EGARPS 0.70 vs pegaptanib 母体 ~5e-7（接触 20、氢键 5）；Case C top5 全部零脱靶、GC 38% 合规。
- **叙事框架**：Type-I（接头耦合）= 冲突条件效应；Type-II（功能耦合）= 主效应。
- **边界**（写限制章节）：Ferritin/1FHA（ODesign 零产出）、Zika/Factor VIII（LinearDesign ≥7 kb OOM）、Nucleocapsid/6M3M e2（显式热点超范围）、RNAsmol/GerNA-Bind 短适配体区分度弱。

## 4. 可选尾巴（启动任何一项前先问用户）

- 图 6b 补 5 家 API key 扩展后端矩阵（`OPENAI/ANTHROPIC/ALIBABA/GOOGLE` 写入 `rna_agent_system/.env` 后 `run_llm_backend_comparison.py --resume` 自动扩展；claude 臂需真 Anthropic 或 OpenRouter——环境现有 `ANTHROPIC_BASE_URL` 是 Kimi 网关，无 claude 模型）。
- 图 5 panel f（partial_rerun 省时测量）：`run_bmc_mechanism_ablations.py --panel f --do-it --f-reps 10`（机器空闲时）。
- pegaptanib `binding_site_residues` 锚点缺口（`data/benchmarks/external_anchors/aptamers/pegaptanib.json` TODO；补齐后图 4d/7B 位点对比自动生效）。

## 5. 血泪教训（不要再踩）

1. **EGARPS 输入三坑**（已在代码注释固化，勿回退）：(a) 只接受真 `.pdb`——Protenix mmCIF 的 OP3 原子被拒；(b) `ins.py` 对非 `.pdb` 文件名会把 pickle 缓存覆写回输入文件本体（毁文件）；(c) 链分型 `re.search('protein', basename)`——文件名含 "protein"（如 "proteinx"）会把 RNA 链劫进蛋白特征路径。转换用 `run_known_aptamer_validation.py::_proteinx_cif_to_pdb`（gemmi + 文件名消毒）。
2. **DeepSeek 欠费（402）**：QualityAgent 诊断失败→回退 abort→整轮判负。余额恢复后 `--resume` 即可。
3. **端点错配不是后端数据**：环境 `ANTHROPIC_BASE_URL` 是 Kimi 网关（无 claude 模型）——fig6b claude 臂的 8 条 404 记录属错配，`--resume` 会在真 key 到位后覆盖。
4. **共享机杀进程**：驱动死亡先看日志有无 "Done:" 行区分正常退出；`--resume` 幂等，在跑 job 未写记录会自动重做。查 402 再重启。**重启前确认进程表为空**（2026-07-30 双驱动并行事故）。**长任务超时上限不是硬杀**：SIGALRM 超时会被调用栈宽 except 吞掉（fig6b PA_020 实证 146 分钟仍在推进，见 `run_quality_ablation.py::_turn_time_limit` NOTE）——监控时看到任务超过 timeout 但有进展（连接活跃/CPU 增长），勿误杀。
5. **边界格永不重试**：Ferritin（b/c）、Nucleocapsid-e2、Zika/FVIII——驱动内已跳过或记录在案。
6. **JSONL 同 job 取最新一条**；fig3 记录用 `rep`、fig4 用 `seed_idx` 做去重键。
7. **已修复根因勿回退**（NOTE 注释 + CHANGELOG）：`service_manager.py` 的 `health_timeout`=30s 与 `_port_listening` 忙判宕规则；`cli/form_chat.py` 的 `_bmc_trace` 回退落盘；图 7 驱动的无损 resume 修复（`latest_node_record` + 锚点 outputs 落盘 nodes.jsonl）。
8. 微服务全部自启动（含预检），别手写启动脚本；**直连能力链（fig7 锚点、fig4kav 已知适配体链）不走预检**，服务宕时先用 `service_manager.ensure_services_ready` 拉起。
9. **git 操作（commit/push 等）必须先问用户**。
10. 改代码后跑 `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x`（当前基线 **507 passed, 1 skipped**）。
11. 子代理配额此前已耗尽（403），需要写大脚本时主 agent 自己写。
12. 统计规范（手册 §13）：配对 Wilcoxon + Cliff's δ + BH-FDR 0.05 + AUROC bootstrap CI，工具函数在 `experiments/analysis/stats_utils.py`；跨条件比较用固定参考点 ASF（utopian ASF=0 陷阱见 `multi_objective.py` 注释）。
13. **模型 API 记录（强制）**：任何产生论文数据的实验，驱动必须在记录中写明每个 LLM 调用的 provider/model/endpoint（并尽量采集 token usage）；完成后当天更新 `experiments/results/MODEL_API_USAGE.md`（规范见该文件 §6）。当前状态：全部结果仅用 DeepSeek `deepseek-v4-pro`（QualityAgent），其余模型均本地部署。

## 6. 新会话开工顺序

1. 读完三份文档（本文件 + MANUSCRIPT + RESUME_CHECKPOINT）。
2. 确认无在跑任务（全部完成）；若要启动 §4 的可选项，先问用户。
3. 论文写作以 `plots/fig{2..7}.png` + 各 summary JSON + §3 叙事骨架为据。
