# 交接提示词（2026-08-07：S0 三处失败已修 + 约束拍板已实施,待验证重跑）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E5_IMPL_READY_S0_RUNNING.md`（实施完成,S0 首跑）→ **本文件（三处失败修复 + 约束拍板实施,验证未完成）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`,主工程 `rna_agent_system/`（所有命令带绝对路径或同条命令内 `cd rna_agent_system &&`,Bash cwd 每次调用可能重置到项目根,勿依赖持久）。

## 0. 一句话现状

**S0 首跑失败三次（①StructuredTool 缺 .func ②AuditEvent 类型越界 ③约束定义与真实序列分布冲突导致池 0/36 全灭）;前两项已修并过 pytest（649 passed）;第三项经用户基于文献拍板后已在驱动中实施（C1→80、C5/C8 降软约束、C6→≤10、GEMORNA 落盘缓存）。当前无运行中实验。下一会话第一步 = 验证驱动（import + 自测 + Insulin 池重放 ×2 验确定性 + pytest 全量）→ 同步预注册文档 → 重跑 S0 → 呈判定书。**（注：以上修改均未 commit;git 操作必须先问用户。）

## 1. 本会话已完成（勿重做）

### 1.1 S0 三次失败的根因与修复（全部已写入磁盘）
1. **①StructuredTool 缺 .func**（S0 首跑在池构建第 4 步崩）：驱动把 `@tool` 装饰的工具当普通函数调用。已修：7 处调用点统一补 `.func(...)`（`experiments/run_e5_constraint_nav.py` 内 `linearfold` / `gemorna_utr` / `gemorna_predict_mrl` / `gemorna_predict_stability` / `cds_cai` / `_fold_mfe`）。与仓库惯例一致（`junction_ddg_pilot_eval.py`、`score_literature_mrna_anchors.py`）。
2. **②AuditEvent event_type 越界**（S0 二跑在 C 臂第一轮 audit 崩）：驱动用了 7 种 event_type,AuditEvent Literal 只允许 5 种。已修：`agent_core/calibrated/models.py` 的 AuditEvent Literal **只增** 6 种（gate_action_reject / gate_constraint_reject / gate_arbitration_reject / gate_repair_round_limit / repair_round / lineardesign_extra）,原 5 种不动。**此修改后 pytest 已跑：649 passed, 1 skipped**。
3. **③约束定义与真实序列分布冲突**（S0 二跑池 0/36 全灭,无崩溃,但 S1/S2 判据必挂）：经离线重放定位 C1/C5/C6 全否,C8 波动(24/36 → 12/36 跨运行),再经三篇文献核对（mRNAdesigner / LinearDesign / joint 5'UTR+CDS,均存 `relevant_references/`）,**用户基于文献拍板**：
   - **C1** GC 滑窗上限 70→**80**（文献无滑窗硬阈值,mRNAdesigner 用目标 GC 偏差;实测 LinearDesign CDS 局部窗口 73–80%,上限 80 全过）
   - **C5** 剪接共识 **降为软约束**（文献 CDS 优化均无剪接过滤——体外转录无剪接;`[AG]G[AC]AG` 5-mer 在 20 靶点 wt CDS 必命中 3–95 次）
   - **C6** 起始区最长茎 `<6` → **≤10**（文献无硬阈值,语义为起始区开放;实测窗口茎 5–14bp,≤10 过 30/36）
   - **C8** 5'UTR 无 uAUG **降为软约束**（真实 5'UTR uAUG 普遍,GEMORNA 生成含 uAUG 是常态且不幂等——Insulin 两次运行 3/3 vs 0/3 preset 含;E4 MRL 已覆盖 UTR 起始质量）
   - **GEMORNA 落盘缓存**（生成不幂等 → 池随机波动不可复现;按 (target, 类型, preset) 缓存到 `experiments/results/e5_gemorna_cache.json`,首次生成后复用,生成预算不变）
   - 约束矩阵 9 条 → **7 条**（C1–C4 + C6 + C7 + M1）;C5/C8 档案键 `C5_splice_motif_count` / `C8_uAUG_count`;C7(≤30bp)保持——有 mRNAdesigner 直接出处
   - **文献依据提取要点**（`/tmp/mrnadesigner.txt` 等可复查）：mRNAdesigner CDS 默认 "maximum stem-loop length: 30 bp"（C7 出处）;CDS 三原则=最小化未配对比例/目标 GC 偏差/避免过长茎;5'UTR 关注起始 30nt 配对状态;无剪接位点过滤。

### 1.2 驱动当前已改内容（`experiments/run_e5_constraint_nav.py`,均在磁盘）
- `CONSTRAINT_IDS = ["C1","C2","C3","C4","C6","C7","M1"]`（7 条）
- `GC_MIN, GC_MAX = 30.0, 80.0`;`START_REGION_MAX_STEM = 10`（判定用 `<=`）
- 池构建与 `_evaluate_candidate_in_pool`：C5/C8 移出 constraints,档案加 `C5_splice_motif_count` / `C8_uAUG_count`;`splice_motif_count()` 纯函数新增
- `_gemorna_cached(utr_type, preset, target_id)` 落盘缓存;`build_pool` 改用之
- docstring §4/§7.1/C 臂 gate/R4/§13-1 全部同步为 7 条 + 实施修正注记
- **GEMORNA 缓存文件已存在**：`e5_gemorna_cache.json`（651B,Insulin 6 条,08:27 写入;utr5 medium 含 2×AUG、utr3 medium 4×AUG、utr3 long 1×AUG——这是用户拍板后首次生成结果,重放 Insulin 池会用这批序列;若想换 UTR 序列,删缓存文件重跑）

