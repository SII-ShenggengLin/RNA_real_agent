# 交接提示词（2026-08-07：S0 验证发现 C2/C4 结构性冲突,全 20 靶点扫描后台运行中,等用户拍板）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E5_IMPL_READY_S0_RUNNING.md`（实施完成）→ `HANDOFF_2026-08-07_E5_CONSTRAINTS_FIXED_VERIFY_PENDING.md`（三处失败修复+约束拍板）→ **本文件（验证发现 C2/C4 冲突,扫描运行中,方案待拍板）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`,主工程 `rna_agent_system/`（所有命令带绝对路径或同条命令内 `cd`,Bash cwd 每次调用可能重置,勿依赖持久）。

## 0. 一句话现状

**S0 验证第一步发现池通过率与预期严重不符（Insulin 6/36,预期 ≥18/36;追加诊断 A1AT/EPO 均 0/36）。根因 = C2（6x 同聚物）/C4（4 克隆位点）与 LinearDesign 生成分布结构性冲突（长 CDS 普遍命中）,且部署的 LinearDesign 二进制无 DFA 约束（论文机制未实现）→ 生成端无法根治,只能判定层处置。用户已拍板"先停,查文献定 C2/C4 方案"。文献依据已查齐;**全 20 靶点池级扫描正后台运行（PID 1043348）**,完成后离线重放阈值矩阵 → 呈用户拍板 → 改驱动 → pytest → 同步 PREREG → 重跑 S0 → 判定书 → S1/S2。**

## 1. 本会话已完成（勿重做,均在磁盘）

### 1.1 驱动验证（交接文档 §2.1 第一步全部执行）
1. **import 检查** ✓（`experiments.run_e5_constraint_nav` 可导入）
2. **离线自测** ✓ `/tmp/e5_selftest.py` → **ALL PASSED**（32 项,零微服务依赖）
3. **Insulin 池重放 ×2** ✓（`/tmp/e5_pool_replay.py`）:两次**完全一致**（seq_fp `a94bf3275526`、通过率、逐约束全同）→ **缓存确定性验证通过**。但通过率 **6/36 全过**（预期 ≥18/36）,per-constraint：C1 36 / C2 18 / C3 36 / C4 36 / C6 24 / C7 18 / M1 36。全过候选 = λ4.0×short UTR5(3) + λ10.0×short UTR5(3),**仅 2 个 distinct λ**。
4. **pytest 全量** ✓ **649 passed, 1 skipped**（24.97s;驱动未改,基线一致）。

### 1.2 多靶点诊断（关键新发现,用户已确认方向）
- **A1AT:0/36 全灭**。C2=0（4 个 λ 的 CDS 全部含 `CCCCCC`,1254nt 长 CDS）;C4=0（4 克隆位点中至少 1 个必中）;C7 拦 λ0/1（全长最长茎 36/32bp,λ4/10 为 20/19bp）;C6 健康（λ4/10 窗口茎 9–10）。
- **EPO:0/36 全灭**。C2=9（仅 λ1.0 无同聚物）;C4=18;C7 全过（茎 ≤29）;C6 健康（λ4/10 窗口茎 5–8）。
- **结论**：C2/C4 是**结构性杀手**（非 Insulin 特例,非 UTR 样本问题;长 CDS 上 6x 同聚物/克隆位点概率性必现）。C6 的 Insulin 特例（medium/long UTR5 窗口茎 11/15 > 10）在 A1AT/EPO 上不成立（C6 健康）→ C6 是 Insulin UTR5 样本特例。
- 诊断明细：λ=0.0 CDS `GGGGGG` @cds207;λ=0.0 全长最长茎 42bp;λ=4.0 medium UTR5 窗口茎 11bp **跨 UTR5/CDS 边界**（ext 68–91）、long UTR5 15bp **在 UTR5 内部**（ext 29–63）。

