# 断点续跑手册（2026-07-30 更新）

> 所有实验驱动的记录**逐行增量写入** JSONL，并支持 `--resume`（跳过 success=true 的记录，重跑失败/缺失的）。
> 本文件是唯一的续跑入口。微服务无需手工启动——CLI 预检会自动拉起。

## 0. 2026-07-30 终态（全部实验完成）

**图 2–7 全部实验、统计、绘图均已完成，无在跑任务。**

- 图 7：3/3 案例 ✅（A 85 min、B 47 min、C 73 s）。驱动经"无损 resume"修复（`latest_node_record` 恢复 prior 字段 + 锚点 outputs 落盘 nodes.jsonl；直连锚点链不自启服务的注意事项已在码内 NOTE）。三个 `case_summary.json` 完整。
- 图 5：141 成功 + 12 边界（Ferritin b/c 6 + Nucleocapsid e2 6，驱动内跳过勿重试）。`fig5_summary.json`。
- 图 6：6a ✅ 38/38；6b deepseek 19/19（claude 2/10 为 Kimi 网关 404 错配；用户决定暂不补 5 家 key，重启需先问用户）。
- 统计修缮（bh_q/median_delta/ASF 核实健康）、失败分类学（`failure_taxonomy.json`）、绘图（`plots/fig{2..7}.png` 全部目检合格）均完成。
- **模型 API 使用记录**：`experiments/results/MODEL_API_USAGE.md`（论文 Methods 必备：全部结果仅用 DeepSeek `deepseek-v4-pro`@QualityAgent；后续实验必须按该文件 §6 规范记录并更新）。
- 坑固化：代码注释 + `docs/CHANGELOG.md` 2026-07-30 条目；pytest 基线 507 passed, 1 skipped。
- 监控 cron 已全部删除。

### 可选尾巴（重启任何一项前先问用户）

- 图 6b 补 5 家 API key 扩展后端矩阵（key 写入 `.env` 后 `run_llm_backend_comparison.py --resume`）。
- 图 5 panel f：`run_bmc_mechanism_ablations.py --panel f --do-it --f-reps 10`（机器空闲时）。
- pegaptanib `binding_site_residues` 锚点缺口（`data/benchmarks/external_anchors/aptamers/pegaptanib.json` TODO；补齐后图 4d/7B 位点对比自动生效）。

---

# 断点续跑手册（2026-07-19 第二次关机前保存）

> 所有实验驱动的记录**逐行增量写入** JSONL，并支持 `--resume`（跳过 success=true 的记录，重跑失败/缺失的）。
> 本文件是唯一的续跑入口。微服务无需手工启动——CLI 预检会自动拉起。

# 断点续跑手册（2026-07-19 第二次关机前保存）

> 所有实验驱动的记录**逐行增量写入** JSONL，并支持 `--resume`（跳过 success=true 的记录，重跑失败/缺失的）。
> 本文件是唯一的续跑入口。微服务无需手工启动——CLI 预检会自动拉起。

## 0. 本次关机前的重要修复（已生效）

- **`health_timeout` 2 s → 30 s**（`agent_core/services/service_manager.py:490`，测试已同步）：EGARPS 等单工作进程服务在长请求期间 /health 应答 > 2 s，被误判为宕机 → 误触发重复启动 → 端口冲突（"address already in use"）→ 连锁任务失败。这是图 4 大量 cli_failure 的总根因，修复后预检不再误重启。`tests/test_service_manager.py` 31/31 通过。
- **stdin 补丁**（上一关机点已加）：`run_task_dict` 以 `input="y\n"` 启动 CLI 子进程，避免"是否继续? (y/n)"提示在 EOF 下崩溃。
- **3v03 (BSA) CB 修复**（已验证端到端成功）。

## 1. 已完成（无需重跑）