## 2. 未完成——下一会话第一步（严格按序）

1. **验证驱动**：
   - `PYTHONPATH="$(pwd):$PYTHONPATH" python -c "import experiments.run_e5_constraint_nav"`（rna_agent_system 下）
   - 离线自测：`PYTHONPATH="$(pwd):$PYTHONPATH" python /tmp/e5_selftest.py`（断言不依赖修改阈值,应 ALL PASSED）
   - **Insulin 池重放 ×2 验证通过率 + 缓存确定性**（两脚本可合并;预期：λ=4/10 的 18 候选全过 7 条 → 池 ≥18/36 全过;两次重放序列/通过率完全一致;注意重放含 LinearDesign/GEMORNA/LinearFold 调用,~2min/次）：
     ```python
     import sys, json
     sys.path.insert(0, "/inspire/.../rna_agent_system")
     sys.path.insert(0, "/inspire/.../rna_agent_system/experiments")
     from run_e5_constraint_nav import build_pool, make_runner, TARGETS_DIR, CONSTRAINT_IDS
     meta = json.loads((TARGETS_DIR / "Insulin.json").read_text(encoding="utf-8"))
     registry, _ = make_runner()
     pool = build_pool("Insulin", meta, registry, log=lambda *a, **k: None)
     n = sum(1 for c in pool["candidates"] if c["flags"]["passed"])
     print(f"pass all {len(CONSTRAINT_IDS)}: {n}/36")
     print({k: sum(1 for c in pool["candidates"] if c["constraints"][k]) for k in CONSTRAINT_IDS})
     ```
   - **pytest 全量**：`python -m pytest -q`（基线 649 passed, 1 skipped;驱动所有修改在 ③ 拍板后**未跑过 pytest**,必须跑）
2. **同步预注册文档** `experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`：§4 约束矩阵加"实施修正 2026-08-07"注记（C1 80 / C5、C8 软约束→7 条 / C6 ≤10 / GEMORNA 缓存）,§9 判据（约束满足率分母 7）、§13-1 同步。保留原拍板文本,追加注记（只增不改）。
3. **重跑 S0**（无成功记录,`--resume` 等价全新跑;缓存已存在→确定性池）：
   `setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s0 --targets Insulin --repeat 3 --resume > experiments/results/e5_s0.log 2>&1 &`（先 `echo "=== rerun after constraint fixes $(date) ===" >> e5_s0.log` 标记;启动后 `pgrep -af run_e5_constraint_nav` 确认;挂后台 until 循环等 `e5_verdict_s0.json` 或进程退出）
   - 预期：池构建 ~2min（CDS 4 次 + UTR 6 次生成/预测 + 36 全长 fold + 12 窗口 fold）→ C 臂 3 重复（每次 ~3–6min LLM + 交付 junction folds）→ 判定书;总 ~25–35min
   - 判据（§9 S0）：约束识别 100% / 输出格式完整(每画像 5 候选) / R2 τ≥0.8 / 无崩溃 / ≤40min
4. **呈 S0 判定书给用户**,确认后 S1（5 靶点 A1AT,Insulin,EPO,GFP,IL-2 × 3 臂,~1.5–2h）→ S2（20 靶点 × 3 臂,2 分片串行）。
5. 当天更新 `experiments/results/MODEL_API_USAGE.md` 实测行。

## 3. 关键状态与指针

- **无运行中实验**（已 pgrep 确认）;微服务 8004 GEMORNA / 8014 LinearDesign / 8015 LinearFold **仍在跑**（S0 首跑拉起的,勿杀;若 down 驱动会幂等自启）。
- **S0 日志** `experiments/results/e5_s0.log`：含三次失败 traceback（①TypeError .func ②pydantic Literal ③池 0/36 后 C 臂 audit 崩——③后进程退出,无判定书）。
- **未产出**：`e5_verdict_s0.json`、`e5_s0_runs.jsonl`（都不存在）。
- **未 commit**：`experiments/run_e5_constraint_nav.py`、`agent_core/calibrated/models.py` 的修改都在工作区;git 操作必须先问用户。
- **预注册文档未同步**（本会话只改了驱动 docstring,PREREG md 待改,见上节第 2 步）。
- **自测**：`/tmp/e5_selftest.py`（纯函数,无需微服务;断言不依赖修改阈值,无需改）。
- **文献**：`relevant_references/mRNAdesigner...pdf`（文本提取在 `/tmp/mrnadesigner.txt`）、`/tmp/lineardesign.txt`、`/tmp/joint5utr.txt`。
- **上一份交接**：`experiments/results/HANDOFF_2026-08-07_E5_IMPL_READY_S0_RUNNING.md`（§4 工程纪律 / §5 指针,仍有效）。
- **MODEL_API_USAGE.md**：E5 预登记行已存在（C 臂 5–9 次/基因、B 臂 2–4 次）;S0 预算 15–27 次。

## 4. 工程纪律（用户既定规则）

1. git 操作必须先问用户（commit/push/reset）。
2. pytest 基线 649 passed, 1 skipped;改代码后必跑全量（约 25s）。
3. 简洁优先;锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改;AuditEvent Literal 本次即为只增）。
4. **预注册项改动必须先呈用户**（本次 C1/C5/C6/C8/缓存均为用户拍板;后续若再需调整,同样先呈）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程;命令同条内 cd,勿依赖 Bash cwd 持久。
7. 决策文化：重大路线由用户决定,助手给建议与证据;论文 Nat Methods 直冲,不做提前预注册公开。