### 1.3 文献依据（已查齐,`relevant_references/` 三篇 + WebSearch）
- **C2 同聚物**：mRNAArchitect（bioRxiv 2024）**明确避免 6nt poly(C)/poly(G)**（C2=6 有直接出处）;Twist Bioscience 合成硬拒绝线为 **≥14bp**,6–13bp 属"应避免但非硬拒绝";OpGene 移除 AAAAAA。→ C2 阈值 6 合理,7/8 属灰色区（有"可放"空间但无直接出处）。
- **C4 克隆位点**：PMC10935487 Table1（密码子优化对比）避免 NheI/EcoRV/NotI/BamHI/BspEI;mRNAArchitect 硬约束避免 BsaI/XbaI/XhoI。→ 克隆位点规避是标准做法,位点清单属设计选择;当前 4 位点（BamHI GGAUCC/EcoRI GAAUUC/XhoI CUCGAG/NotI GCGGCCGC）均为标准克隆位点。
- **关键结构性事实**：LinearDesign 官方二进制（`external_repos/LinearDesign/bin/LinearDesign_2D.real`）仅支持 `--lambda/--codonusage/--verbose`;**论文的 DFA 编码约束（禁限制位点/稀有密码子,Extended Data Fig.3c）在开源版未实现**;微服务（8014 `microservices/lineardesign_service/main.py`）同样只暴露 lambda/codon_usage/verbose。→ **C2/C4 无法生成端根治,只能判定层处置（阈值调整/软约束化）**。
- 类比先例：C5（剪接共识）已因"体外转录无剪接"拍板降软约束;C4 克隆位点同理（交付物是 mRNA 序列,克隆位点仅 DNA 载体阶段有意义）——可作拍板讨论依据,但**是否降软约束由用户定**。
- 检索来源：mRNAArchitect https://www.biorxiv.org/content/10.1101/2024.12.03.626696v1.full.pdf;Twist https://www.twistbioscience.com/faq/gene-synthesis/are-there-any-sequence-limitationsdesign-guidelines-genes-which-i-should-follow ;PMC10935487 Table1 https://pmc.ncbi.nlm.nih.gov/articles/PMC10935487/table/tbl1/

### 1.4 工程产物
- 扫描/重放脚本：`/tmp/e5_pool_survey.py`（扫描,已启动）、`/tmp/e5_survey_replay.py`（离线重放矩阵,语法 OK,待跑）、`/tmp/e5_pool_replay.py`（Insulin 重放,已用）。
- GEMORNA 缓存 `experiments/results/e5_gemorna_cache.json` 现含 **18 条**（Insulin/A1AT/EPO 各 6）——扫描为 A1AT/EPO 追加了 6 条,后续 S1 直接复用。

## 2. 正在运行——必须监控（本会话唯一未完成的后台任务）

**全 20 靶点池级扫描**：
- 进程：PID **1043348**（setsid nohup,脱离会话;`pgrep -f e5_pool_survey` 可查）
- 日志：`experiments/results/e5_pool_survey.log`（每靶点一行 `[i/20] TARGET: pass-all N/36 per={...}`,末尾 `DONE ... -> .../e5_pool_survey.json`）
- 输出：`experiments/results/e5_pool_survey.json`（每候选：constraints 快照、max_hp_run、hp_base、restriction_hits、c6_win_stem、c7_full_stem、gc_min/max、序列快照）
- 启动 09:14:49;A1AT（1254aa）生成较慢,预计**总 40–60min**,完成时间约 10:00–10:15
- 监控方法：`until grep -q "^DONE" <log> || ! pgrep -f e5_pool_survey; do sleep 30; done`（或每 5min tail 日志）
- 依赖：微服务 8004/8014/8015（勿杀,驱动会幂等自启）;会调用 80 次 LinearDesign + 120 次 GEMORNA（写缓存）+ folds
- 若进程已退出但无 DONE：读日志尾部找 traceback,报告用户

## 3. 未完成——下一会话第一步（严格按序）

1. **收扫描结果**：等 `DONE` 行出现（或进程退出）;确认 `e5_pool_survey.json` 20 个靶点齐全。
2. **跑重放矩阵**：`PYTHONPATH="$(pwd):$PYTHONPATH" python /tmp/e5_survey_replay.py`（零新调用,纯离线）→ 输出现状 vs 各 C2×C4×C6 组合的通过率分布、zero-targets、每靶点明细、λ 多样性恢复情况。**重点看**：
   - C2 6→7/8 各救回多少;C4 去位点/软约束各救回多少;C6 10→12/14（Insulin 特例）
   - 组合目标：pass≥5 的靶点数、λ 多样性 ≥3 档（D2 判据）、端到端通过率可行性
