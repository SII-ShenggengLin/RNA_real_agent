# 交接提示词（2026-08-07 02:20 UTC：E4 全矩阵 120 战役已收口，仅剩 HPV16_L1 补齐重跑在跑；新会话接管收尾）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-05_E4PREREGISTERED.md`（预注册）→ `HANDOFF_2026-08-05_E4FULL_RUNNING.md`（启动）→ `HANDOFF_2026-08-05_E4FULL_MIDRUN.md`（中段监控）→ `HANDOFF_2026-08-06_E4FULL_PAUSED_RESTART.md`（暂停/续跑）→ **本文件（最终收尾）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`；**注意：Bash 工具的工作目录每次从项目根初始化，启动后台任务时须在同一条命令内 `cd rna_agent_system &&`，`&` 后的前台命令用绝对路径**——本会话曾因此踩坑）。
> 写本文件时：**E4 全矩阵 120 战役全部跑完（A shard `Done: 44 ok, 4 failed, 32 skipped` 正常退出；B shard 早前收口）。唯一收尾动作 = 等待 HPV16_L1 补齐重跑完成 → 合并分析出判定书 → 报告双终点 → 更新 MODEL_API_USAGE.md。** 用户已拍板重跑 HPV16_L1（2026-08-07 02:17 启动）。

## 0. 一句话现状

**E4 全矩阵（120 战役）已完整收口，双驱动均正常退出。** 全矩阵仅 1 个非预声明失败 cell：B/memory HPV16_L1（QualityAgent LLM JSON 解析错误，瞬时故障概率高），用户已拍板 `--resume` 精准重跑补齐（只跑该 1 场，其余 3 场 skip）。**重跑 02:17 启动，本交接写完后仍在跑或已出结果**——新会话第一步先确认其结果。完成后按 §3 收尾流程走完即可。**若重跑再次失败：报告用户，勿自作主张（备选：再次重试 / 接受该 cell invalid 直接分析）。**

## 1. 已完成（勿重做）

1. 预注册、驱动改造、双终点分析脚本、测试基线（649 passed, 1 skipped）、git 提交 `3a2cf63`、MODEL_API_USAGE.md 预登记 240 次——均已完成，勿重做。
2. **本次会话（08-06 07:00 UTC 起）**：续跑两 shard（--resume）→ 全矩阵跑完（B shard 40/40 于 08-06 09:1x 收口；A shard 80/80 于 08-07 02:1x 收口，`Done: 44 ok, 4 failed, 32 skipped`）→ 启动 HPV16_L1 补齐重跑（进行中）。
3. 运行期观察（已记录、已向用户报告）：
   - **A1AT（C/memory c13）首跑失败**（empty_candidate_list）→ **重跑成功**（evals=7）→ 已恢复计入，无需再处理。
   - **HPV16_L1（B/memory c16）失败**（QualityAgent: Parse error on content，候选已生成 9 个后 LLM 质量评估输出解析失败）——非预声明，用户已拍板重跑补齐。
   - 预声明 cell 确定性失败形态：Zika_E_protein、Factor_VIII 在 memory 臂 cli_failure（empty_candidate_list），nomem 臂 OK+evals=9/final_lambda=None——均属预期，勿重启。

## 2. 最终数据状态（跑完快照，勿误读）

- **shard A**（A,B 组 80 场）：JSONL 82 行（76 success + 6 fail 记录）。fail cells：A/memory Factor_VIII、A/memory Zika、B/memory HPV16_L1（重跑中）、B/memory Zika（前 3 个预声明）。
- **shard B**（C 组 40 场）：JSONL 43 行（38 success + 5 fail 记录：C/memory Factor_VIII ×2、Zika ×2、A1AT 首跑 ×1——A1AT 有 success 记录）。fail cells：C/memory Factor_VIII、C/memory Zika（预声明）。
- 合计：**119/120 success**（补齐 HPV16_L1 后 120/120），预声明失败 5 个（Zika ×3 组 + Factor_VIII ×2 组 memory 臂），A1AT 已恢复。
- 记忆根 `workspace/e4_full/case_memory/{A,B,C}`：A 5 条、C 7 条、B 随 B 组进度写入（驱动按 JSONL 重建，勿手工改动）。

## 3. 收尾流程（按序执行，第 1 步已完成一半）