| 内容 | 文件 | 状态 |
|------|------|------|
| 图 2 全部 210 任务 | `fig2_cpu_a.jsonl` (106), `fig2_cpu_b.jsonl` (66), `fig2_gpu.jsonl` (38) | ✅ 209/210（1 个为 QualityAgent 正确中止） |
| 图 2 CDS 空跑（18/20 靶点；Zika/FVIII 为 LinearDesign OOM 边界，记录在案） | `fig2_cds_nulls.jsonl` | ✅ |
| 图 2 文献面板（IRES 53 + 小分子 17） | `fig2_literature_panels.jsonl` | ✅ |
| 图 2 汇总统计 | `fig2_summary.json`（`experiments/analysis/summarize_fig2.py` 可随时重生成） | ✅ |
| 锚点数据（20 WT CDS、疫苗序列、pegaptanib、IRES、小分子） | `data/benchmarks/external_anchors/` + `SOURCES.md` | ✅ |
| 图 3c 锚点打分 | `fig3_anchors.json` | ✅ |

## 2. 进行中任务的断点状态（去重后唯一成功数/120）

> **2026-07-25 01:29 状态：4 个消融分片全部完成，无需再续跑。**
> - 图 3 Type-I A/B：**240/240** ✅（fig3_summary.json 已生成）
> - 图 4 Type-II A/B：**228/240** ✅ + Ferritin 12 格确诊边界（ODesign 零产出，见 §4；fig4_summary.json 已生成，Myoglobin 误中止格已补回）
> - 进行中：图 3d steering（`fig3_steering.jsonl`，监控 cron `bfd2e390` 每小时 :41）；跑完自动接图 4c/d 与图 5。
> - 以下 4 条命令仅作历史参考（如需复核数据可用 --resume 重跑失败项，幂等）。

> **2026-07-23 06:38 第四次关机前保存（用户要求主动停止）**。4 个分片已 TERM 停止；重启后按下表四条命令（`setsid nohup ... < /dev/null &` 脱离会话方式）重启即可，`--resume` 幂等。停止时在跑的 4 个任务（Spike r1 rep2、Transferrin r1 rep0、Lysozyme r2 s[42,123]、Thrombin r2 s[2024,31415]）未写记录，续跑自动重做。监控 cron（id `c99b6eb7`，每小时 :23，含 402 判据）随 CLI 会话持久化，`kimi resume` 本会话后自动恢复；用户说"继续"即按本节重启分片（**fig3A/fig3B 均用 --timeout 9000**）。
>
> **2026-07-21 16:10 第二次停跑（DeepSeek 欠费）**：约 13:26 起 DeepSeek API 402 Insufficient Balance，QualityAgent 诊断回退 abort → SpecialistAgent 把整轮判负（`specialist_agent.py:65`），四片此后零成功（fig3A/fig4A/fig4B 为 cli_failure=402，fig3B 为 HER2 超时叠加）。已主动 TERM 全部 4 片止血，进度无回退。用户充值后 16:33 重启恢复。**恢复条件：用户充值 DeepSeek（或批准切换 QualityAgent 默认 provider / 修改 infra-失败不判负的行为）后**，按下表命令重启；fig3B 注意改用 `--timeout 9000`（HER2 在负载下 r0 就要 ~87 分钟，r1+ 超 5400s 天花板）。

| 分片 | 断点文件 | 进度 | 续跑命令（在 `rna_agent_system/` 下） |
|------|----------|------|--------------------------------------|
| 图 3 Type-I 分片 A | `fig3_type1_shard_a.jsonl` | 101/120（Spike 大蛋白，**用 --timeout 9000**） | `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type1_ablation.py --targets Zika_E_protein,SARS-CoV-2_Spike_WT,Beta_galactosidase,HIV-1_Env_gp120,Luciferase,HPV16_L1,Ovalbumin,Growth_hormone,IL-2,IFN_alpha_2a --resume --timeout 9000 --output experiments/results/fig3_type1_shard_a.jsonl` |
| 图 3 Type-I 分片 B | `fig3_type1_shard_b.jsonl` | 111/120（**用 --timeout 9000**） | `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type1_ablation.py --targets Factor_VIII,HER2,Transferrin,Albumin,RSV_F_protein,Influenza_HA_H1N1,A1AT,GFP,EPO,Insulin --resume --timeout 9000 --output experiments/results/fig3_type1_shard_b.jsonl` |
| 图 4 Type-II 分片 A | `fig4_type2_shard_a.jsonl` | 75/120（15 个待重试，忙判宕修复后稳定清扫中） | `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type2_ablation.py --targets BSA,Carbonic_anhydrase_II,Chymotrypsinogen,Concanavalin_A,Cytochrome_c,Ferritin,GFP,Lysozyme,MBP,Myoglobin --resume --timeout 5400 --output experiments/results/fig4_type2_shard_a.jsonl` |
| 图 4 Type-II 分片 B | `fig4_type2_shard_b.jsonl` | 91/120（1 个待重试） | `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type2_ablation.py --targets Papain,Pepsin,RNase_A,SARS-CoV-2_Nucleocapsid,Streptavidin,Subtilisin,TNF_alpha,Thrombin,Trypsin,VEGF --resume --timeout 5400 --output experiments/results/fig4_type2_shard_b.jsonl` |