3. **呈用户拍板 C2/C4（±C6）方案**（预注册项改动,先呈,不改不跑）：
   - 候选方案（供讨论,勿自行决定）：A. C2 6→8（mRNAArchitect 6nt 是"避免"级,Twist 硬线 14bp;灰色区）;B. C4 降软约束（档案记录命中位点,类比 C5 先例——体外转录无克隆）;C. C6 10→12/14（Insulin 特例）;D. 组合。
   - 附带影响提示：约束矩阵 7 条 → 若 C2/C4 软约束化则剩 5 条（C1/C3/C6/C7/M1）;S1 判据"约束满足率分母 7"与"端到端通过率 5 候选全过"随之变化;R4 约束满足候选子集定义同变。**PREREG §4/§7/§9/§13-1 全部要同步**（只增注记,保留原拍板文本）。
4. **拍板后实施**（顺序）：
   a. 改 `experiments/run_e5_constraint_nav.py`（阈值/软约束/档案字段）
   b. `python -m pytest -q` 全量（当前基线 649 passed, 1 skipped）
   c. 重放 Insulin 池 ×1 确认（`/tmp/e5_pool_replay.py`,~2min）
   d. 同步 PREREG（§4 实施修正注记、§7.1 分母、§9 判据、§13-1）
   e. **重跑 S0**：`echo "=== rerun after C2/C4 pin $(date) ===" >> experiments/results/e5_s0.log`;`setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s0 --targets Insulin --repeat 3 --resume >> experiments/results/e5_s0.log 2>&1 &`;`pgrep -af run_e5_constraint_nav` 确认;挂 until 循环等 `e5_verdict_s0.json`
   - S0 判据（§9）:约束识别 100% / 输出格式完整（每画像 5 候选）/ R2 τ≥0.8 / 无崩溃 / ≤40min（**不含池通过率**）
   f. 呈 S0 判定书 → 用户确认 → S1（5 靶点 A1AT,Insulin,EPO,GFP,IL-2 × 3 臂,~1.5–2h）→ S2（20 靶点,2 分片串行）
5. 当天更新 `experiments/results/MODEL_API_USAGE.md` 实测行。

## 4. 关键状态与指针

- **后台任务**：扫描 PID 1043348（唯一运行中;本会话的 until 循环随会话关闭消失,需重挂）。
- **微服务 8004/8014/8015 在跑**（S0 首跑拉起的,勿杀）。
- **未 commit**：`experiments/run_e5_constraint_nav.py`、`agent_core/calibrated/models.py` 修改都在工作区;git 操作必须先问用户。
- **缓存**：`e5_gemorna_cache.json` 18 条（Insulin/A1AT/EPO）。
- **未产出**：`e5_verdict_s0.json`、`e5_s0_runs.jsonl`（S0 无成功记录,`--resume` 等价全新跑）。
- **PREREG 未同步**（§4 实施修正注记、§9 分母 7、§13-1,等待本次 C2/C4 拍板后一并写）。
- **脚本**：`/tmp/e5_selftest.py`（已过）、`/tmp/e5_pool_replay.py`（已用）、`/tmp/e5_pool_survey.py`（运行中）、`/tmp/e5_survey_replay.py`（待跑）。
- **文献**：`relevant_references/`（mRNAdesigner/LinearDesign/Joint5'UTR pdf;文本在 /tmp/mrnadesigner.txt 等）+ WebSearch 依据（见 §1.3）。

## 5. 工程纪律（用户既定规则）

1. git 操作必须先问用户（commit/push/reset）。
2. pytest 基线 649 passed, 1 skipped;改代码后必跑全量（约 25s）。
3. 简洁优先;锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项改动必须先呈用户**（C1/C5/C6/C8 已拍板;本次 C2/C4/C6 再调整同样先呈,附文献+分布数据）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程;命令同条内 cd,勿依赖 Bash cwd 持久。
7. 决策文化：重大路线由用户决定,助手给建议与证据;论文 Nat Methods 直冲,不做提前预注册公开。
