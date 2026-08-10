# 交接提示词（2026-08-04 W3–4 进行中：E1 扩展已开跑，新会话专用）

> 用法：新会话先读本文件 + `HANDOFF_2026-08-04_W12.md`（当日 W1–2 收官版，含全部工程纪律 §6），再按本文件 §1 执行。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（命令统一带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。

## 0. 一句话现状

W3–4 已开工：E1 扩展锚点集 v2 定稿（6 Part A 靶点 + 5 docking 锚点，66 条目，断言全过），**GPU 画像正在跑**（pid 2419878，Part A 37 条 + Part B 2×21 poses，预计数小时）。E4 执行器路线仍挂起（用户推迟到 W3–4 收尾拍板）。pytest 基线 507 passed, 1 skipped（全天未动 agent_core）。

## 1. 下一步（按优先级）

### 1.0 立即：接管正在跑的 GPU 任务

- **进程**：`pgrep -af "run_e1_capability"`（pid 2419878）。日志 `rna_agent_system/experiments/results/logs/e1_extension_run.log`。
- **注意**：上一会话建的监控 cron（每小时 :23）**不会带到新会话**（cron 会话级）——请重建一个每小时检查任务，或按用户要求手动检查。
- 完成标志：日志出现 `Part B done`。若进程死了先读日志区分正常退出/被杀，再用原命令加 `--resume` 重启（幂等）：
  ```
  cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e1_capability_profiling.py \
    --anchor-set data/benchmarks/external_anchors/aptamers/e1_anchor_set_v2.json \
    --targets "IL-17A,Angiopoietin-2,SARS-CoV-2 N,HIV-1 RT,Factor IXa" \
    --output-a experiments/results/e1_oracle_scoring_v2.jsonl \
    --output-b experiments/results/e1_docking_power_v2.jsonl --resume
  ```
- 完成后跑合并分析（试点+扩展按 id 合并）：
  ```
  cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e1_extension_analysis.py \
    --anchor-set data/benchmarks/external_anchors/aptamers/e1_anchor_set_v2.json \
    --scoring experiments/results/e1_oracle_scoring.jsonl experiments/results/e1_oracle_scoring_v2.jsonl \
    --docking experiments/results/e1_docking_power.jsonl experiments/results/e1_docking_power_v2.jsonl \
    --out experiments/results/e1_capability_summary_v2.json
  ```
- 判定书出来后向用户汇报，并更新：`docs/CHANGELOG.md` 2026-08-04 条目、`experiments/results/MODEL_API_USAGE.md`（E1 扩展零 LLM）、`data/benchmarks/external_anchors/SOURCES.md`（E1 扩展段）。

### 1.1 W3–4 剩余里程碑

1. **锚点基础设施固化**：`anchors/` 目录规范 + curation 脚本模式文档（`curate_e1_anchor_set.py` / `_v2.py` 为模板；v2 的断言模式已验证有效——抓出 AptAF42 长度误读、tNSP9/10 亲本错位、Seq15_12_35 串行字面量笔误）。
2. **E2 自家审计落文**：图 4 主效应 + 图 7B pegaptanib 对比逐条过画像协议复核（数据全在 `experiments/results/`），worked example 写法见 `docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §4 Results 3。不动 GPU，可与画像并行。
3. **W3–4 收尾**：请用户拍板 E4 路线（三选一见 W12 交接 §4.0），然后更新设计文档 §3 E4 + §5 里程碑。

## 2. 今日（W3–4 部分）已落盘的关键资产

- **锚点集 v2**：`data/benchmarks/external_anchors/aptamers/e1_anchor_set_v2.json`（66 条目：试点 29 逐字 + IL-17A 11 + Ang2 11 + SARS-CoV-2 N 15；docking 锚点 = Thrombin×3 + 1HVU + 8EPK）；生成器 `experiments/curate_e1_anchor_set_v2.py`（docstring 含全部出处与 rejected_candidates 注册）。
- **预注册**：`experiments/run_e1_capability_profiling.py` docstring「E1 EXTENSION PRE-REGISTRATION」段——含三条严谨性补丁（用户讨论后定）：阈值敏感性网格（AUROC 0.6–0.9 × ρ 0.4–0.7）、EF@top-3/EF@25%、「reliable/across targets」措辞纪律；ranking 限 `ranking_eligible` 同 assay 子集。
- **分析**：`experiments/analysis/e1_extension_analysis.py`（合并试点+扩展 jsonl，输出 `e1_capability_summary_v2.json`）。
- **驱动扩展**：`--anchor-set` / `--targets` 参数（试点默认值不动）；NUC_MAP 加 8EPK 修饰残基（A2M/ATD/CFZ/OMC/OMG/OMU/UFT），DROP_ATOMS 加 `CM'`/`CM2`。
- **蛋白 fasta**：`aptamers/proteins/{il17a,ang2,sars2n}.fa`（curation 脚本从 UniProt 全长生成，断言校验）。
- **结构**：`aptamers/structures/{1hvu,8epk}.pdb`。
- **文献缓存**：`experiments/lit_cache/`（五篇用户下载 PDF 的文本层 + EPMC 全文 XML + 补充包；注意 `parvez2026_il17_rsc_maintext.*` 是正文、`parvez2026_il17_rsc_si_real.txt` 才是真 SI）。

## 3. 靶点终选与注册偏离（勿再争论，细节全在 curation docstring）

- **Part A 6 靶点**：Thrombin / VEGF / PDGF-BB（试点）+ IL-17A / Angiopoietin-2 / SARS-CoV-2 N。
- **Docking-only**：HIV-1 RT（1HVU，4.75 Å 低分辨率已注册）、Factor IXa（8EPK 2.65 Å）。
- **出局（注册偏离）**：SARS-CoV-2 RBD（仅 2 条单序列 binder，di/trimer 是多价构建体）、Tenascin-C（Hicke 2001 决定性数据全图版）、EGFR（个体 Kd 图版）；HIV-1 RT / FIXa 的 Part A 因序列证据不足降级为 docking-only。用户问过"是否放宽图版纪律救 Tenascin-C"——建议不放宽，用户未反对。
- **重要纠错**：网上流传的"RB006=GGGAGGACGAUG…"序列是 PSMA A9 串扰错误；已排查项目数据未踩雷，curation 有守卫断言。

## 4. 工程纪律（W12 交接 §6 全部有效，重点重申）

- **GPU 单工作者**：画像运行期间不再起任何 GPU 驱动；`GPU_get.py`（pid 35618，20GB）是他租户任务，勿杀勿等；服务常驻 uvicorn 空闲占显存正常。
- **预算匹配铁律** + 预注册写 docstring 再跑；E1 扩展无臂比较（budget N/A，已注册）。
- **pytest 基线 507 passed, 1 skipped**；改代码后必跑（今日只动 experiments/ + data/）。
- **git 操作（commit/push）必须先问用户**。
- **序列核实纪律**：图版序列不收；新条目须正文/表格 + 复核；断言放生成器。
- cron 任务会话级，新会话需重建；已完成任务及时删 cron。

## 5. 悬而未决（W3–4 收尾时问用户）

- **E4 执行器路线**三选一（P1 v1 优化器 / 生成时集成 / E4 暂缓）——用户 2026-08-04 明确表示"先不着急"，W3–4 收尾再拍。