**重要**：
- 全部分片统一用 `--timeout 5400`（Beta_gal/Pepsin 在竞争下超 3600s）。
- 每个分片首遍完成后，**再用同一命令跑一次**（--resume 只重跑失败项），直到失败清零或确认为边界案例。
- 关机时在跑的任务未写记录，续跑自动重做。
- 2026-07-20 起 CLI 已修复 `_bmc_trace` 落盘（见 §3b），重启后新任务自动带真实 trace；分片驱动的启动日志追加到 `experiments/results/fig{3,4}_shard_{a,b}.log`。

## 3. 待启动（脚本已就绪，等分片结束后开跑）

- 图 3d 参考点引导：`experiments/run_reference_point_steering.py` ✅（Spike/EPO × 3 配置 × 3 重复；池自动从分片 JSONL 的 Serial 记录构造，Spike 串行记录未齐前会明确报错）。
- 图 4c/d 已知适配体验证：`experiments/run_known_aptamer_validation.py` ✅（7 个 block；已知数据缺口：pegaptanib binding_site_residues=null、6M3M 已知热点编号超出结构范围——记录里会标注）。
- 图 5 机制消融：`experiments/run_bmc_mechanism_ablations.py` ✅（panels b–f 共 159 jobs；`APTAMER_FEEDBACK_MODE` 开关已上线，默认行为不变；panel f 需机器空闲时 --do-it 手动跑）。
- 图 6 智能体层：`experiments/run_quality_ablation.py` / `run_llm_backend_comparison.py` ✅（provider 切换=构造注入，零代码改动；pa_benchmarks.json 目前只有 19 个任务 006–024，手册写的 26 个，脚本数据驱动自动适配）。
- 图 7 案例管线：`experiments/run_case_study_pipelines.py` ✅（驱动内链式，不用 --pipeline-file；Case A 等 Spike 串行池，7 个单测过）。
- 绘图与成稿：`plots/plot_fig2.py` ✅（已目检成图）；plot_fig{3..7}.py 待数据齐后写；图 1e `export_bmc_rule_map.py` ✅（--check 防漂移）。
- 图 3e trace panel 专用：分片结束后单跑一次 Spike `bmc_max_rounds=3`（修复后的 CLI 会落真实 trace）。

## 3b. 2026-07-20 修复：`_bmc_trace` 落盘

`cli/form_chat.py` 的 `_save_workflow_results` 此前读 `state["_bmc_trace"]`（无人写入）→ 所有 CLI artifact 的 trace 恒为 `[]`。已加回退到 `result._state_writeback["_bmc_trace"]`（锁内 audit 字段，additive；pytest 505 全绿）。**影响**：此前写入的 fig3/fig4 分片记录 `bmc_trace=None`——每轮执行情况可从会话候选 metadata（`bmc_regenerated`/`bmc_round`）事后恢复；之后启动的 CLI 子进程自动带真实 trace。分析脚本对 None trace 已优雅降级。

## 4. 已知边界/发现（写入论文相应章节）

