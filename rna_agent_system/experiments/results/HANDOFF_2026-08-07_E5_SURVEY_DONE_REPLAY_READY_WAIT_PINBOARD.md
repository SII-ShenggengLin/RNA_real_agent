# 交接提示词（2026-08-07 晚：池级扫描完成 + 重放矩阵就绪，C2/C4 方案等用户拍板）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E5_IMPL_READY_S0_RUNNING.md`（实施完成）→ `HANDOFF_2026-08-07_E5_CONSTRAINTS_FIXED_VERIFY_PENDING.md`（三处失败修复+约束拍板）→ `HANDOFF_2026-08-07_E5_SURVEY_RUNNING_WAIT_PINBOARD.md`（验证发现 C2/C4 冲突,扫描运行中）→ **本文件（扫描完成,重放矩阵就绪,等拍板）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`,主工程 `rna_agent_system/`（所有命令带绝对路径或同条命令内 `cd`,Bash cwd 每次调用可能重置,勿依赖持久）。

## 0. 一句话现状

**全 20 靶点池级扫描已完成（18/20 成功,2 生成端失败:Factor_VIII、Zika_E_protein）;离线重放矩阵已跑完（关键数字见 §1.5）。现状 pass≥5 仅 5/20;最优组合 C2<8 + C4 软约束 + C6≤12 达 16/20,剩余不可救 4 靶（HER2/Spike 约束层 + Factor_VIII/Zika 生成层）。拍板材料已呈给用户（§1.6 是完整呈报文本）,等待用户拍板 C2/C4(±C6)。拍板前不改驱动、不跑 S0。无正在运行的后台实验。**

## 1. 本会话已完成（勿重做,均在磁盘）

### 1.1 收扫描 ✓
- 全 20 靶点池级扫描完成:16650s（~4.6h,09:14:49 启动,约 13:52 结束）,输出 `experiments/results/e5_pool_survey.json`（18 靶点,每候选含 constraints 快照、max_hp_run、restriction_hits、c6_win_stem、c7_full_stem、gc_min/max、序列快照）。
- 日志 `experiments/results/e5_pool_survey.log` 完整（每靶点一行 + DONE 行）。
- **生成端失败 2 靶**（不进 JSON,需文档化）:
  - `[5/20] Factor_VIII`:pool generation failed: no CDS produced（~2300aa）
  - `[20/20] Zika_E_protein`:3419aa > LinearDesign 服务 1800aa 上限（`LINEARDESIGN_MAX_AA` 拦截,内存平方增长保护）
- 全 18 靶现状（pass-all N/36）:IL-2 24、Growth_hormone 18、GFP 8、Insulin 6、Ovalbumin 6、其余 13 靶 **0/36**（A1AT/Albumin/Beta_gal/EPO/HER2/HIV-1_Env_gp120/HPV16_L1/IFN_alpha_2a/Influenza_HA_H1N1/Luciferase/RSV_F_protein/SARS-CoV-2_Spike_WT/Transferrin）。
- 每靶耗时:短靶 66–777s,长 CDS 靶 957s(Transferrin)–3737s(HER2)/3221s(Spike)。

### 1.2 跑重放矩阵 ✓（`/tmp/e5_survey_replay.py`,纯离线零调用,~3s）
- **C2 阈值扫（C4=4 位点固定）**:C2<6(现状) 5/20 pass≥5 → <7 9/20 → **<8 11/20** → <9 11/20。C2 是主导杠杆;8 之后无增益。
- **C4 位点扫（C2=6 固定）**:4 位点 5/20 → 单 BamHI 7/20 → 软约束 8/20。单拉提升有限。
- **组合**:C2<8+C4soft 15/20 pass≥5（λ≥2 12/20、λ≥3 6/20）;加 C6≤12 → **16/20**（C6 12→14 无增益）。C2<9+C4soft+C6≤12 仍 16/20（λ≥2 到 14/20）。
- **每靶点明细（C2<8+C4soft+C6≤12）**:A1AT 0→18、EPO 0→33、Albumin 0→27、Luciferase 0→27、IL-2 24、Growth_hormone 18→27、GFP 8→30、Insulin 6→12、Ovalbumin 6→18、Beta_gal 0→9、HIV-1 0→9、HPV16 0→15、IFN 0→18、Influenza_HA 0→18、RSV 0→9、Transferrin 0→6、**HER2 0→0、Spike 0→0**。
- **λ 多样性（严格口径 λ≥3 档/靶点）**:现状 1/20 → C2<8+C4soft(C6 10 或 12) 6/20 → C2<9 亦 6/20。注意 D2 是**每画像**判据（≥3 个不同 λ 或间距≥2 档）,per-target 口径是更严的参考。