1. **确认 HPV16_L1 重跑结果**（本交接写完后可能已完成）：
   ```bash
   pgrep -af run_e4_learning_curve | grep -v "bash -c" | grep python   # 应无进程（重跑完成退出）
   tail -3 rna_agent_system/experiments/results/e4_full_shard_a.log     # 应见 "[4/4] ... OK in Ns" 或 Done 行
   python -c "import json; rows=[json.loads(l) for l in open('rna_agent_system/experiments/results/e4_full_shard_a.jsonl')]; print([r for r in rows if 'c16_HPV16_L1' in r['task_id']][-1]['success'])"
   ```
   - 成功（success=True）→ 直接进入第 2 步。
   - 再次失败 → **报告用户**（备选：再重试一次 / 接受 invalid 直接分析，由用户定）。
2. **合并分析出判定书**（预计 ~几分钟，跑在 rna_agent_system/ 下）：
   ```bash
   PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e4_analysis.py
   ```
   输出 `experiments/results/e4_full_summary.json`（pass_criteria + endpoints + go_no_go）。双终点判定规则（预注册锁定）：
   - **效率终点**（两分量都需）：① memory 斜率显著为负（per 组 per 臂回归；3 组 memory 斜率单样本 t one-sided less p<0.05）② 预算节省 1−Σmem/Σnomem ≥25%（配对成功 cell；预声明失败 cell 排除）。
   - **设计收益终点**（任一指标过即可）：4 个已验证指标（CAI↑、全长 MFE↓、接头 mfe/nt 均值↓、GemORNA MRL↑）配对 Wilcoxon、BH-FDR 校正、Cliff's δ |δ|≥0.3 方向有利 → q<0.05 且 δ 达标 → 指标过。
   - **任一终点过 → GO**；双终点均不过 → NO-GO（退路 = 记忆简化为画像结果复用，见 REDESIGN §6）。
3. **向用户报告双终点 GO/NO-GO + 判定书要点**（效率/设计收益各自过否、关键数字）。
4. **更新 `experiments/results/MODEL_API_USAGE.md`**：E4 全矩阵行预登记 240 次 → 实测（按驱动 JSONL 中 `quality_actions` 统计；试点参考：24 次/12 战役）。
5. **git 提交询问用户**（判定书/JSONL 在 ignored 目录；代码文件是否提交由用户定）。

## 4. 已知观察与预声明失败清单（分析时会列出，报告时对照）

| cell | 失败形态 | 分类 |
|---|---|---|
| A/C/B memory Zika_E_protein、A/C memory Factor_VIII | cli_failure（empty_candidate_list） | 预声明（预期） |
| 各 nomem 臂 Zika/Factor_VIII | OK evals=9/final_lambda=None | 预声明（预期，分析 invalid） |
| C memory A1AT 首跑 | empty_candidate_list | **已重跑成功，恢复** |
| B memory HPV16_L1 | QualityAgent LLM parse error | **非预声明，重跑补齐中** |

## 5. 监控（可选）

- 全矩阵已跑完，剩余仅重跑 1 场（~5-30min）——**无需每小时 cron**；如需，CronCreate `7 * * * *` 指向本文件 §3 即可（会话内有效，关闭失效）。
- 若确认重跑进程已退出且 JSONL 未新增 → 无异常，直接收尾。

## 6. 工程纪律（用户既定规则）

1. **git 操作必须先问用户**（commit/push/reset）。
2. **pytest 基线 649 passed, 1 skipped**；改代码后必跑全量 `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -q`（约 25s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项若需改动，先呈用户**（已拍板项见 `HANDOFF_2026-08-05_E4PREREGISTERED.md` §2，不要自行改动）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程；**命令须同条内 cd rna_agent_system &&，前台检查用绝对路径**。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲，不做提前预注册公开。

## 7. 关键指针

- 全矩阵预注册全文：`experiments/run_e4_learning_curve.py` docstring。
- 前序交接：`experiments/results/HANDOFF_2026-08-05_E4PREREGISTERED.md`、`HANDOFF_2026-08-05_E4FULL_RUNNING.md`、`HANDOFF_2026-08-05_E4FULL_MIDRUN.md`、`HANDOFF_2026-08-06_E4FULL_PAUSED_RESTART.md`。
- 试点判定书（管线验证件）：`experiments/results/e4_pilot_summary.json`（overall_pass=True）。
- E4 设计：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 + §5 里程碑。
- 服务由 `ensure_services_ready` 自动拉起（勿手动启动）。