- LinearDesign 对 ~7 kb+ CDS OOM（SIGKILL）：Zika (10 kb)、Factor VIII (7 kb)——操作包络限制。
- 两款获批疫苗（BNT162b2/mRNA-1273）接头窗口 AUG/Kozak 弱配对——掩埋检查是软指标。
- RNAsmol/GerNA-Bind 在短适配体上区分度弱（AUROC ~0.5）——工具训练分布边界。
- sirna GC-rich 任务被 QualityAgent 正确中止——治理能力正面案例。
- **单工作者服务"忙而不答 /health"**（EGARPS 为另一分片连续打分时分钟级不应答）：2026-07-22 起 `ensure_services_ready` 用 `_port_listening` 区分"忙"（端口在听→等待后照常放行，绝不重启）与"宕"（端口空闲→走原启动路径）；30s `health_timeout` 约定不变。此类失败（cli_failure + 日志含 "address already in use"）一律 `--resume` 重试。
- **Ferritin (1FHA) 为 ODesign 靶点侧边界**（2026-07-24 确诊）：12 个矩阵格 + 3 轮重试全部 `no_sequences_extracted_from_odesign_output` → `candidate_generation_failed`——ODesign 在该靶点上零产出，确定性，不再重试。fig4A 有效完成度 107/120 + 12 Ferritin 边界格（与 Zika/FVIII 的 LinearDesign OOM 同类，写入限制章节）。
- **Myoglobin r3 s2 的 QualityAgent 误中止**（"no user request"幻觉理由，工作流本身成功产候选）：重试观察中；若再三误中止记为 LLM 治理边界案例（佐证"LLM 是顾问而非承重墙"的讨论点）。
- **DeepSeek 欠费（402）事故**（2026-07-21）：QualityAgent 诊断失败回退 abort → SpecialistAgent 整轮判负。余额恢复后全部重跑成功；监控 cron 含 402 判据。
- **fig3B 的 HER2 需要 `--timeout 9000`**（负载下 r0 ~87 分钟，r1+ 超 5400s 天花板）。

## 5. 分析注意

- 所有分析用 `experiments/analysis/` 下的 `stats_utils.py`（Wilcoxon/Cliff's δ/BH-FDR/bootstrap AUROC）。
- JSONL 同一 task/target 可能有多条记录（失败+重试），**取最新一条**。
- 图 3/图 4 的 utopian 参考点下 best_candidate 的 `asf_distance` 可能为 0（参考点即最优候选本身）；BMC vs 串行比较用统一固定参考点 ASF + 各目标分量 + Pareto 超体积。


> 所有实验驱动的记录**逐行增量写入** JSONL，并支持 `--resume`（跳过 success=true 的记录，重跑失败/缺失的）。
> 本文件是唯一的续跑入口。微服务无需手工启动——CLI 预检会自动拉起。

## 1. 已完成（无需重跑）

| 内容 | 文件 | 状态 |
|------|------|------|
| 图 2 全部 210 任务 | `fig2_cpu_a.jsonl` (106), `fig2_cpu_b.jsonl` (66), `fig2_gpu.jsonl` (38) | ✅ 209/210（1 个为 QualityAgent 正确中止） |
| 图 2 CDS 空跑（18/20 靶点；Zika/FVIII 为 LinearDesign OOM 边界，记录在案） | `fig2_cds_nulls.jsonl` | ✅ |
| 图 2 文献面板（IRES 53 + 小分子 17） | `fig2_literature_panels.jsonl` | ✅ |
| 图 2 汇总统计 | `fig2_summary.json`（`experiments/analysis/summarize_fig2.py` 可随时重生成） | ✅ |
| 锚点数据（20 WT CDS、疫苗序列、pegaptanib、IRES、小分子） | `data/benchmarks/external_anchors/` + `SOURCES.md` | ✅ |
| 图 3c 锚点打分 | `fig3_anchors.json` | ✅ |
| 3v03 (BSA) 结构 CB 修复 | `experiments/repair_structure_cb.py` 已执行，原件在 `structures/originals/` | ✅ |

## 2. 进行中任务的断点状态