### 1.3 不可救 4 靶点（无论怎么调约束都救不回,PREREG 需文档化）
- **HER2、Spike**:~1255aa/~1273aa 最长 CDS;C2=0（8x+ 同聚物必现）、C4=0、C7=9,λ 全空 → 约束层结构性不可行。
- **Factor_VIII、Zika_E_protein**:生成端失败（LinearDesign 长度/aa 上限）→ 生成层不可行。
- 候选文档化方式（供用户拍板时一并定）:S1/S2 排除 + 显式标注,或纳入统计并在论文中报"生成/约束不可行率 4/20"。

### 1.4 文献依据（拍板引用,`relevant_references/` + WebSearch）
- **C2 同聚物**:mRNAArchitect（bioRxiv 2024.12.03.626696）明确避免 6nt poly(C/G)（C2=6 出处）;Twist 合成硬线 ≥14bp,6–13bp 灰色区（"应避免非硬拒"）→ 6→8 有放行空间但无直接出处。
- **C4 克隆位点**:规避是标准做法（PMC10935487 Table1、mRNAArchitect）;交付物是 mRNA 序列,体外转录无克隆阶段 → 类比 C5（剪接共识）先例可降软约束。
- **结构性事实**:LinearDesign 开源二进制/微服务无 DFA 约束（论文 Extended Data Fig.3c 未实现）→ C2/C4 只能判定层处置。
- 来源:https://www.biorxiv.org/content/10.1101/2024.12.03.626696v1.full.pdf ; https://www.twistbioscience.com/faq/gene-synthesis/are-there-any-sequence-limitationsdesign-guidelines-genes-which-i-should-follow ; https://pmc.ncbi.nlm.nih.gov/articles/PMC10935487/table/tbl1/

### 1.5 呈用户拍板材料（§1.6 全文已在会话中呈出;候选方案表）
| 方案 | 内容 | 约束矩阵 | 效果(pass≥5) |
|---|---|---|---|
| A | C2 6→8(硬) | 7 条不变 | 11/20 |
| B | C4 降软约束(档案记录命中位点) | 7→6 条 | 8/20(单拉) |
| C | C6 10→12(硬) | 7 条不变 | 5/20(单拉,Insulin 特例) |
| D(组合) | C2<8 + C4 软 + C6≤12 | 7→6 条 | **16/20** |
- 助手建议（供讨论）:D 案证据最强;保守备选 A+B（15/20,不动 C6）。**是否采纳由用户定。**

### 1.6 呈报全文（本会话最后一次用户可见输出,勿重写）
- 现状:18/20 成功,2 生成失败;pass≥5 仅 5/20,13 靶全灭;每靶点耗时区间。
- 重放矩阵四段（C2 扫/C4 扫/组合/C6 扫）+ 每靶点明细表 + λ≥3 口径表。
- 不可救 4 靶（HER2/Spike/Factor_VIII/Zika）与文档化问题。
- 文献依据三条 + 候选方案 A–D 表 + 附带影响（PREREG §4/§7.1/§9/§13-1 同步、分母 7→6、R4 子集定义变）。
- **待用户回答两件事**:① 选哪案（C2/C4/C6 各自阈值或软硬）;② 4 个不可行靶点的文档化方式。

## 2. 正在运行/可监控的后台任务

- **无正在运行的后台实验**（扫描已结束;本会话的 until 循环随会话关闭消失,无需重挂）。
- 微服务 8004/8014/8015 仍在跑（S0 首跑拉起的,勿杀,驱动会幂等自启）。

## 3. 未完成——下一会话第一步（严格按序）

1. **（可能已拍板）若用户已回复拍板** → 跳到步骤 3。
2. **（尚未拍板）呈拍板材料**:重呈 §1.6 核心数字（重放矩阵可用 `/tmp/e5_survey_replay.py` 重跑,纯离线 ~3s）+ §1.4 文献依据,请用户拍板 C2/C4(±C6) 及 4 不可行靶点文档化方式。**拍板前不改驱动、不跑 S0。**
3. **拍板后实施**（顺序）:
   a. 改 `experiments/run_e5_constraint_nav.py`（阈值/软约束/档案字段）
   b. `cd rna_agent_system && python -m pytest -q` 全量（基线 **649 passed, 1 skipped**,约 25s）
   c. 重放 Insulin 池 ×1 确认（`/tmp/e5_pool_replay.py`,~2min）
   d. 同步 PREREG `experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（§4 实施修正注记、§7.1 分母、§9 判据、§13-1;另加 4 不可行靶点文档化;只增注记,保留原拍板文本）
   e. **重跑 S0**:`echo "=== rerun after C2/C4 pin $(date) ===" >> experiments/results/e5_s0.log`;`setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s0 --targets Insulin --repeat 3 --resume >> experiments/results/e5_s0.log 2>&1 &`;`pgrep -af run_e5_constraint_nav` 确认;挂 until 循环等 `e5_verdict_s0.json`（可用 Bash run_in_background 的 until 循环）
   - S0 判据（§9）:约束识别 100% / 输出格式完整（每画像 5 候选）/ R2 τ≥0.8 / 无崩溃 / ≤40min（**不含池通过率**）
   f. 呈 S0 判定书 → 用户确认 → S1（5 靶点 A1AT,Insulin,EPO,GFP,IL-2 × 3 臂,~1.5–2h,用 setsid nohup + 日志落盘 + pgrep 确认 + until 等完成）→ S2（20 靶点,2 分片串行,注意 Factor_VIII/Zika 按拍板文档化处理）
4. 当天更新 `experiments/results/MODEL_API_USAGE.md` 实测行（本日已发生:80 次 LinearDesign + 120 次 GEMORNA 扫描调用,量级与 S1/S2 相当,若驱动未改可一并记账）。

## 4. 关键状态与指针

- **后台任务**:无运行中（扫描已结束,无需监控）。
- **微服务 8004/8014/8015 在跑**（勿杀）。
- **未 commit**：`experiments/run_e5_constraint_nav.py`、`agent_core/calibrated/models.py` 修改都在工作区;git 操作必须先问用户。
- **缓存**：`experiments/results/e5_gemorna_cache.json` 含 18 条靶点扫描缓存（扫描追加了除 Insulin/A1AT/EPO 外的缓存,S1/S2 直接复用）。
- **未产出**：`e5_verdict_s0.json`、`e5_s0_runs.jsonl`（S0 无成功记录,`--resume` 等价全新跑）。
- **PREREG 未同步**（§4 实施修正注记、§9 分母 7→6（若 C4 软化）、§13-1,等待本次 C2/C4 拍板后一并写;加 4 不可行靶点注记）。
- **脚本**：`/tmp/e5_pool_survey.py`（已跑完）、`/tmp/e5_survey_replay.py`（已跑,可重跑）、`/tmp/e5_pool_replay.py`（Insulin 重放,待拍板后用）、`/tmp/e5_selftest.py`（已过）。**注意 /tmp 可能被清理,脚本内容均为纯离线分析,若丢失可从旧交接文档 §1.4 的接口描述重建或直接读 JSON。**
- **文献**：`relevant_references/`（mRNAdesigner/LinearDesign/Joint5'UTR pdf;文本在 /tmp/mrnadesigner.txt 等）+ WebSearch 依据（§1.4）。

## 5. 工程纪律（用户既定规则）

1. git 操作必须先问用户（commit/push/reset）。
2. pytest 基线 649 passed, 1 skipped;改代码后必跑全量（约 25s）。
3. 简洁优先;锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项改动必须先呈用户**（C1/C5/C6/C8 已拍板;本次 C2/C4/C6 拍板是唯一前置门,拍板前不改驱动不跑 S0）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程;命令同条内 cd,勿依赖 Bash cwd 持久。
7. 决策文化：重大路线由用户决定,助手给建议与证据;论文 Nat Methods 直冲,不做提前预注册公开。