| 分片 | 断点文件 | 已完成/总数 | 续跑命令（在 `rna_agent_system/` 下） |
|------|----------|------------|--------------------------------------|
| 图 3 Type-I 分片 A | `fig3_type1_shard_a.jsonl` | 2/120（6 个 Beta_gal 超时失败待重跑） | `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type1_ablation.py --targets Zika_E_protein,SARS-CoV-2_Spike_WT,Beta_galactosidase,HIV-1_Env_gp120,Luciferase,HPV16_L1,Ovalbumin,Growth_hormone,IL-2,IFN_alpha_2a --resume --timeout 5400 --output experiments/results/fig3_type1_shard_a.jsonl` |
| 图 3 Type-I 分片 B | `fig3_type1_shard_b.jsonl` | 17/120（全部成功） | `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type1_ablation.py --targets Factor_VIII,HER2,Transferrin,Albumin,RSV_F_protein,Influenza_HA_H1N1,A1AT,GFP,EPO,Insulin --resume --timeout 5400 --output experiments/results/fig3_type1_shard_b.jsonl` |
| 图 4 Type-II 分片 A | `fig4_type2_shard_a.jsonl` | 9/120（11 个 BSA 失败待重跑，结构已修复） | `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type2_ablation.py --targets BSA,Carbonic_anhydrase_II,Chymotrypsinogen,Concanavalin_A,Cytochrome_c,Ferritin,GFP,Lysozyme,MBP,Myoglobin --resume --output experiments/results/fig4_type2_shard_a.jsonl` |
| 图 4 Type-II 分片 B | `fig4_type2_shard_b.jsonl` | 9/120（Papain 瞬时失败待重跑） | `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type2_ablation.py --targets Papain,Pepsin,RNase_A,SARS-CoV-2_Nucleocapsid,Streptavidin,Subtilisin,TNF_alpha,Thrombin,Trypsin,VEGF --resume --output experiments/results/fig4_type2_shard_b.jsonl` |

**重要**：
- 图 3 分片 A 必须用 `--timeout 5400`（Beta_gal 在四片竞争下超过默认 3600s；其他失败均为瞬时，重跑即可）。
- 4 个分片可同时后台运行（服务串行处理，瞬时失败由末尾的统一续跑兜底）。建议开机后先跑 2 片（如图 3 两片），再跑图 4 两片，减少竞争。
- 关机时正在执行的任务（Beta_gal r2 rep2、Albumin r1 rep2、Carbonic r2 s2、Pepsin r1 s0）未写记录，续跑时会自动重做，无需特殊处理。
- 每个分片首遍完成后，**再用同一命令跑一次**（--resume 会只重跑失败项），直到失败清零或确认为边界案例。
- **EOF 提示崩溃已修复（2026-07-19）**：CLI 在服务预检部分失败时会问"是否继续? (y/n)"，非交互 stdin 下 input() 撞 EOF 秒崩。`run_task_dict` 现在以 `input="y\n"` 启动子进程（自动答 y；服务真死则运行照常失败并由 resume 重试）。所有 2026-07-19 之后启动的分片均使用补丁版驱动。

## 3. 待启动（未开始）

- 图 5 机制消融（手册 §7）：需先在 `AptamerCoordinator` 加反馈模式开关（`APTAMER_FEEDBACK_MODE`），脚本 `experiments/run_bmc_mechanism_ablations.py` 待写。
- 图 6 智能体层（手册 §8）：需确认 QualityAgent/SynthesisAgent 的 provider 切换；脚本 `run_quality_ablation.py`、`run_llm_backend_comparison.py` 待写。预算 < ¥250。
- 图 7 案例管线（手册 §9）：3 个 pipeline JSON + `run_case_study_pipelines.py` 待写。
- 图 3d 参考点引导（手册 §5.2）：`run_reference_point_steering.py` 待写（Spike/EPO × 3 配置 × 3 重复，先导串行 pilot 定池范围）。
- 图 4c/d 已知适配体验证：`run_known_aptamer_validation.py` 待写（锚点已就绪）。
- 绘图与成稿：`plots/plot_fig{2..7}.py`。

## 4. 已知边界/发现（写入论文相应章节）

- LinearDesign 对 ~7 kb+ CDS OOM（SIGKILL）：Zika (10 kb)、Factor VIII (7 kb)——操作包络限制。
- 两款获批疫苗（BNT162b2/mRNA-1273）接头窗口 AUG/Kozak 弱配对——掩埋检查是软指标。
- RNAsmol/GerNA-Bind 在短适配体上区分度弱（AUROC ~0.5）——工具训练分布边界。
- sirna GC-rich 任务被 QualityAgent 正确中止——治理能力正面案例。

## 5. 分析注意

- 所有分析用 `experiments/analysis/` 下的 `stats_utils.py`（Wilcoxon/Cliff's δ/BH-FDR/bootstrap AUROC）。
- JSONL 同一 task/target 可能有多条记录（失败+重试），**取最新一条**。
- 图 3/图 4 的 utopian 参考点下 best_candidate 的 `asf_distance` 可能为 0（参考点即最优候选本身）；BMC vs 串行比较用统一固定参考点 ASF + 各目标分量 + Pareto 超体积。
