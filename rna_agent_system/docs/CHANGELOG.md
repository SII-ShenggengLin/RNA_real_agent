# Change Log

- **受影响实验重跑全部完成 + Exp 37（表 1）落地（2026-09-07，DECISIONS (aa) 收官）**：GenNav-默认平台上的四组重跑与三案例全部收尾——**Exp 2+3**：20/20（三大靶无上限补跑；CAI designed 0.896 > WT 0.729 > random 0.675，P=1.1e-06 δ=0.91；MFE/nt −0.297 δ=−1.0，WT/random 不可分 P=0.30），图 2b/c + fig2 组装重渲染；**Exp 24**：241/241、冻结 241 会话/11,003 事件/1,356 门决策（616 拒/586 需画像/154 降级/0 允许），8 个含导航语料库会话在 context 修复后替换重跑（exp24_r3、latest-record-wins），184 个被替换时代未盖章探测事件披露为已知缺陷排除，图 2a/2h/2i/4f 重渲染；**Exp 18**：E3-M 双臂 40/40——FP 36.4%（8/22）→8.3%（1/12）相对削减 77.1%（门 PASS）、越界 7→0、TP 保留 78.6%（14→11）低于 90% 门如实报告（三损失=ClaimGate 未画像家族降级为相对口径，裁决读作 neutral；构建器最近档 λ 解析 + 多映射 echo 校验两项仪器适配）；**Exp 25**：93/93 门 PASS + verify 字节级一致（on 臂 1 次重试恢复；图 4g 重试列首现非空、画布扩宽）；**Exp 37**：三案例全绿——(A) Spike 全长平台默认流 6.6 h（无上限），best CDS CAI **0.969（λ6.5 齿轮）超过 BNT162b2 锚点 0.952**，导航 35/35 打满、stability 档零交付边界如实披露；(B) anti-VEGF v4 导航 23.4 min，top 候选 EGARPS 被工作流自身快速指标门跳过（RhoFold pLDDT<65）、同链 pegaptanib 锚点 0.365、无验证筛选力——自审示例重定位；(C) NSP12 siRNA 106 s、top-5 零脱靶；`--verify` 锚点逐项复现全绿。论文全量重基：§2.2（默认流描述+终数）、§2.4（审计构成/运行时/E3-M）、§2.7+表 1（三案例新数字+披露口径）、摘要/贡献 3、Methods（战役冻结句+E3-M 资产句）、图 2a-e/h/i、图 4d-h 图例；Fig 6/§2.6 移除（用户指示，湿实验小节素材）。运行时口径变更登记：case 墙钟时间为披露的并发负载口径。工程注记：导航探测并发 >800aa 2→4（输出中立）、exp2/exp37 时间上限移除（用户指示，看门狗 60 s 心跳监控+自动恢复替代，pgrep 自匹配 bug 修复）、常驻 ODesign 舰队（6 副本 GPU 0/1/2+8012 轮询代理）、exp2 超时公式三次按实测修订后废除。
- **平台变更 — 全长 mRNA 两步重设计 + 治理化 UTR 池（2026-09-07，用户指示，DECISIONS (bb)，湿实验计划驱动）**：`full_length_mrna_design` 重构为两步协议（GEMORNA 论文的"先选 CDS 再配 UTR"次序）——第一步 CDS 评估后按导航 profile 选 ≤3 条（静态配方取 top-3，共享 CDS 综合分），UTR 抽样从不按 CDS 重采样（消除 UTR 抽样方差对 CDS 排序的混杂）；第二步每 run 一个 UTR 池 = GEMORNA 筛选规模抽样（12 条 5'UTR + 10 条 3'UTR）+ 断言校验基准池（`agent_core/data/utr_benchmarks/utr_benchmarks_v1.json`：BNT162b2 5'UTR 模板验证 51-nt α-globin 来源形（GenBank PP544446 区间 + Xia 2021 描述 + RefSeq NM_000558.5 核心三方一致；仓库锚文件的 3-nt GAG 前缀判定为组装伪迹并披露）、BNT162b2 3'UTR 94-nt AES–mtRNR1（LinearDesign 补充材料逐字，其 COVID 与 VZV 两处完全一致）、LinearDesign 论文 5'UTR 43-nt、天然 HBA1 对 37/111-nt——全部程序化提取零手工转录，加载时 md5/长度/纯度/规则通过断言）。**准入规则只收有文献定量阈值的**：U1 设计 5'UTR 无 AUG（Kozak 1986/1989 扫描模型 + Sample 2019 MPRA）、U2 3'UTR 无 II 类串联 AUUUA ARE（Chen & Shyu 1995）、U3 帽入口 60-nt 窗 MFE > −30 kcal/mol（Kozak 1989：−30 发卡距帽 12 nt 阻止 40S 结合、距 52 nt 无害——规则故意只限帽近端）、U4 扫描路径 150-nt 窗 > −61 kcal/mol（hp7 停滞阈）；**明确不实现**（无可引阈值，登记禁复造）：U 含量上限、GU-rich TLR motif 计数（Vaidyanathan 2018 只做全局 15.5%→12.6% 重编码）、内部 AAUAAA（递送 mRNA 不遇核切割机器，BNT162b2 自己的 5'UTR 就带帽近端 AAUAAA）。5'UTR 短名单（≤6）由已认证 MRL oracle 排序——生成 UTR 只有在 in-silico 胜过临床基准时才会被选中；3'UTR 短名单（≤6）为准入幸存顺序（基准优先，算力上限而非排序）。**utr3_stability 从 ASF 排序目标降级为报告诊断**（ToolSpec evidence_use → scoring_annotation；oracle 在所有注册 task type 下 unprofiled，按 (e) 不得参与排序；reference_point 命名该键改为响亮报错）。输出维持 5'UTR+CDS+3'UTR（用户指示 2026-09-07：加帽加尾由湿实验方按规程处理，系统不输出 poly(A)/cap）。CDS 层零改动（导航委托与 GenNav 核心原样，exp26/27/28/30/31 冰冻仪器不受影响）。测试 686 passed 1 skipped（新增 tests/test_utr_pool.py 19 项 + 两步/准入/门/降级钉扎更新）。**影响面登记与重跑**：Exp 24（22 个全长任务 + PA 全长会话）、Exp 18（E3-M 任务重建）、Exp 37 caseA（表 1）；改动前 in-flight 的 exp37 caseA 第三次运行保留为改动前内部登记。。**重跑结果（2026-09-07 当日落地）**：Exp 24 三跑 241/241 零失败——冻结切片 24,897 事件 = 19,848 调用 + 4,862 门决策（1,800r/489p/1,391d/**1,182a**，allow 类首次非零 = 降级注记用途）+ 187 装配；代表会话 PA_036（2,738 事件）；全长道中位 8.8 min 成为最慢中位工作流（治理池成本如实披露）；239/241 ≤1 h；`--verify` 一致；fig2a/2h/2i/4f + 组合图重渲染，四文档重基；前两时代归档 `_utrgrid/`。Exp 18 三跑 40/40——FP 33.3%→7.7%（76.9% 降幅）、**TP 12/12=100% 双门全过**（navgrid 时代 78.6% 未达门的损失 = never-profiled 降级声明，两步设计后不再产生）；fig4d + 组合图重渲染；旧时代归档 `_navgrid/`。
- **平台默认变更 — GenNav-λ 成为 mRNA 工作流默认 + 受影响实验重跑开启（2026-09-06，用户指示，DECISIONS (aa)）**：`mrna_cds_design` v2.0.0 — `navigation` 改三态（未设置+默认配方 `design_tool="all"` → GenNav-λ 约束导航；显式钉引擎 → 静态配方路径，注册仪器语义逐字保留；True/False 总是覆盖），新增 `resolved_navigation` 单一解析点（物种 fail-fast 合约跟随解析后模式）；`full_length_mrna_design` 新增同语义三态 `navigation` 字段并**原样透传**给 CDS 子工作流（默认策略单一来源 = CDS 层），导航 trace 进入合并 state writeback，导航 CDS 交付与 3×3 GEMORNA UTR 网格组合不变。CapGate 确认默认在线（审计轨迹 + 门决策 + 排名治理装配，模式无关；进程内默认 enforce，战役显式 advisory）。适配体导航保持 opt-in（证据双向，DECISIONS (i)/(aa)）。测试 672 passed 1 skipped（基线 646 + 导航默认套件：三态解析表、全长委托/静态回退/钉引擎保持/显式覆盖、静态路径钉 navigation=False）。Pilot（Insulin 全长 form 入口，新默认）：success、99 候选 = 11 导航 CDS × 9 UTR、best=`full_length:cds_design_gennav:lambda1.75:utr5_short:utr3_long`、ASF 排名带治理标记（`utr5_mrl: transferred`、`utr3_stability: unprofiled`）、审计落 gate_decision/ranking_objective_assembly。**影响面登记与重跑（同指示）**：Exp 2+3（图 2b/c，designed 臂 = 新默认流；静态时代归档 `exp2_cds_nulls_static/`，会话前缀 `exp2nd_/exp2ns_`，driver 追加日期修正案）、Exp 24（图 2a/2h/2i/4f）、Exp 25（图 4g）、Exp 18（图 4d 基础资产）；exp26/27/28/30/31 与适配体/siRNA/结构/小分子各战役不受影响（全部显式钉旗或自建池）。后续：Exp 37（表 1 三案例）。
- **Exp 31 / 图 5d 次级终点渲染（第四次重置，§2.5，2026-09-05，figure-only）**：`experiments/exp31_fig5d_secondary.py` —— 无新测量，面板每个数字从冻结的 Exp-28 记录（`exp28_gennav_mrna_endpoint_v2/full/runs.jsonl`）重算并与存储 verdict 逐项断言相等（c_e2e 0.45 / a_e2e 1.0、Wilcoxon P=0.7309、约束率门 0.9、预算账本），输出 `exp31_fig5d_secondary/panel_data.json`，`--verify` 字节级一致；本 reset 中 5d 此前从未渲染，无旧件可删（登记）。**编码重注册**（FIGURE_PLAN 行 d "pending re-registration" 落定）：三块式单栏——(上) 注册判据 bullet bars：gene-e2e 合取 GenNav **0.45（9/20）vs 0.8 门（legacy 校准）**、规则池 1.00（20/20，交付层上下文——其失败在 JCD 层，见 5b/5c）+ 约束率 **0.944（60 格均值）≥ 0.9 TRUE**（次级判据中唯一成立项）；(中) Δcomposite 逐格堆叠点（fig2d/2f 惯例，**+24/=18/−18，Wilcoxon P=0.73 NS**，方向色沿用 5b 语义、图内不加键——fig5b 惯例）；(下) 逐靶导航花费条带（栈 11–35，**均值 24.55/35、10 靶触顶、10 靶 11–16 早停、违规 0 · LLM 0**）。渲染 `experiments/plots/fig5d_secondary_endpoint.py` → `fig5d_secondary_endpoint.{pdf,png}`，89×74 mm、6 pt 纯黑、palette rev 7、1200 dpi + 矢量 PDF；程序化护栏（全文本画布内 + 两两文本碰撞断言——首版图例行超宽、Wilcoxon 注记压零栈计数两次被拦下后定稿：图例行取消改双注记、计数标签白底衬）；栅格 QA GREEN（精确画布 4205×3496、零边缘墨、纯调色板）；视觉通道对全幅图两次误报（登记过的失效模式），以原生分辨率分块复核 + 确定性几何核查为准。文档同步：FIGURE_PLAN 行 d、PAPER_DRAFT 图例 (d) + §2.5 一处 Fig. 5d 引用、PAPER_FACT_SHEET Exp 31 小节、MANUSCRIPT E6 行、AGENTS.md（含 2026-09-05 用户确认可用 GPU 0/1/2）。
- **Exp 30 完成 / 图 5h 生产实跑数据（第四次重置，§2.5，2026-09-05 用户指示重启并行）**：`experiments/exp30_production_navigation_live.py` 停止后重启——**11/11 表单生产会话全成功（适配体 6 会话，IFN-γ 即 pilot 会话、其记录经 `carry` 带入臂汇总 + mRNA 5），`--verify all` 字节级一致，预算违规 0**。适配体臂（48-raw cap，E14 序列-only 生产路径，`RNADA_CAPGATE=advisory`，质量评审默认开）：IFN-γ 3/3 细胞 47/48 提前停、Ang2 1/3、FGF2 1/3、IL-17A 1/3、PDGF-BB 2/3、**Influenza H3N2 HA 0/3（如实稀缺边界，48 cap 打满）**——共 8 细胞。mRNA 臂（GenNav-λ 35-raw cap，Exp-28 修复版导航器）：PTH 3/3（11/35）、CSF3 3/3（11/35）、LEP 2/3（12/35，交付期 D1 多样性地板降级）、THPO 3/3（28/35）、PLAT 2/3（24/35，同前）——共 13 细胞，全部提前停。逐轮 rounds/probe/交付全量在录。**图 5h 重绘于本数据**（`experiments/plots/fig5h_production_navigation_pareto.py`：成本-交付帕累托散点（11 战役，臂双色彩 + cap 虚线 + 帕累托角环 + 4.3× 同交付成本注记）+ 适配体突破阶梯 inset（gap 链精确重建：IFN-γ 29/35/47、PDGF-BB 36/48、swH3 HA 持平 0；mRNA 阶梯不绘——其 gap→细胞映射被交付期 D1 地板截断，LEP/PLAT 以 2 细胞点如实呈现）；程序化标注碰撞断言 + 键行溢出断言 + 栅格 QA GREEN；89×62 mm、1200-dpi PNG + 矢量 PDF；FIGURE_PLAN 行 h 与 PAPER_DRAFT 图例 (h)、§2.5 正文一句 Fig. 5h 引用已同步；interim Exp-29 sweep 曲线退回 §2.5 正文引用（cap16 10:2 P=0.039 晋升点保留在文中）。**2026-09-05 修订（用户指示，逐条披露于 run 记录）**：(i) 3 个剩余适配体靶复用同序列已有 ProteinX 折叠（IL-17A 用其自身中断会话引用的 CIF=断点续跑等价；PDGF-BB/swineH3HA 用 Exp-29 扩展池最新完整折叠）经 `protein_structure_path` 跳过折叠——ProteinX 折叠跨 run 非字节确定，属披露的协议修订；FGF2/Ang2/pilot-IFN-γ 仍为新鲜折叠序列-only 会话。(ii) 纯基础设施：8012 端口临时由轮询代理（`microservices/odesign_service/roundrobin_proxy.py`）分流至 6 常驻副本（GPU 0/1/2 各 2，taskset 绑核 0-41/42-83/84-127），单请求 ~21 s（vs 子进程 ~90 s），跑毕已恢复原 8012 服务；生产代码零改动。加速效果：IL-17A/PDGF-BB ~22-23 分钟/会话（旧路径 FGF2 88 分钟）。会话工作区 `workspace/sessions/exp30_*`；结果 `experiments/results/exp30_production_navigation_live/{pilot,aptamer,mrna}/`。
- **终稿一致性修正案（2026-09-05，用户指示）**：PA_028（全库唯一导航会话）在最终 v4 导航器下重测——表单生产入口 2/2 turns、4084 s（−35%）；Exp 24 审计切片外科重冻结（`exp24_refreeze_pa028.py`：10,331 事件、reject 709→654、其余 240 会话逐字节保留、新 SHA-256 清单与披露块——原分析器的静默轨迹断言在如今繁忙的审计轨迹上不可重申，故注册外科式替换）；Exp 25 PA_028 三臂串行重跑（并发同靶会互相风暴，改串行）→ 93/93 恒等性保持；fig2i/4f/4g/4h 重渲染；PAPER_DRAFT 审计构成与运行时数字全部更新（10,331/8,810/1,337/184；68.1 min）。
- **Exp 29 / Fig 5e–5g + Fig 5h（第四次重置，§2.5 实验 3，2026-09-03→04）**：适配体战役弧全量重跑（`experiments/exp29_aptamer_campaign_arc.py`，预注册 docstring，RNA-BioBench-Aptamer 20 靶池，双臂 48-cap 预算匹配，零 LLM，100 组配对运行零预算违规，`--verify` 60 记录+判定字节级一致）。四段弧：seg1 松矩阵饱和（b:c=1:1，55/60 both-pass，导航臂 32.7/48 同交付 −32% 成本）；seg2 重锚定稀缺（10:9，静态失败 33%）；seg3 决定性面板 NO-GO（8:9）；seg4 确认（1:8，P=0.039 静态占优）；合并 9:17 P=0.17——**四次分配器版本（shipped/v2/v3/v3b）逐格等价，如实报告为扩散生成器上的诚实边界**。三轮生产修复（v2 收官轮+中心探针；v3 收缩估计+UCB+D1 感知停止判据；v3b 循环选带+UCB 选齿轮）各有单格级可归因修复但总量不动；机制诊断：+15pp/样本信号、ICC 0.30、同齿轮多样性等同——识别成本吃掉集中收益。**保留优势**：seg3 e2e 4:0（唯一端到端交付全来自导航臂）；seg1 −32% 同交付成本；预注册预算扫描（sweep 模式，2026-09-04）：cap24 导航 8 vs 静态 3（b:c=8:3）、cap32 8:8、cap48 持平——**紧预算下交付 2.7×、同交付省 25% raw**（Fig 5h 重定位为成本-交付曲线+成本节省 inset）。生产变更：`gennav_aptamer.py` v3b（central_probe_lengths/adaptive_round/delivery_gaps/shrunken_gear_rate，旧 E8-E14 函数逐字保留）；工作流新增 `navigation_raw_budget` 生产旋钮；测试 test_gennav_aptamer_v2.py 新增、全套 650 passed 1 skipped。机器注记：2026-09-04 恢复 3-GPU（bring-up 均衡分卡恢复），12 ODesign 副本分三卡 + taskset 钉核（GPU 组 0-41/42-83/84-127）+ OMP 封顶——每请求 ~90s 子进程加载的 CPU 瓶颈驯服，sweep 阶段 24 靶 ~90 分钟。**Exp 30（图 5h 原生产实跑设计）2026-09-04 用户指示停止**：pilot IFN-γ 3/3 全交付（47/48 提前停）+ Ang2/FGF2 记录 + mRNA 5 靶已确认清单（PTH/LEP/CSF3/THPO/PLAT）保留于 `exp30_production_navigation_live/`，后续按用户指示处置。论文重定位：§2.5 适配体段 + Fig 5 图例 (e)-(h) + FIGURE_PLAN 5e-h 全部改写为上述结果；Discussion 增加适用边界机制（生成器确定性 moderator：mRNA-λ 确定性格点 17:6 决定性胜 vs 扩散格点等价）。
> **Scope**: interface changes and major workflow introductions.
> **Last updated**: 2026-09-03

> **History policy**: this log records the current interface state and a
> condensed register of the most recent change eras. Full narratives live in
> git history and the audit-evidence directories cited per entry; the
> experimental do-not-repeat register is [`DECISIONS.md`](DECISIONS.md).

## 2026-09-03 — Exp 28：GenNav mRNA 主终点修复重跑（图 5b/5c）+ 生产导航 v2.4 + GPU 变更

- **Exp 29 终版追加（2026-09-04→05，用户指示的 1+3 组合）**：v4 生产导航器（最少服务优先带轮转，修 seg4 带独占缺陷）→ seg3 改善至 **10:3 P=0.092（C24:A17，e2e 4:0）**，seg4 1:8 如实保留；**扩池 RNA-BioBench-Aptamer-Expanded**（12 复合物结构靶 RNA 链剥离 + 7 序列靶 ProteinX 一次折叠缓存）39 靶 × cap 16/20/24/32/48 双臂全档扫描：**cap16 10:2 P=0.0386 显著导航胜（适配体侧升格点）；cap32 10:22 P=0.050、cap48 12:30 P=0.0079 静态胜（双向披露）**；全曲线 nav [10,9,18,17,34] vs static [2,4,15,29,52]（`expanded_summary.json`）。工程：常驻 ODesign 服务（权重驻 GPU、22 s/请求 vs 90 s 子进程路径、输出逐字节一致，`start_resident.sh` 入库）、`navigation_raw_budget` 生产旋钮、ProteinX 折叠按靶缓存、两次关机保存恢复（RESTORE_NOTE）。fig5e/f/g/h 终版重渲染（QA 绿）+ §2.5/图例/FIGURE_PLAN/FACT_SHEET/DECISIONS(29,30)/AGENTS 全部落定。

- **第四次重置第 2 个实验的修复轮（§2.5 实验 2 / paper registry E6，论文引用口径）**：Exp 27 测得 shipped 默认参数批量饥饿（0:24 反转）后，生产导航按注册锚修复——预算匹配（35 = 规则臂原始生成调用数，违规 0）、λ 网格加密至 35 值、带参数逐维对齐注册矩阵（CAI 0.80=CAI_MIN 全带生效、茎 ≤30bp=C7 新增 CDS 级维度、GC 窗 [0.30,0.80]=C1、同聚物 <14=C2）、恢复 legacy E6 组件 3 同义多样化扩展器（密度 0.15、每带 30 上限、零生成预算）、CDS 级 D1 门槛 0.03=P3 标定值、探测并行（>800aa 自适应 2 线程）。三轮 pilot 逐根因校准（D1 贪心/茎维/上限耗尽/稀释边际/stability CAI），护栏测试更新后 25+110 全绿。
- **全量 20/20 零失败，`--verify` 逐字节一致**：**McNemar b:c = 17:6, p = 0.0347, n = 60——配对不一致检验显著偏向导航**；导航 35/60 JCD 格 vs 规则 24/60；18/20 靶有交付（6 靶 3/3）；**HER2（legacy 零可行档靶）交付 1 个导航专属格**；GFP 反向边界（E. coli 滑窗 GC，3 格）；e2e 联合项 0.45 < 0.8 与复合辅终点（Wilcoxon 0.73 NS）如实披露；零 LLM。图 5b/5c 重渲于 exp28 数据（脚本改指新目录），raster QA 全绿。墙钟两段：18 靶 12-LPT-worker ≈ 5.3 h + HER2/Spike 2-worker 8.9 h。
- **中途事件**：2026-09-02 深夜 Spike LD 子进程并发内存下被 SIGKILL（returncode −9）→ RetryInstrument 90 s 单次重试 + 大蛋白探测降并发修复；**2026-09-03 机器关机迁移（GPU 3 卡 → 2 卡，可用仅 0 号，1 号他任务占用）**：bring-up 脚本 GPU 映射全部改钉 0（后续实验同此），exp28 关机保存点后无损续跑（RESTORE_NOTE 留档）。
- 文档同步：PAPER_DRAFT（摘要/贡献 4/§2.5/讨论/Fig 5 图例 b–d/Methods/LLM 用量/数据可用性——描述最终修复系统与实测结果；Exp 27 降为内部边界登记）、PAPER_FACT_SHEET（Exp 28 小节 + 判读核对 + 关键数字 18；Exp 27 标注 superseded）、FIGURE_PLAN_V5 行 b/c/d、MANUSCRIPT E6 行、MODEL_API_USAGE Exp 28 行、AGENTS.md（含 GPU 现状）。

## 2026-09-02 (b) — Exp 27：GenNav mRNA 主终点重跑（图 5b/5c）+ 数据集记录修正（修复前边界测量，内部登记）

- **第四次重置第 2 个实验**（§2.5 实验 2 / paper registry E6）：E6 S2 双终点战役在现行生产平台重测——A 臂 = 注册静态配方池（Exp-26 仪器逐字复用，315 构造体）+ 规则交付；C 臂 = 生产 GenNav-λ 导航模式（`mrna_cds_design navigation=True`，deterministic zero-LLM）；JCD 判据 v8 与双终点从 git `e601913`/`b6dad08` 逐字移植（scope 修正用户拍板 2026-09-02：18 → **20 靶**（+OTC/PDGFB），n = 60）。pilot 2/2 + `--verify` 逐字节一致；**全量 20/20 零失败：主终点 NO-GO 且方向反转——b:c = 0:24（全部偏向规则臂），McNemar p = 1.19e-07，c_e2e_gene = 0.0 vs a_e2e_gene = 1.0**（legacy 30:0 偏向导航臂不复现：决定性优势属于驱动器层的 lattice+GEMORNA 兜底行+LLM 修复轮机制，均不存在于现行 shipped 模式；机制 = 批量饥饿——49/60 格交付 <5 条 CDS、0/60 e2e，而有交付处多样性机制通过（CAI 跨度 0.10–0.18））。辅终点败并披露（约束率 < 0.9、无靶 ≥3 档）；**零 LLM**（legacy 43）。并行提速修正（用户指示 2026-09-02，重启前登记）：8 个靶独占 worker（Exp-24 惯例），墙钟 ≈ 7.2 h（并发负载口径）。图 `fig5b_gennav_mcnemar.{pdf,png}`（配对 dumbbell + 计数 + 置换零分布 inset，Robin EDF 4c 惯例）+ `fig5c_delivery_mosaic.{pdf,png}`（20×3 配对结果 mosaic + gene-e2e 列）；palette rev 7、6 pt 纯黑、绝对 mm、1200 dpi；确定性 raster QA 全绿（精确画布、零边缘墨、纯调色板；画布溢出断言拦下统计块超宽与图例行超宽两次）。
- **数据集记录修正**（用户指示"有误的信息要及时修改"，2026-09-02）：`RNA-BioBench-FullLength-mRNA` 的 manifest 与 `sequences/` 陈旧（列 Factor_VIII/Zika_E、无 OTC/PDGFB），与全部驱动实际读取的 `targets/*.json`（= 现行 20 靶 18+OTC+PDGFB）不一致——manifest targets 列表改正 + 注记、sequences/ 补 OTC.fa/PDGFB.fa 删两个陈旧 fasta、benchmarks README 靶表与总表对齐（含图号列按 FIGURE_PLAN_V5 重定位、PA 行改 31 会话）。
- 文档同步：PAPER_DRAFT（摘要/贡献 4/§2.5/讨论/Fig 5 图例 b–d/Methods 统计/LLM 用量/数据可用性——全部改基到重测的反转结论，适配体侧标注"待其自身重跑"）、PAPER_FACT_SHEET（Exp 27 小节 + 判读核对 + 关键数字 18 改基；legacy E6 小节标 superseded）、FIGURE_PLAN_V5 行 b/c/d、MANUSCRIPT E6 行、MODEL_API_USAGE Exp 27 行、AGENTS.md。

## 2026-09-02 — AGENTS.md 压缩（96 KB → 24.6 KB，用户指示，doc-only）

- 根 `AGENTS.md` 超出 32 KB 建议上限：What's New 段由逐实验叙事体压缩为一里程碑一行的登记表（约 26 条，逆序），
  各实验的协议、预注册、修正、披露与图形 QA 细节不在 AGENTS.md 重复——权威记录在本文件（按日期检索）、
  `PAPER_FACT_SHEET.md`（claim check）与 `MANUSCRIPT.md`（实验手册）；压缩段顶部加了指路注记。
- 顺带修正两处陈旧信息：Standing facts 首条"third programme reset"→ 第四次重置（进度：Figs 2/3/4 + Fig 5a 完成，
  下一步 = Fig 5 其余 + Fig 6）；Testing 基线 635 → 646 passed, 1 skipped（2026-08-25 LinearDesign 密码子表接线后的最新登记数）。
- Standing facts 其余条目、Documentation Index、Project Architecture、LLM Configuration、Multi-Agent Execution、
  Testing 各节逐字保留（git diff 校验：除上述两处外零改动）。无代码、无实验、无图形变动。

## 2026-09-02 — 第四次实验计划重置开启 + Exp 26 执行（Fig 5a：选择层前驱池失败重测，§2.5 实验 1 / 登记名 E5）

**计划重置（用户指示）**：架构再度大改，全部实验重新跑、代码重写——沿用 2026-08-29 第三次重置的
"一次一个实验、只替换当前实验产物"规则与 12 色统一调色板（palette rev 7 原样，用户复述的 12 hex
与之一致）；可用 GPU 0/1/2 不变。legacy E5 证据文件（`e5_verdict_s*.json`、`E5_REPORT`）与旧
fig5a 资产在历次重置中已删除、盘上无待删项；`exp5_*`（声明越界/IRES）属未重跑实验、按规则不动。

**Exp 26（`experiments/exp26_selection_layer_pool.py`，预注册 docstring，协议自 git `b6dad08`
逐字恢复——LD λ{0,1,4,10} + RNARL + GEMORNA 30 采样 = 35 CDS × 9 UTR 组合 = 315 构造体/靶点；
硬约束 C1/C2/C6/C7/M1/CAI 阈值原版；arm-A 规则交付 × 3 画像；D1 交付批次最小两两距离对 2% 门槛）**
：数据集 = 现行 `RNA-BioBench-FullLength-mRNA` S1 五靶子集（A1AT/Insulin/EPO/GFP/IL-2，与
Fig 2b/c/4d 同一套文件——2026-09-02 用户确认）；仪器 = 生产工具路径（ToolExecutor，advisory
CapGate，审计 runtime，2,310 次调用；GEMORNA 8004/RNARL 8008 GPU 2，LinearDesign 8014/
LinearFold 8015 CPU；CAI 本地 Kazusa）；GFP 双接线 = pre-B0 默认 human 表（注册的修复前仪器，
CAI 315/315 全倒）vs 生产 E. coli 表，RNARL/GEMORNA/UTR 档共享、表是唯一杠杆；GEMORNA 采样非
幂等、legacy 缓存已删 → 新实现落盘缓存（实测而非复刻，披露）；LinearFold 全长结构+MFE 单次
确定性调用合并（legacy 折两次，值相同，披露）；零 LLM。**6/6 cell，0 失败（pilot Insulin
123/315、D1 0.0090；全量 35.8 min）：通过数 A1AT 27 / Insulin 144 / EPO 306 / IL-2 297 /
GFP 0→18（default→E. coli 表；通过者恰好全在 λ{4,10} 两档，与注册"可用档仅 λ{4,10}"逐字复现）；
Insulin 交付批次多样性 1.01% < 2% 门槛——λ 饱和失败结构复现（legacy 0.82%）；EPO 306/315 与
legacy 逐数相同（实现巧合，披露）；预注册预期全部命中；`--verify` 六条记录从存储数据重算逐字节
一致。** 图 `experiments/plots/fig5a_selection_pool_pass.py` → `fig5a_selection_pool_pass.
{pdf,png}`（89 × 82 mm 双层条形图：上层固定池通过数 6 条——4 human 灰蓝 + GFP 双条 terracotta/
sage；下层交付批次多样性 5 条按 2% 门槛分色 sage/terracotta + 虚线门槛线；6-pt 纯黑、绝对 mm、
1200-dpi PNG + 矢量 PDF；视觉 QA 一轮修正——门槛标签改置于低于门槛条上方的空白带、面板间隙
加大、旋转标签缩短；栅格 QA：零边缘墨迹、颜色仅出自 12 色调色板、文字纯黑、双面板基线像素级
确认存在）。PAPER_DRAFT（§2.5 句 + Fig 5 图例 a + Methods 战役段 + LLM 用量 + 数据可用性——
全部改引 26/315→18/315、1.01% 重测值）、PAPER_FACT_SHEET（Exp 26 小节 + claim check + 关键数字
16 扩展；legacy E5 节标注为内部登记）、FIGURE_PLAN_V5 行 a、MANUSCRIPT 重置表、MODEL_API_USAGE
（零 LLM 行）、AGENTS.md 更新。**下一步：Fig 5 其余面板（GenNav 战役）+ E21/E22 基线，同模式。**

## 2026-09-01 — Exp 25 执行（Fig 4g + 图 4h：质量评审 advisory 三臂 + 各战役 LLM 用量实测）

**接口变更**：`cli/form_chat.py` 新增 `RNADA_QUALITY_REVIEW` 环境旋钮（默认 `on`，取
`off/0/false/no` 时构造 `AgentRunner(quality_review_enabled=False)`）——仿 `RNADA_CAPGATE`
惯例的批处理/运维开关，交互默认行为不变。这是驱动"评审关"臂走生产表单入口的唯一平台接线
（预注册 docstring 披露）。

**实验**（`experiments/exp25_quality_review_advisory.py`，预注册 + 中途登记修正；pilot 6/6）：
数据集对齐用户指示取全量 31 PA 会话（PA_006–PA_036 = Exp-24 战役 PA 臂；legacy "19" 为其时代
全量）；三臂 × 31 = 93 次表单入口 CLI 子进程（输入逐字、CapGate advisory、GPU 0/1/2 预热；
调度 ≤6 并发、GPU 类工作流 ≤3；墙钟 ≈ 5.5 h，时间非指标）。**93/93：完成 31/31 × 3 臂；工作流级
30/31 × 3（唯一例外 PA_023 = 继承性输入缺口，三臂逐字相同）；跨臂逐轮结果完全一致（0 不匹配）；
评审开臂 144 次成功调用 = 72 被评审轮 × 2；失败注入臂 144 次尝试全部 review_unavailable、0 轮受影响；
重试 0/0/0；`--verify` 字节一致。** 中途修正（分析前、依据 exp8/exp24 冻结证据登记）：双成功判据 +
跨臂配对一致性主终点；PA_023 缺口（`workspace/pa023_5utr.fa`，审计保留期 0 次成功读取）按实测披露、
不重建（重建将与 Exp-24 锚定运行分叉）。

**图**：`experiments/plots/fig4g_quality_advisory_strip.py`（配对条带：31 会话行 × 三臂块，
sage/terracotta 结果 tile × 评审状态字形，分类分隔线上被评审/免评审两段，四样例键行；
canvas-overflow 断言两度拦截旋转表头溢出与键宽低估后改为两行水平表头 + 精确模拟键宽）与
`experiments/plots/fig4h_llm_usage_bubble.py`（气泡条带：8 战役行 × 每任务一泡、面积 = 实测
LLM 调用数、短刻度线 = 零调用任务；零调用空心圆经视觉 QA 判读为占位符后改刻度线）；数据装配
`experiments/exp25_fig4h_data.py`（**Exp-24 的 482 次评审调用自各 run 保存的
`_diagnosis_history` 实测提取**；GenNav 导航战役未重跑、登记排除）。两图 6-pt 纯黑、palette
rev 7、绝对 mm、1200 dpi，确定性 QA 绿（图 4g 视觉 QA 亦通过；图 4h 视觉通道 MCP 调用失败——
已注册失效模式，以确定性 QA 为准）。

**文档**：PAPER_DRAFT（Overview/贡献 1/§2.4/局限/Methods/Fig 1b/Fig 4 g,h 图例/LLM 用量/数据
可用性——19/19 全部改写为 31 会话配对一致口径）、PAPER_FACT_SHEET（Exp 25 节 + claim check，
legacy Fig-6a 节改 superseded）、FIGURE_PLAN_V5 行 g/h + 注记、MANUSCRIPT 重置表、
MODEL_API_USAGE、AGENTS.md。

## 2026-09-01 — Fig 4d 用户指示修订（第五轮：行长标签缩短；无重跑）

- 两个 Sample-2019 文库行标签从 fig3f 全名（"Random 50-nt 5′UTRs" / "Varying-length human 5′UTRs"）缩短为 fig4e 短名惯例（"EGFP random-50" / "Var-len human"）——它们单独撑宽了整个标签列；缩短后标签列宽度由 "Novel 5′UTR 11" 行决定，画布 62.3 × 86.0 → **50.8 × 86.0 mm**。全名仍在 Fig 3f 与 Fig 4e 图注中。同轮附加：底部裁定键从两行各自居中改为**两行共享列网格**（列宽取两行最大值，两列色块/文字左缘分别对齐，整块居中）。数据不变。光栅 QA 同前全绿。文档同步：FIGURE_PLAN_V5 注记、AGENTS.md Exp-18 条。

## 2026-09-01 — Fig 4d 用户指示修订（第四轮：改回第二轮层级条带；无重跑）

- 地毯图（第三轮）经用户评审为不如条带直观，**`fig4d_mrna_family_strip.py` 回退到第二轮的层级家族条带**（家族表头行 + 缩进靶行单列标签、10-mm 臂块、两行居中裁定键、0.5–0.6 lw 细线、62.3 × 86.0 mm 竖版）并重渲染——逐像素统计与第二轮首次渲染逐项一致（可复现）；数据不变（FP 35.3% → 8.3%、TP 11/11）。第三轮地毯图的旋转标签锚定探针结论（matplotlib rotation=90 向下悬挂需 ha="center", va="top"）留档备复用。文档同步：PAPER_DRAFT 图注 (d) 恢复条带措辞、FIGURE_PLAN_V5 行 d + 注记、AGENTS.md Exp-18 条。

## 2026-09-01 — Fig 4d 用户指示修订（第三轮：改图型；同一份 Exp-18 冻结结果，无重跑）

- **`experiments/plots/fig4d_mrna_family_strip.py` 改为转置任务×臂裁定地毯图（oncoprint 式）并重渲染**（`fig4d_mrna_family_strip.{pdf,png}`）：20 任务列按 8 家族分组 × Ungated/Gated 两行，单元格整格填裁定色（白描边空格 = 未发布声明）；家族表头居中于列组上方、按渲染器实测字宽贪心分层（同级间距 ≥0.8 mm 断言、中心钳入画布）；靶名 90° 悬于列下（fig3d 旋转刻度惯例；matplotlib 旋转锚定语义经探针实测——rotation=90 须用 ha="center", va="top"）；可信/不可信块间短竖分隔线只穿地毯区；裁定键单行居中。横版 86.3 × 50.8 mm（与 fig4c/fig4e 同向）。数据不变（FP 35.3% → 8.3%、TP 11/11）。光栅 QA：零边缘墨迹、暗色像素全为纯黑+抗锯齿灰、彩色像素全在调色板→白线段上。文档同步：PAPER_DRAFT Fig 4 图注 (d) 改写为地毯图、FIGURE_PLAN_V5 行 d + 注记、AGENTS.md Exp-18 条。

## 2026-09-01 — Fig 4d 用户指示修订（第二轮；同一份 Exp-18 冻结结果，无重跑）

- **`experiments/plots/fig4d_mrna_family_strip.py` 修订并重渲染**（`fig4d_mrna_family_strip.{pdf,png}`）：(1) 左侧标签区并为单列层级文字列——家族表头行 + 缩进靶行取代旋转类别列与独立家族列（可信/不可信分组改由全宽分隔线承担并在图注声明），回应「左侧两列文字过宽」；(2) 行标签生物学显式化并跨图一致——"Novel UTR 7/11/13" 补回丢失的撇号为 "Novel 5′UTR 7/11/13"，Sample-2019 文库改署 Fig 3f 名 "Random 50-nt 5′UTRs" / "Varying-length human 5′UTRs"，家族表头去折行（"3′UTR stability rank"、"Relative comparison" 等）；(3) 单声明格臂块 18 → 10 mm，臂表头精确居中于色块列；底部裁定键改两行居中；(4) 分隔线与空格描边 0.4 → 0.5–0.6 lw——旧版细线在 1200-dpi 下渲染为事实灰 (42,42,42)，是「有文字发浅」观感来源之一（文字本体经栅格复核旧版即全为 #000000 文字核）。画布 79.5 × 62 → 62.3 × 86.0 mm；palette rev 7 用色、6-pt 纯黑、1200-dpi PNG + 矢量 PDF（fonttype 42）不变。光栅 QA：四边零墨迹、暗色像素全为纯黑+抗锯齿灰、全部彩色像素落在调色板→白线段上。文档同步：PAPER_DRAFT Fig 4 图注 (d)（删过时 mosaic-inset 从句、补分隔线分组说明）、FIGURE_PLAN_V5 行 d + 注记、AGENTS.md Exp-18 条。

## 2026-09-01 — Exp 24: 生产 campaign 共享仪器重跑（Fig 4f + Fig 2a/2h/2i 再测量，§2.4 实验 5）

- **设计**：用户指示「跑一次、登记为共享仪器、冻结切片」——一次 241 运行生产 campaign（210 RNADesign-210 任务 + 31 PA 表单会话，用户入口逐次子进程、输入 verbatim、advisory CapGate、GPU 0/1/2 服务按发行拓扑预热）同时供四个 panel：Fig 4f（按 oracle 的门决策 Cleveland 点图）、Fig 2a（任务毯图）、Fig 2h（代表会话里程碑轨）、Fig 2i（runtime ECDF）。drivers：`experiments/exp24_production_campaign.py`（campaign，预注册 docstring，pilot 4/4）+ `experiments/exp24_run_parallel.py`（编排）+ `experiments/exp24_audit_gate_stats.py`（只读分析器；`--verify` 从冻结切片重算字节一致）。
- **并行修订（用户指示提速，重跑前登记）**：11 个工作流独占并行 worker——同一工作流的运行永不重叠，unstamped 门事件按 payload 工作流键唯一归属（硬断言，0 歧义；歧义即失败而非污染）；单次运行墙钟 = 并发负载下交付的工作流（图注披露）；重试一律新 sid（本次 0 次重试）；两次编排器重启的半途会话按排除披露；并发追加 0 撕裂行。campaign 墙钟 ≈ 6.8 h（串行 legacy ≈ 17.5 h）；利用率全程监控（128 核聚合 CPU 10–60%，GPU 0/1/2 脉冲式、模型驻留）。
- **结果**：241/241、0 失败。冻结审计切片 10,395 事件 = 8,818 tool calls（84.8%，40 工具，3 例孤立瞬时失败）+ **1,392 门决策（709 reject / 549 require_profiling / 134 downgrade / allow 0，11 oracle）** + 185 ranking 组装 + 0 claim。runtime：中位 2.32 min，工作流中位 2.7 s–6.39 min，76.8% ≤5 min，240/241 ≤1 h（最大 = GenNav 导航 aptamer PA_028 104.9 min）。代表会话规则再次选出 PA_036（152 calls + 32 gates [16/8/8] + 3 ranking，7.5 min 跨度）。Fig 2a：210/210。
- **对 legacy（内部登记）**：Exp-9 切片 10,217/8,798/1,377[690/553/134]/42——各项均在几个百分点内复现、downgrade 逐条相等、代表会话相同且分类构成几乎一致；ranking 组装 42→185（当前平台排序治理事件粒度）；Exp-8 runtime 2.6/2.5s–6.29min/98.6min → 2.32/2.7s–6.39min/104.9min（并发口径）。
- **图**：`fig4f_gate_decisions.py`（新 panel：水平 Cleveland 点图、按 oracle 行、三 verdict marker + dumbbell + 计数标注、CASCADE Fig. 5d/e 惯例、verdict 配色沿用 fig2h/4e 惯例）→ `fig4f_gate_decisions.{pdf,png}`；fig2a/2h/2i 重写指向 Exp-24 记录（注册图型不变）；四图栅格 QA 全绿（mm 尺寸正确、零边缘墨、palette 校验）。视觉通道对 fig4f 两次返回旧缓存图（登记过的失效模式）——判不可信，QA 以确定性栅格分析为准。
- **文档**：PAPER_DRAFT（§2.2 审计/runtime 段 + §2.4 Fig-4f 句与数字 + Fig 2 a/h/i 与 Fig 4f 图例 + Methods campaign 段 + Data availability）、PAPER_FACT_SHEET（Fig 2h/2i 节改写为 Exp-24 + Exp 24 节 + claim check）、FIGURE_PLAN_V5（行 a/h/i/f + 共享仪器登记）、MANUSCRIPT 重置表、本 CHANGELOG、AGENTS.md 更新。旧 exp1（覆盖）与 exp8/exp9（runtime/审计）结果目录按重置规则删除（`exp1_bring_up_services.sh` 保留）。

## 2026-09-01 — Fig 4b 用户指示修订（同一份 Exp-17 冻结结果，无重跑）

- **`experiments/plots/fig4b_claim_matrix.py` 修订并重渲染**（`fig4b_claim_matrix.{pdf,png}`）：(1) 删除右上 arm × verdict mosaic inset——其计数已在 Fig 4b 图注与正文陈述（fig2h 删 donut / fig3f 删 waffle 的先例），且其重复的臂标签互相挤压、下方留出整列空带；(2) 行标签改用 fig3 靶标惯例（"IFN-gamma" → "IFN-γ"、"Influenza H3N2 HA" → "swine H3 HA"），"U reduce" 改词为 "U reduction"；(3) 底部四摆片裁定键改为渲染器实测字宽排版（fig4e 惯例）并加画布溢出断言——旧版估算字宽使图例实际比画布宽、靠 tight-crop 外扩；(4) 臂块 12 → 14 mm、块间距 5 → 8 mm，使矩阵主体与单行图例共享画布宽度（tile 1.7 → 2.0 mm）。全部文字维持 6-pt 纯黑（光栅复核：旧版亦全部为 #000000 文字核，无非黑文字）、palette rev 7 用色、1200-dpi PNG + 矢量 PDF。光栅 QA：零非黑文字核、零非调色板色块、tile 内零文字墨迹、四边无裁切。文档同步：PAPER_DRAFT Fig 4 图注 (b) 删 mosaic-inset 从句、FIGURE_PLAN_V5 行 b + 类型清单 + 注记。

## 2026-09-01 — Fig 4c 用户指示修订（同一份 Exp-17/Exp-5 冻结结果，无重跑；数据 59 → 0 不变）

- **`experiments/plots/fig4c_overreach_events.py` 修订并重渲染**（`fig4c_overreach_events.{pdf,png}`）：(1) 臂图例（Ungated/Gated）从悬浮于图顶部（与面板脱开、视觉上像偏置标题）移到面板正下方单行、对轴居中——fig3e「图例贴面板」惯例；(2) y 轴标签从 31 字符的 "Decision-layer overreach events"（6 pt 下超出 23-mm 轴高）缩为 "Overreach events"——decision-layer 限定语在 Fig. 4c 图注中逐字保留；(3) 图几何按新堆叠再平衡（89×44 → 89×40.5 mm，轴 11/12.5/72/23.5 mm，y_top 1.45 → 1.48 使 "59 → 0" 标注完整落于轴内）。子图内无标题维持（Nature 惯例：面板字母组版时加，标题性陈述在图注）。全部文字 6-pt 纯黑（光栅复核：文字核全部 #000000，仅抗锯齿灰晕）、palette rev 7 用色、1200-dpi PNG + 矢量 PDF（fonttype 42）。光栅 QA：四边外 3 px 零墨迹、非条形色块仅调色板两色、无文字/图形重叠。文档同步：FIGURE_PLAN_V5 行 c 注记。

## 2026-09-01 — Exp 23: 选择性门控决策矩阵重跑（Fig 4e，§2.4 实验 4）

- **数据集（用户确认后开跑，与最新重跑对齐）**：认证家族 = Exp-14 MRL 锚集 `e7_mrl_anchor_set.json`（706 / 3 族，Sample et al. 2019 MPRA, GEO GSE114002——即 Fig 3f 的认证基础、Fig 4d 的 MRL 真值，sha256 冻结进 summary）；未剖析家族 = e18 任务集的生产键 `novel_utr_family_7` 及其真实 50-nt 候选；阻断格 3′UTR = 同一 e18 集的生产 Insulin 构造 3′UTR；E1 交叉验证基准 = 保留的 `e7_mrl_scoring.jsonl`。与 Fig 2a–i / Fig 3a–h / Fig 4a–d 的重合核查：Fig 3f 同一文件、Fig 4d 部分取自它（mrl_optimum 两任务）、Fig 2e 同类零重合（706×50 全比对 0 相同 0 包含）、其余无涉。
- **预注册 driver**（`experiments/exp23_selective_gating.py`；pilot 6/6 → 全量 12/12；legacy E7 gate-demo 的重跑，协议恢复自 git 1b45138~1）：12 格三层全走生产路径——DecisionGate 格经 `runtime.review_tool_call` + `oracle_use("ranking_objective", target_family=…)`（与 ToolExecutor 咨询的完全同一条评审）；ClaimGate 格经 `runtime.claim_gate.review`（确定性模板，LLM polish 关）；新增加权执行层经 `ToolExecutor.run_tool` 活体验证（GEMORNA 8004，每判定类一格）。运行时 = `RNADA_CAPGATE=enforce` + 出厂打包默认 SelfModel（29 条记录，Exp-17/18 门控臂的同一仪器；版本漂移无）；15 条平台审计落账；**0 次 LLM 调用**；壁钟 ≈ 6 s。相对 legacy 的披露性扩展（预注册）：三认证家族全测（legacy 只测一个）、生产未剖析家族键取代 legacy 合成标签、打包 SelfModel 取代当次自建、新增执行验证层。
- **结果 12/12 全部符合预注册预期（GO）**：DecisionGate——allow ×3（D1–D3，conf 1.0）、downgrade ×1（D4，transferred、transferred_from_grade=verified、置信度恰为 0.5 = 1.0 × 0.5 衰减、供体 sample2019_egfp_random50、不阻断）、require_profiling ×2（D5–D6，enforce 下阻断）；ClaimGate——pass（C1）/ downgrade（C2，scope absolute → within_target_relative，确定性 `[DOWNGRADED: …]` 改写）/ reject（C3，依赖从未剖析）；执行层——E1 放行执行且 predicted MRL 与 Exp-14 缓存**精确相等**（hi01_egfp_random50，6.28）、E2 降级放行执行（限权是 ClaimGate 的事）、E3 阻断成立（GatedActionError、verdict=require_profiling、gated=true 审计行、耗时 0.0002 s 未触服务）。legacy 4 演示结果一对一复现（legacy 对转移语义的 naive expect_profiling 预期当年如实记为 expectation_met:false——现在降级语义即注册预期）。
- **Fig 4e 绘制**（`experiments/plots/fig4e_selective_gating_matrix.py` → `fig4e_selective_gating.{pdf,png}`，120 × 72 mm）：决策矩阵——DecisionGate 块（6 行：MRL × 3 认证族 + 未剖析族；3′UTR × 2）+ ClaimGate 块（3 行），每行恰一色块落于 allow·pass / downgrade / require-profiling·reject 三列；判定色 sage/mauve/sand/terracotta（fig2h 门控判定惯例）、oracle 竖条 grey blue（MRL，fig3f 色）/ dark warm grey（3′UTR）；右侧置信度 + 工具层注释（D1「score = Exp-14」、D4「conf 0.5 = 1.0×0.5」等）；底部居中四摆片判定键。QA：首轮视觉分析报告多处重叠/裁切→按实测字宽重排（画布 88→120 mm、缩短标注串、拉开列距）重渲染；后续视觉通道命中 CDN 缓存旧图判定不可信，改用确定性光栅 QA 全过——四边零裁切、表头三簇分离（间隙 3.9/7.1 mm）、标注最右 118.1 mm 在界内、图例四簇居中（中心 60.85 vs 60）、分隔线单条无字形相交、行标签与色条垂直居中偏差 ≤ 0.1 mm、D1 行色块恰为 sage+grey blue+GRID。
- **删除面**：本实验在盘无可删旧资产（legacy `e7_gate_demo.jsonl` 久已不在盘——结果保留于 never-delete 的 `e7_mrna_oracle_profile_summary.json`；fig4e 此前未在新程序下绘制）；`e7_*` 证据链属 never-delete 且为打包 SelfModel 证据来源，未动。文档同步：FIGURE_PLAN_V5 行 e + 注记、PAPER_DRAFT（§2.4 句 + Fig 4 图注 e + Methods + LLM 用量 + 数据可用性）、PAPER_FACT_SHEET（Exp 23 节 + claim check + 关键数字 13 补决策矩阵口径）、MANUSCRIPT 重置表 Exp 23 行、AGENTS.md。**Next: Fig 4f–h + Figs 5–6 战役 + E21/E22 baselines 按重置继续，同一模式。**

## 2026-09-01 — Exp 18: E3-M mRNA 侧门控双臂重跑（Fig 4d）

- **任务集按最新数据集重建**（用户指示「与最新的数据集保持一致」；构建器 `experiments/exp18_build_mrna_audit_tasks.py`，断言优先，20 题 = 8 家族 10 可信 + 10 不可信，家族/靶分配与 legacy 相同）：靶标取当前 `RNA-BioBench-FullLength-mRNA` 文件（逐靶密码子表——GFP 按当前注册为 E. coli，legacy 曾四靶统一 Homo sapiens，披露）；CDS 候选 = 生产 `mrna_cds_design` design_tool="all" λ-grid（任务取 λ{0,4,10}、比较取 0 vs 10）；全长度构造 = 生产 `full_length_mrna_design`（utr_mode=all）每靶 top-3 排名唯一构造；MRL 真值 = Exp-14 锚集实测 MRL。可信任务真值 = 生产 CAI 工具（Sharp–Li、逐靶 Kazusa）+ LinearFold MFE + 纯 Python 约束的精确重算；不可信任务分数**不内嵌**，运行期经生产链活体取（GEMORNA 8004 3′UTR/MRL + LinearFold 8015 junction 窗口 MFE/nt + 约束折叠 ddG_open_w1 = 当前平台 junction 报告；junction 计算与设计期工作流值逐位一致交叉验证）。
- **双臂重跑**（`experiments/exp18_mrna_claim_gating.py`，预注册 docstring，pilot 6/6 × 双臂 PASS）：两臂全新运行——未门控 = advisory 全放行；门控 = `RNADA_CAPGATE=enforce` + 打包默认 SelfModel（E7/Exp-14 GEMORNA-MRL 剖析；scoring-由-ranking-蕴含的 legacy 补丁恢复，6 次 pilot v1 运行作废披露）+ 逐家族注册确定性报告指标 + 建时真值执行验证 + ClaimGate。每臂每题恰好 2 次 LLM 调用（deepseek-v4-pro，temp 0；提示词与 git e337ac5 恢复的 legacy E3-M 逐字节相同，仅门控臂加 gate-feedback 块）。确定性盲判（legacy 规则；洗牌 seed 0 + 密封映射；**注册修正案**：decoy 家族上正向断言需以候选 id 为主语——legacy 关键词启发式对门控臂的否定式弃权声明误判）。
- **结果 40/40（20 × 2），0 失败：FP 6/17 = 35.3%（CI 17.3–58.7）→ 1/12 = 8.3%（CI 1.5–35.4）；TP 保留 11/11 = 100%；越权 6 → 0；go-rule 双项通过（降幅 76.4% ≥ 50%、保留 100% ≥ 90%）**。未门控 FP 全部落在 utr3（3/3）+ junction（2/2）+ 一处对称 MRL 排名翻转（最弱认证家族 ρ=0.835，预测 hi30 vs 实测 hi01——两臂同错，即唯一存活的门控 FP，与 legacy 登记通道一致）；门控机制比 aptamer 侧早一层——6 条计划请求被拦后模型在五道 utr3/junction 任务上**完全不发声明**（Fig 4d 白描边空格），3 条跨家族 MRL 绝对声明被降级为靶内相对（neutral），0 压制 0 越权；可信家族 10/10 双臂全 TP，执行验证 0 弃权。
- **平台缺陷披露（构建期发现并绕开）**：全长度结果 JSON 的 `metadata.cds_sequence` 为存储侧截断 echo（200 字符 + "…(truncated)"，ToolExecutor 字符串上限）——设计期评估本身用内存真序列（存储 `cds_cai` 与干净 CDS 的 CAI 精确相等可证），构建器按 cds_source 从 CDS 设计缓存回填真 CDS 并断言前缀一致；修复后五道构造任务重跑（10 次作废运行披露）。用量：80 次有效 + 32 次作废 LLM 调用；壁钟 ≈ 34 min（双臂）+ 设计阶段 64 min（缓存）。
- **Fig 4d 绘制**（`experiments/plots/fig4d_mrna_family_strip.py` → `fig4d_mrna_family_strip.{pdf,png}`）：按任务家族分组配对类别条带——20 任务行 × 两臂块、每发布声明一色块（sage=TP / terracotta=FP / warm grey=neutral，白描边=未发布声明——门控弃权的关键视觉元素）+ 臂×裁定 mosaic inset；palette rev 7、6-pt 纯黑、绝对 mm、1200-dpi PNG；视觉 QA 两轮（首轮标签列相撞，缩短家族/靶标签并加宽标签列）。文档同步：FIGURE_PLAN_V5 行 d + 注记、PAPER_DRAFT（摘要 + 贡献 3 + §2.4 段 + Fig 4 图注 d + Methods + LLM 用量 + 数据可用性）、PAPER_FACT_SHEET（Exp 18 节 + claim check + 关键数字 13 补 E3-M 重测口径）、MANUSCRIPT 重置表 Exp 18 行、AGENTS.md。**Next: Fig 4e–h + Figs 5–6 战役 + E21/E22 baselines 按第三次重置继续。**

## 2026-08-31 — Exp 17: E3 门控双臂主实验重跑（Fig 4a/4b）

- **门控臂 45/45 重跑完成**（`experiments/exp17_claim_gating.py`，预注册 docstring，pilot 8/8 PASS——0 FP、0 越权、14 条计划请求被拦截）：legacy E3 门控臂（登记 57.9% → 0%、TP 8 → 9、越权 23 → 0）在 45 任务 plan-A 尺度重测，与 Exp 5 未门控对照臂（同任务集/提示词/实测 oracle 链）逐任务配对。工具 = 生产门控栈原样（`RNADA_CAPGATE=enforce` + 打包默认 SelfModel；计划请求按声明用途在 oracle 注册任务键 `rna_aptamer_design` 上过 DecisionGate；放行请求经同一 `oracle_use` 上下文走 ToolExecutor 实测——工具层门即实际执行者，dedup cache 播种自 Exp 5；amendment-v1.1 两腿保留：ClaimGate 统一基底规则 + 精确重算弃权）；跨臂洗牌盲裁定 + 密封映射。**FP 0/31 = 0%（CI 0–16.1）vs 未门控 54.5%、越权 59 → 0（71 条计划请求被拦截）——硬保证在 2.25 倍任务尺度成立；TP 保留 80.0%（25 → 20），低于预注册 90% 门，如实报告**：2 条真 metric 声明被基底规则过度压制（LLM 把确定性指标自身声明为依赖 → unprofiled → reject）、2 条 59≠60 nt 长度马虎序列被重算腿正确弃权（反事实为 FP）、未门控臂 2 条侥幸 untrusted TP 按设计不可保留（无已验证 ranking/screening 权力的 oracle，不可验证比较声明正是门所禁止者）、+1 条救回（u_reduce_3）；ClaimGate 流向 31 → 24 发布（20 TP + 4 borderline）/ 7 压制（反事实 4 FP + 3 TP）。
- **Fig 4a/4b 绘制**（`experiments/plots/fig4a_claim_gating_headline.py` → `fig4a_claim_gating.{pdf,png}` 分组条形：FP 率 + Wilson CI / TP 数，未门控 terracotta vs 门控 sage；`fig4b_claim_matrix.py` → `fig4b_claim_matrix.{pdf,png}` 45 行任务 × 两臂逐声明对错色块矩阵（sage=保留 / terracotta=假声明，Biomni Fig. 2C–E 惯例）+ 臂×裁定 mosaic inset；palette rev 7、6-pt 纯黑、绝对 mm、1200-dpi PNG；QA 中修复 fig4b 毫米/英寸双重换算 bug 与 fig4a 0% 标签贴轴问题）。文档同步：FIGURE_PLAN_V5 行 a/b（行 c 数据注记 59→0，面板待绘）、PAPER_DRAFT（摘要 + 贡献 3 + §2.4 段重写 + Fig 4 图注 a–c + Methods + LLM 用量 90 calls + 数据可用性）、PAPER_FACT_SHEET（Exp 17 节 + claim check + 关键数字 13 改为重测口径 + legacy E3 节加 superseded 注记）、MANUSCRIPT 重置表 Exp 17 行。- **图 4c 补绘**（同日，同一份冻结结果、零重跑）：`experiments/plots/fig4c_overreach_events.py` → `fig4c_overreach_events.{pdf,png}`（越权事件 oracle × use 配对条形：未门控 59 = RhoFold 9+11 / ProteinX 11+8 / EGARPS 11+9 → 门控全 0；臂色沿 fig4a 惯例 terracotta/sage，oracle 组标签沿 fig3e 惯例，59→0 括号注记为注册的 Δ 标注；零值标签按 6-pt 纯黑惯例）。FIGURE_PLAN_V5 行 c 改为已绘，PAPER_DRAFT 图注 (c) 补 71 条拦截机制句，MANUSCRIPT 行补脚本名。**Next: Figs 4–6 其余战役 + E21/E22 baselines 按第三次重置继续。**

## 2026-08-31 — PAPER_DRAFT §2.3 按 Fig 3 成品合图与最新重测数字重写

- **`docs/PAPER_DRAFT.md` §2.3 全节重写**（用户指示；依据成品 `experiments/plots/output/fig3_composite.png` 逐面板核对，全部数字与 `experiments/results/exp{10,11}_v3 / exp12–16`（含 `exp15_rnasmol_v020_sandbox`）及 `exp5_claim_overreach` 的冻结 summaries 逐一相符）：面板引用重排为严格阅读顺序 **a→h**（旧文为 a–d, g, f, e, h，不合惯例）；节结构 = 引言（三失败模式框定）→ **Uncalibrated tool trust**（a–d；拆为「锚集+门槛+screening+ranking」与「docking+affinity 标定」两段）→ **Claim overreach**（e）→ **MRL 认证**（f，profiling 双面性）→ **RNAsmol 部署保真**（g，v0.2.0 沙盒考古 + 「邻接改写=损害载体」测量闭环 + 己方预测被证伪的披露）→ **Confounded improvement**（h；240 cells / 228 成功 / Ferritin 注册边界 / 56 paired cells / 19 有效靶标，δ +0.14→+0.05→−0.01，自审计 0/2）。
- **相对旧文的实质修正**：`Protenix ipTM` → `ProteinX ipTM`（与图面板标注及数据键 `proteinx_ipTM` 一致；§2.1 概览段的 Protenix 指 vendored 仓库名，保留）；ranking 段旧表述「每个通过细胞的 CI 均跨零」更正为精确版——三个 IFN-γ 细胞 CI 跨零（−0.23/−0.50/−0.60 起），而 Angiopoietin-2 细胞为 n = 3、ρ = 1.0 的退化点估计（CI [1.0, 1.0]，其三条目在随机复合物实现间 ~0↔~1 翻转）——结论「无可靠 ranking 细胞」不变。**同日修正落实**（用户指示，三处 + 同类引申处）：摘要「0 of 18 cells」→ v3 口径（0/27 可靠 screening/ranking 细胞 + docking 0/19 top-1）；「every passing CI spans zero / all CIs span zero」的四处活文档（PAPER_DRAFT Fig-3 图注 b 行、FACT_SHEET Exp-11 v3 节与关键数字 10 号、FIGURE_PLAN_V5 row b、DECISIONS Part-1 段）统一更正为「三个 IFN-γ CI 跨零；proteinx × Ang2 细胞为 n = 3 退化估计（ρ = 1.0、CI [1.0, 1.0]、条目在实现间翻转）」；FACT_SHEET Exp-10 v3 节 FGF2 括注更正为 AUROC 0.37/0.63/0.30（原括注 0.47/0.43/−0.18 混入 ranking-ρ 值）；FIGURE_PLAN_V5 row a 由 v2 六靶口径更新为 panel 实际渲染的 v3 九靶 run（2/27 名义通过、全 CI 跨随机，并补引 v3 summary）。CHANGELOG 历史条目按写作时保留，更正以本条及新版 §2.3 为准。
- 其余节逐行 diff 确认不变（§2.4 起全同）。自动化核查：必含数字 token 全部在文、无遗留旧值、面板引用序列 a→h。

## 2026-08-31 — Fig 3 composite 组装（a–h 八面板）

- **`experiments/plots/fig3_assemble.py` 新增 → `experiments/plots/output/fig3_composite.{pdf,png}`**：八个完成的 Fig 3 面板组合成一张大图。Nature 惯例经 `relevant_references/` 已发表 DeepRare 主图（Figs. 2–4，Nature 651，2026）复核：粗体小写字母置于各面板左上角（无句点、无括号）、严格阅读顺序 a→h、行顶对齐使同行字母共线、固定列网格。面板经 PyMuPDF `show_pdf_page` 以矢量 Form XObject 嵌入（无栅格化）；字母 Helvetica-Bold 8 pt 墨黑（palette TEXT）由组装器统一绘制；所有面板 scale 1.0（重置计划的统一 6-pt 文字样式，全图无 fit 缩放）。
- **布局**（同日晚些时候用户指示修订）：a（screening balloon 矩阵）全宽；**b、c 共行且两端齐平** —— b 为 27-cell 高瘦 Cleveland 点图（82.3×103.4 mm），c 以**双行 composite 变体**嵌入（`FIG3C_LAYOUT=composite python experiments/plots/fig3c_docking_lollipop.py` → `fig3c_docking_lollipop_composite.{pdf,png}`：19 个 lollipop 在 SARS-CoV-2 RBD｜PSMA 组分界处折为 11+8 两行，画布 97.2×103.8 mm 与 b 同高；单行独立面板 c 不变）；**d、e 等高配对** —— 首版 d|e 行在 e 下方留出高差空白带（d 高 e 56 pt），用户指示后 d 就地缩小重渲染（3.84×2.46 → 3.70×2.00 in → 86.7×44.1 mm）、e 就地放大重渲染（89×34 → 94×44.6 mm，轴区 71×21 → 75×31 mm → 85.5×41.4 mm），两者 6-pt 字体与内部版式不变、数据不变；**f、g、h 三联等高一排收尾**（fig2 fgh 行惯例：统一绘制高度 90.2 pt，各面板缩放 ≈ 0.69/0.64/0.81，宽度随各自纵横比、剩余宽度均分为 gutters；用户指示 —— h 无需全宽，首版的全宽收尾变体 `fig3h_dissolution_composite.*` 随之退役删除，fig3h 脚本回退单一版式）。
- **分辨率**：成品 PDF 一页 539.9×721.7 pt（190.5×254.6 mm），PNG 从矢量成品以 **1200 dpi** 渲染（8999×12029 px，Nature Methods line-art 指引）。组装 QA 发现 fig3a 的 colorbar 渐变在面板 PDF 内以 100 dpi 栅格嵌入（成品中唯一的栅格元素）—— fig3a 的 savefig dpi 已统一为 1200 并重渲染（仍读 v3 summary，"cells passing AUROC > 0.8: 2/27" 不变；顺带将其独立 PNG 提到 1200 dpi，与 fig3b–h 的 1200-dpi 惯例一致），现成品 PDF 中该 colorbar 为 1200 dpi。逐条带视觉 QA（各行字母线、b|c 接缝、d|e 等高、fgh 三联行、h 的 inset/门槛标注、右缘齐平）通过。
- FIGURE_PLAN_V5（Fig-3 表后注记）、AGENTS.md、本日志更新。

## 2026-08-31 — Figs 3–5 撤销 a 子图总结图（用户决定）；fig3 图脚本与输出改名 fig3a–h

- **结果图不再以总结/机制示意图开头**：Fig 3a 失败模式示意图（当日早些时候绘制，见下条）连同文件删除；规划中的 Fig 4a（CapGate 机制示意）与 Fig 5a（GenNav 机制示意）在战役重跑前移除；Figs 3–5 原 b–i 面板重编为 a–h，图例与正文引用同步（机制引用改指 Fig. 1d / Fig. 1e — 机制示意保留在 Fig 1；§2.3 开头引用改指整图）。
- **文件改名**：`experiments/plots/fig3{b..i}_*.py` → `fig3{a..h}_*.py`（output/ 下 pdf/png 同步）；脚本内 Usage/Output 路径与面板惯例互引重编（fig3b/3c/3g 惯例 → fig3a/3b/3f 等；外部文献引用如 CASCADE Fig. 3b 未动）；8 个脚本 py_compile 通过。`fig3a_failure_modes.{py,pdf,png}` 删除。Fig 2a 毯图与 Fig 6a 能力地图为数据面板，未动。
- **文档同步**：FIGURE_PLAN_V5（三图删 a 行、行重编、9→8 panels、类型清单字母、新增 2026-08-31 注记）、PAPER_DRAFT（Results 引用 + 三个图例 + 头部注记）、PAPER_FACT_SHEET / MANUSCRIPT（v5 面板字母 + 图脚本路径 + legacy→v5 映射注记）、AGENTS.md。历史登记条目（本日志旧条目、预注册 driver docstring、冻结结果 summary）按写作时字母/路径保留。

## 2026-08-31 — Fig 3a 绘制（失败模式示意图，Fig 3 九面板收尾；**当日撤销 — 见上条**）

- **`experiments/plots/fig3a_failure_modes.py` → `fig3a_failure_modes.{pdf,png}`**（b–i 八个子图既成后按规划绘制行 a 示意图；Nature 风格 surveyed 自 `relevant_references/` Robin Fig. 1 / Co-Scientist Fig. 1：圆角浅彩盒 + 细墨线边框、左→右数据流、克制用色、充分留白）：
  顶部主轴 = 未门控生产路径 [Design goal] → [Ungated agent: plans · calls tools · narrates results] ⇄（calls / scores 双箭头）[Tool layer: oracles & scorers] → [Report: candidates + claims]，下弯回环箭头标注 "iterative rounds — pool grows"（多轮协同环）；流程上三个编号入口（① 工具/分数端口、② 报告端口、③ 回环），下方三条编号 lane 一一对应：
  1 **Uncalibrated tool trust**（b–e）—— 实测 (score, affinity) 点为噪声云（sage 点）vs agent 假设的单调关系（terracotta 虚线），"optimizes an oracle score with no measured power — climbing noise"；
  2 **Claim overreach**（f）—— claim 条（terracotta）越过 evidence 条（sage）尽头的虚线证据边界，"narration outruns measurement"；
  3 **Confounded improvement**（i）—— 表观 δ +0.14 在预算匹配 +0.05 / 固定重采样 −0.01 下消解的三点斜率，点色复用 Fig-3i 阶段色（terracotta / grey blue / sage）。
  约定：实线 slate-blue = 数据流（paper_v5 示意图惯例）；terracotta = 未门控/apparent/claim，sage = 实测真值/证据，grey blue = 对照，mauve grey = lane 2 识别色，深暖灰 = 中性边框/边界；全部文字 6-pt 纯黑（fig3f 惯例）；无图内标题（标题在 Fig-3 图注）；全宽 184 × 51 mm、绝对 mm 几何、矢量 PDF（fonttype 42）+ 1200-dpi PNG。分区域视觉 QA 通过（calls/scores 标注、回环下凹 + ③ 端口徽章、三 lane 图元——无文字/图形重叠；回环 rad 符号经显示坐标验证修正）。FIGURE_PLAN_V5 行 a、AGENTS.md、本日志更新。

## 2026-08-31 — Exp 16（Fig 3i / §2.3 实验 8）混淆改进证伪全面板重跑

- **`experiments/exp16_confounded_improvement.py` 执行**（第三次重置计划，预注册 docstring，pilot 8/8；用户确认 RNA-BioBench-Aptamer 全 20 靶标 × 3 seeds × 4 臂 = 240 cells）：被移除的协同环（BMC，2026-08-18 删除，DECISIONS (m)）**作为研究对象在实验驱动内逐字重构**——legacy AptamerCoordinator 确定性规则从 git 1b45138~1 恢复（utopian 参考点诊断 / ASF 最优 + 各维度领先者诊断集 / EGARPS-IPTM 差距→热点扩展±5 再生 8 / RHOFOLD 差距→长度+10（pLDDT<60）或+5、种子+1 / 零违规→池 8 早停）；四臂 = serial8 / loop16 / serial16（同种子一次生成 16）/ fixed16（固定种子+1 重采样、无诊断内容）；平台本身零改动，全部走生产 RnaAptamerDesignWorkflow（逐 cell 新实例、CapGate advisory、全审计）；主指标 egarps_component best-of-pool（被注销的 oracle——测的就是它）；配对 Wilcoxon + 两样本 Cliff's δ（legacy 约定）+ 10⁴ 符号翻转置换零分布；预注册 gate δ≥0.3（P0/P3 约定）；E2 四步自审计确定性重跑（阈值 70%）。
- **结果：240/240 记录，228 成功 + 12 Ferritin 零输出边界失败（19 靶有效，legacy 口径）；环 56/57 走热点扩展分支，实现池 8/16/16/16。表观效应 δ = +0.1397（p = 0.0026，perm p = 0.0555，胜 41/56）——方向为正、名义显著，但已在门槛之下；预算匹配 δ = +0.0504（p = 0.212，胜 34/56）——消解；固定重采样 δ = −0.0120（p = 0.730，胜 31/57）——恰好为零。自审计存活 0/2（两条 legacy 旗舰声明均被注销）。** vs 注册 legacy 弧线（+0.457→0.278→0.222，0/2，内部登记保留）：证伪定性复现且全面板尺度下更锐利——表观效应在对照之前就不再过门槛。
- **部署拓扑（披露）**：6 个认领制并行 worker + 5 个服务副本（EGARPS×3、ProteinX×2，GPU 0–2，同代码同权重仅端口/设备不同；设备位置不影响分数——exp10 约定）；EGARPS 输入按 worker 隔离目录（result.txt 并发竞态防护）；导向失败自动回落默认端点；两次整机断电经监督重启 + 陈旧认领接管零 cell 损失。并行拓扑下 240 cells ≈ 36.5 h（单进程投影约 3×）。
- **图 `experiments/plots/fig3i_dissolution.py` → `fig3i_dissolution.{pdf,png}`**（斜率轨迹 + δ=0.3 门槛虚线 + 每段 δ/P 两行标注；置换零分布直方图 inset（10⁴ 符号翻转，观测 δ 陶土红标线，象限自适应避让数据；Robin Extended Data Fig. 4c 惯例）；阶段点陶土/灰蓝/鼠尾草绿，连线暖灰，门槛线深暖灰（fig3b/3c 惯例）；无图内标题、6-pt 纯黑统一、单栏 88 mm 几何、PNG 1200 dpi；视觉 QA 通过）。
- PAPER_DRAFT（§2.3 混淆改进段重写为重测数字 + Fig 3i 图注）、PAPER_FACT_SHEET（Exp 16 节 + claim check + 关键数字 9 号升级）、FIGURE_PLAN_V5 行 i、MANUSCRIPT 重置表（Exp 16 行）、本日志更新；workspace 隔离 scratch 清理。

## 2026-08-30 — Fig 3g 视觉修订（Nature 风格 + 布局修正，用户指示）

- **`experiments/plots/fig3g_mrl_certification.py` 纯视觉修订，数据与数字不变**（仍渲染 `exp14_mrl_oracle_certification` 的 summary：AUROC 0.9903/1.000/1.000、ρ 0.9256/0.9201/0.8353，706/706）：
  (1) 全部文字统一 6-pt 纯黑 #000000（fig3f 惯例 —— palette `TEXT` #1A1A1A 在 6-pt 抗锯齿下显灰；原 chance/zero 标注用的是 dark warm grey）；
  (2) chance 0.5 / zero 参考线及其标注移除 —— 认证判读只依赖预注册 gate 线（0.8 / 0.6，保留，虚线 + 纯黑标注）；chance 在共享 0–1 坐标轴上仍然可读，并写入 Fig 3g 图注（fig2g 第二轮修订惯例）；原 "zero" 标注悬于两面板之间、"chance" 与 "gate 0.8" 互相挤碰的问题随之消除；
  (3) 两个 x 轴第二行标签互相压叠修复：删去其中的 n 标注（分层 60+60 / 排序 n=120 移入图注），标签缩短为 "(high vs low MRL tier)" / "(predicted vs measured MRL)"；
  (4) 数值标签加白色衬底，不再与 gate 虚线穿插；
  (5) 行标签改为 Sample-2019 5′UTR 文库名（"Random 50-nt 5′UTRs (in-distribution)" 等）；
  (6) 布局改为绝对 mm 几何并重新配平（标签列 22 mm｜两个 29 mm 轴｜面板间距 6 mm，图高 58 → 52 mm）；
  (7) PNG 1200 dpi（Nature Methods line-art 指引）+ 矢量 PDF（fonttype 42）。PAPER_DRAFT Fig 3g 图注、FIGURE_PLAN_V5 row g、PAPER_FACT_SHEET E7 条目、AGENTS.md、本日志更新。

## 2026-08-30 — Fig 3f 视觉修订（Nature 风格 + 布局修正，用户指示）

- **`experiments/plots/fig3f_claim_overreach.py` 纯视觉修订，数据与数字不变**（仍渲染 `exp5_claim_overreach` 的 records/summary：56 claims = 23 确定性 + 33 适配体（30 FP / 25 TP / 1 borderline），59 越界事件按 oracle×用途 = 9/11、11/8、11/9）：
  (1) 图内标题与汇总统计全部移除 —— 原 "FP rate 30/55 = 54.5% (95% CI …)"、"deterministic/aptamer tasks: n claims, n FP"、"59 events on 21 tasks" 各行的数字 Fig 3f 图注原本已含；panel 字母组装时添加（fig2d–fig3g 惯例）；
  (2) 文字-文字重叠修复：原两个块标题互相压叠（"…0 FPaptamer tasks…"）；华夫块改挂短组标签 "deterministic tasks" / "aptamer tasks"，居中于各自块正下方、共用基线；
  (3) 图例归位：判定图例（false positive / true positive / borderline）改为华夫面板正下方居中单行，用途图例（ranking objective / screening evaluation）改为条形面板正下方居中单行 —— 各自紧贴所属面板（原先一在图左上角、一在整图底部）；
  (4) 条形面板 oracle 标签（RhoFold / ProteinX / EGARPS）从 ranking 行改为居中于一组两条之间；
  (5) 全部文字统一 6-pt 纯黑 #000000（用户指示；原 palette `TEXT` #1A1A1A 在 6-pt 抗锯齿下显灰）；图形颜色仍全部出自 palette rev 7 十二色；
  (6) 布局改为绝对 mm 几何（fig3g 惯例，89 mm 单栏宽，bbox_inches="tight"），消除原图的大片空白带；
  (7) PNG 1200 dpi（Nature Methods line-art 指引，与 fig3d/fig3e/fig3g 一致）+ 矢量 PDF（fonttype 42）。FIGURE_PLAN_V5 row f、AGENTS.md、本日志更新。
- **同日第二轮（用户指示）：华夫面板整个移除，Fig 3f 变为纯条形面板** —— 用户判定逐声明小方块信息量过低（类选择性一句话即可说清）；`draw_waffle`、判定图例（false/true positive、borderline）与华夫组标签随之移除，图高 63 → 34 mm；PAPER_DRAFT Fig 3f 图注改为 "horizontal bars: …; the per-claim adjudication is text-reported"，59 事件注明 "spread 8–11 per cell"；FIGURE_PLAN_V5 row f 图型 waffle + bar → bar。
- **同日第三轮（用户指出图例疑问）：用途图例色块 grey_blue → palette 预留中性深暖灰 #7A7672** —— 用户问"三种颜色为什么只有两个图例"：三色是 oracle 标识、已由 y 轴标签直接标注（无需颜色图例），图例只承担实心/浅色 alpha 通道；grey_blue 色块易被误读为第四种数据色，故改用预留中性色。图例锚点同时从整图居中（0.5）改为坐标轴居中（50.5/89）—— 原位置相对坐标轴偏左 6 mm。
- **同日第四轮（用户指示）：图例改为六色块样式键** —— 用户要求"分别用三个深颜色和三个浅颜色做标注"：上行三个实色块（RhoFold sage / ProteinX slate / EGARPS terracotta）标注 "ranking objective"，下行三个对应浅色块标注 "screening evaluation"，与六种条形样式一一对应；手绘色块（fig.patches + fig.text，fig.legend 无法实现行标注网格），整体对齐坐标轴中心；坐标轴上移 1 mm、图例行下移（首轮实现与 x 轴标题重叠，已修）。中性深暖灰方案被本轮取代。
- **同日第五轮（用户指示）：样式键两行并为一行** —— [实色 sage/slate/terracotta] "ranking objective"　[浅色 sage/slate/terracotta] "screening evaluation" 同一行，整体对齐坐标轴中心；行宽 ≈65.5 mm < 轴宽 71 mm。

## 2026-08-29 — Fig 3e 视觉修订（Nature 风格 + 布局修正，用户指示）

- **`experiments/plots/fig3e_affinity_calibration.py` 纯视觉修订，数据与数字不
  变**（仍渲染 `exp13_affinity_calibration` 的 records/summary：thrombin 系列
  ρ = +0.49 (n = 6)、pooled AUROC 0.52 (62 vs 28)、三类 ridgeline
  67/11/17）：
  (1) 图例从右侧面板下方移到整图底部居中单行 —— 原先锚在右图下且被图缘
  裁断（"Random sequences (n = 17)" 显示不全）；
  (2) 右侧三条 ridgeline 在面板内均匀展开 —— 原先挤在左半边（xlim 0–6.4
  而三条峰只占 0.15–3.3）；
  (3) 文字-图形重叠清理：thrombin ρ 标注移入数据上方留白带（原与顶部散点
  重叠）、pooled AUROC 汇总数字移出面板进 Fig 3e 图注（fig3d 惯例——汇总
  统计与判据入图注；原文字压在 random-negatives 峰上）、pegaptanib 标注
  移位避开散点与网格线；
  (4) 散点 x 轴范围扩至 1.2 × 10³ nM —— 原 xlim 止于 400，IFN-γ 家族三个
  Kd 结合物（439.5 / 481.6 / 913.9 nM）被裁掉，现 62 个 Kd binders 全部
  在图；
  (5) 全部文字统一 6-pt 墨黑（palette `TEXT`，含显式 `legend.labelcolor`），
  无图内标题（Nature 惯例 —— headline 进图注、panel 字母组装时添加）；
  (6) PNG 1200 dpi（Nature Methods line-art 指引，与 fig3d/fig3g 一致），
  PDF 保持矢量。
- 文档：PAPER_DRAFT Fig 3e 图注（thrombin 系列标明 ringed、pegaptanib
  annotated）、FIGURE_PLAN_V5 row e、AGENTS.md Exp 13 条目、本日志。
- **同日第二轮（用户指示）**：(1) 右图三条单侧 ridgeline 改为镜像密度小提琴
  —— 数据与 KDE（Scott 带宽）不变，仅改为对称填充；三根并排柱子用半小提琴
  观感不佳；(2) 图例行整体取消，组名直接标注在各自小提琴下方（直接标注优于
  脱离面板的图例盒；右图内部无空位放图例）；(3) pegaptanib 指引线缩短为
  水平短线（原斜长线易被误读为趋势线，且中途擦过一个散点）；(4) Fig 3e 图注
  补明散点为"九个靶标全部 62 个带 Kd 的 binders"。
- **同日第三轮（用户指示）**：小提琴 KDE 在概率物理边界 score = 1 处截断
  （1 以上的密度是带宽伪影），右图顶部由此空出留白带，pooled AUROC 统计量
  （0.52, CI 0.39–0.65, 62 vs 28）回到面板上、置于该留白带（取代第一轮的
  "仅入图注"处理——用户指出右图不能没有数字）。
- **同日第四轮（用户指示）**：pooled-AUROC 统计量再次撤下面板 —— 其
  62 vs 28 口径（保留 P2 登记的 Kd-binder 约定）与小提琴组标签 67/11/17
  并排读来自相矛盾；数值（含 CI 与组成）保留在图注与正文；右图改为直接
  标出纵坐标（y 刻度标签 + 主网格线穿过小提琴），分数轴在两个面板上都可
  直接读数。
- **同日第五轮（用户指示）**：左图 thrombin 标注从纯文字改为带墨黑圈点
  标记的图例项（圈点样式 = 数据中的环标点心智一一对应），读者第一眼即可
  明白为何这六个点带黑边框。
- **同日第六轮（用户指示）**：右图密度小提琴整体更换为逐点抖动散点列 +
  中位数刻线 —— n = 11–67 且横跨九个数量级，密度曲线会假装出数据中没有
  的结构；每个点直接可见，中位数直接标在纵轴刻度上，且与左图散点共享同一
  分数轴、图型呼应。组标签改两行/三行换行避免相互触碰。
- **同日第七轮（用户指示）**：类别分布伴随面板整体撤下 —— 图 3e 收敛为
  单面板 Kd–分数散点（62 Kd binders；thrombin 环标 + 图例项；pegaptanib
  标注）。类别分离证据（pooled AUROC 0.52 [CI 0.39–0.65, 62 vs 28] 与三类
  中位数 0.22 / 1.4e-3 / 2.2e-2）改为文字报告（图注 + 正文），筛选失败的
  系统性展示由 Fig 3b 承载。

## 2026-08-29 — Exp 15（图 3h，§2.3 实验 7）：RNAsmol 部署工件保真度 A/B —— 两臂皆过 + 预注册缺陷类判据被证伪（披露）

- **§2.3 实验 7 重跑**（用户确认数据集后启动；驱动 `experiments/exp15_rnasmol_fidelity.py`，预注册 docstring，下一个空闲重置序号；pilot 20/20）。数据 = RNAsmol 官方 held-out 测试集两份逐字（robin n=1,492 763/729；pdb n=170 87/83；全部 1,662 条源序列带小写修饰碱基编码；pdb 字母表含 T 与 x）；decoy 案例与 OOD 面板不在范围（图 2g 证据；全大写输入——两臂无对比）。两臂打同一部署服务（start.sh CPU 默认 8007，GPU 0–2 未占用）：臂 A = 生产工具路径 `ToolExecutor.run_tool("score_rna_ligand_binding_with_rnasmol")`（工具层 uppercase+T→U 归一化 = v0.2.0 缺陷类的现役等价物；advisory CapGate，全部入审计）；臂 B = case-preserving verbatim 直连端点（exp7 协议）。历史参考（仅上下文，从不 gate）：v0.2.0 修复前 0.7864/0.4103。
- **全量 3,324/3,324，0 失败：臂 A 0.9745 (0.9678–0.9804) / 0.9860 (0.9715–0.9963)；臂 B 0.9744 (0.9677–0.9803) / 0.9828 (0.9616–0.9968)** —— 预注册的缺陷类判据（臂 A 双 split 低于 0.8 门槛）**未成立**。交叉验证全过：臂 B 与 exp7 记录**逐对位级一致（1,662/1,662，max |Δp| = 0.0）**；臂 A 归一化回显验证 1,662/1,662 零错配（ggguuagggu → GGGUUAGGGU）；两臂 checkpoint 逐对一致。
- **证伪披露**：exp7 备案中"工具层归一化会静默复现 v0.2.0 缺陷类"的注册预测被本次现测证伪——case 塌缩在分布内 **AUROC 中性**：逐对分数扰动实质性存在（robin 中位 |Δp| 0.006 / max 0.415，1,046/1,492 对 >1e-3；pdb 中位 0.083 / max 0.910，44/170 对被拉入 [0.4,0.6] 不确定带，臂 B 为 0/170）但不破坏类别判别。v0.2.0 塌缩（0.7864/0.4103，注册历史；坏工件已不存在、不可重跑）归因于服务端预处理移植层（大写词表 + adjacency 处理），v0.3.0 已修复——非 case 信息单因素。**净结论：部署保真度在两条出厂集成路径上均经现测认证（含默认工具路径——1,662 对官方考卷交付已发表性能）；部署失真真实、静默且分层依赖，只有测量能回答它在哪一层。**
- 图 `experiments/plots/fig3h_rnasmol_fidelity.py` → `fig3h_rnasmol_fidelity.{pdf,png}`（哑铃 + 现测验证分叉：v0.2.0 空心 terracotta 标记（注册历史）分叉至两条现测臂——terracotta 工具路径 / sage verbatim 端点——CI 须线、chance/gate 参考线、图例为轴下居中行块（fig2i 惯例）；palette rev 7）。PAPER_DRAFT（§2.3 段落 + Fig 3h 图例）、PAPER_FACT_SHEET（Exp 15 节 + 证伪披露）、FIGURE_PLAN_V5 行 h、MANUSCRIPT 重置表 Exp 15 行更新。
- **同日 addendum——v0.2.0 工件考古复核（用户指示；驱动 `experiments/exp15_rnasmol_v020_sandbox.py`，预注册 docstring，主结果已知后注册——披露；pilot 10/10）**：从 git `7262e54` 逐字节恢复 v0.2.0 服务（main.py sha256 每次调用断言；同 commit 恢复 `common_utils.py`；沙箱镜像原 `microservices/` 布局、端口 8107（生产注册表之外）、CPU、`rnasmol_service_env`、`external_repos/RNAsmol` symlink 指向未动 checkpoint；生产 8007 全程未触碰），同一批 1,662 对官方考卷重测：**robin 0.7897 (0.7663–0.8117)、pdb 0.4197 (0.3335–0.5070) —— 1,662/1,662 零失败，注册事故值 0.7864/0.4103 复现于 |Δ| 0.0033/0.0094**，checkpoint 与 exp15 逐对一致，注册预期全过。**缺陷分解就此闭合为实测**：v0.2.0（大写 + 重写邻接）0.790/0.420 vs exp15 臂 A（大写 + 上游保真邻接）0.975/0.986——同样的大写处理、只差邻接 ⇒ 真凶是 v0.2.0 对上游邻接索引怪癖（checkpoint 训练所依赖）的"修复"，而非 case 塌缩；"看似致命的改动无害，看似改进的改动致命"。注册历史 pre-fix 数值就此升级为实测。图 3h 改从实测取数重渲染（视觉复核通过）；沙箱服务已停。PAPER_DRAFT/FACT_SHEET/FIGURE_PLAN_V5/MANUSCRIPT（addendum 行）/本条更新。

## 2026-08-29 — Exp 14（图 3g，论文登记 E7）：MRL 表达 oracle 认证重跑 —— 三族双门槛全过，逐条复现

- **E7 = §2.3 实验 6（oracle 认证·正面）重跑**（用户确认三族原设计，含 in-distribution 正控族）：驱动 `experiments/exp14_mrl_oracle_certification.py`（预注册 docstring；下一个空闲重置序号，不与图 2g 的 `exp7_rnasmol_boundary.py` 冲突）。锚定集 `data/benchmarks/external_anchors/utr_mrl/e7_mrl_anchor_set.json` 逐字节未动（706 条 / 3 族：random-50 训练分布内（正控，用户复议后保留）+ 变长随机 + 变长人内源；每族 hi60/lo60 筛选层 + 120 条秩分层排序子集；组成断言全部通过）。仪器 = 生产工具路径 `ToolExecutor.run_tool("predict_5utr_mrl_with_gemorna")` → 部署 GEMORNA 8004（GPU 0/1/2 布局继承不动；锚序列逐字节写入 scratch 文件，工具层 uppercase+T→U 规范化为唯一变换——锚集"DNA 按 RNA 计"约定，服务回显 input_sequence 逐条记录）；RNADA_CAPGATE=advisory，全程审计；零 LLM；pilot 6/6（与保留记录逐位一致）。
- **全量 706/706，0 失败（≈ 37 min）：三族双门槛全过，且与保留证据完全复现** —— AUROC **0.9903 (CI 0.9754–1.0) / 1.0000 / 1.0000**（门槛 > 0.8，CI 均清 chance），ρ **0.9256 / 0.9201 / 0.8353**（门槛 ≥ 0.6；新增描述性 bootstrap CI 0.884–0.949 / 0.874–0.947 / 0.748–0.897，全部高于门槛）；与保留 `e7_mrl_scoring.jsonl` 1:1 对照 **706/706 精确一致，max |Δ MRL| = 0.0** —— oracle 经部署链端到端完全确定。披露：保留 S0 sanity 注（6.34 vs 2.48）的聚合口径不可考（旧驱动已删）；本次池化层均值 6.364 vs 2.818（逐条分数逐位相同，仅上下文引用）。
- 图 `experiments/plots/fig3g_mrl_certification.py` → `fig3g_mrl_certification.{pdf,png}`（点图+CI 对门槛：左 AUROC（chance 0.5 实线 + 0.8 门槛虚线）、右 ρ（零线 + 0.6 门槛虚线），三族行共享，值+CI 印于点上方；GEMORNA MRL oracle 色 = palette 灰蓝 #8FA6BB（区别于 3b–f 结构 oracle 三色）；6-pt 墨黑、无图内标题（fig2/3 系惯例）；palette rev 7）。保留 `e7_*` SelfModel 证据链未动（never-delete 规则；打包默认 SelfModel 无需变更——本次全部证实其 graded verdict）。
- 文档：PAPER_DRAFT（§2.3 正文 + Fig 3g 图注 + Methods 基准段 + 数据可用性）、PAPER_FACT_SHEET（E7 节 + claim check）、FIGURE_PLAN_V5 row g、MANUSCRIPT E7 行、本日志、AGENTS.md 更新。**下一步：按用户顺序重跑新程序后续实验。**

## 2026-08-29 — 实验程序重置（第三次）+ Exp 5（图 3f，E3 控臂 45 任务重测）+ 误删恢复

- **程序重置（用户指示）**：整体架构变动较大，所有实验按用户顺序逐个重跑、逐个换新代码——**只有当前正在重跑的实验可以替换它自己的旧代码/结果/图；尚未重跑实验的一切文件保持原样**。（当日曾误将 exp1–exp13 的旧代码/图/结果整体删除，用户指出后**已从 git 290141b 全量恢复**（175 个已跟踪文件 100% 找回）；不可恢复的仅两类未跟踪文件：旧运行日志 `results/*.log`（`.gitignore` 第 60 行 `*.log`）与 exp10–13 结果目录下的 `scratch/` 中间产物——均非判据证据，后者可由保留驱动确定性重算。）
- **Exp 5 = E3 控臂（声明越界）在 45 任务规模重测（图 3f，华夫+条形）**：任务集 `experiments/e5_audit_tasks.json`（生成器 `exp5_build_audit_tasks.py`，确定性 + 断言优先；24 确定性（3 族 × 8）+ 21 适配体（12 排序 + 9 筛选，9 靶标全覆盖）；strata = legacy_v1 20 条逐字节（自 git e601913 恢复，候选/Kd 与 v3 逐条断言一致）+ extension_v2 25 条（方案 A 预注册规则：每靶标排序/筛选全覆盖、≥8-Kd 靶标拆第二排序任务（结合物不相交））。驱动 `experiments/exp5_claim_overreach.py`（预注册 docstring；仅 ungated 臂；每任务 2 次 LLM 调用 deepseek-v4-pro temp 0，提示词与旧 E3 逐字节一致；**oracle 分数改走 live 生产路径**（ToolExecutor → rhofold 8005 / proteinx 8022 / egarps 8023，按 (候选, oracle) 去重缓存：213 分数 / 71 候选，0 服务错误）——唯一预注册协议偏离，已披露；RNADA_CAPGATE=advisory，全程审计）。Pilot 8/8（不可信类 5 FP + 11 越界 → 判别门 PASS）。**全量 45/45 零失败（≈4.5 h）：FP 30/55 = 54.5%（Wilson CI 41.5–67.0），越界事件 59（全落不可信类，3 oracle × 2 用途 8–11/格）；类选择性极强——确定性类 23 TP / 0 FP，不可信类 30 FP / 2 TP = 93.8%（排序 16/17、筛选 9/10）；两 stratum 同率（55.6% / 53.6%）；legacy-20 子集 15/28 = 55.6% + 28 事件 ≈ 登记值 57.9% + 23（实现方差内）**。图 `experiments/plots/fig3f_claim_overreach.py` → `fig3f_claim_overreach.{pdf,png}`（华夫：逐声明瓦片，FP 陶土/TP 鼠尾草绿/borderline 暖灰，确定性/适配体两块；条形：越界事件按 oracle×用途，oracle 配色同 3b–3e，实心=排序目标/浅色=筛选评估；用途图例图底居中（fig2i 惯例）；palette rev 7）。PAPER_DRAFT（摘要/引言/§2.3/§2.4/Fig 3f 与 Fig 4b,d 图注/Methods 基准段/数据可用性）、PAPER_FACT_SHEET（Exp 5 节 + 关键数字 14）、FIGURE_PLAN_V5 row f、MANUSCRIPT E3 行、MODEL_API_USAGE、本日志更新。**下一步：按用户顺序重跑新程序的后续实验（同模式，只替换当前实验自己的产物）。**

## 2026-08-29 — Fig 3b 视觉修订（Nature 风格，用户指示）

- **`experiments/plots/fig3b_oracle_screening.py` 纯视觉修订，数据与数字不
  变**（仍渲染 v3 summary，9 靶标 27 格，2/27 nominal pass）：(1) 删除图内
  标题 — Nature 惯例 headline 进图注、panel 字母在组装时添加，与
  fig2d/fig2f/fig2h/fig2i 的既有修订一致；(2) 全部文字统一为 6-pt 墨黑
  （palette `TEXT`）— 删除深色气泡上的白字分支与白色描边光晕（该光晕是
  2026-08-28 为两个最小气泡格加的，却恰好让那两个 AUROC=0.17 的格子白字
  叠白底糊成一团；墨黑无描边在本调色板的中间明度色阶上各种气泡尺寸均可
  读）；(3) 色条标注缩减为 "AUROC (binder vs negative)"（chance 实线 /
  gate 虚线的含义本就在图注中）；(4) 图宽上限 7.4 in → 183 mm（Nature
  双栏上限），PNG 600 dpi 不变。
- 文档：PAPER_DRAFT Fig 3b 图注补 "+/−" 锚点计数记号定义（binders + /
  negatives − 列于列标签下）。
- **同日追加（用户指示）**：删除两个过门格（0.83×2）的深色圆环标记 —
  过门信息已由格内数值承载，全部气泡渲染统一；色条上的 0.8 gate 虚线
  一并去除（仅保留 0.5 chance 实线），PAPER_DRAFT 图注与
  FIGURE_PLAN_V5 row b 的参考线描述同步更新；坐标轴范围收紧至与最外圈
  网格线重合，消除边框与网格线之间的白缝。

## 2026-08-29 — QualityAgent 提示词/profile 全面审计：3 处方向性错误修正 + 过时默认值同步

- **审计范围**: 全部 4 个 LLM 调用点（QualityAgent 默认诊断提示词、
  secondary-structure `build_prompt` 覆盖、SynthesisAgent 综合报告、ClaimGate
  抽取/润白）+ 8 个进入提示词的 QualityProfile 的 evaluation_dimensions 与
  adjustable_params hints，逐条对照当前工作流实现、工具语义与重置后实验结论。
- **方向性错误修正（3 处）**: (1) `blast_perc_identity` hint 写反 — BLAST
  perc_identity 是最低相似度过滤，higher = stricter（fewer matches），
  原文 "Lower = stricter" 反了；(2) RNASTOP `overall_stability`（mrna_cds +
  full_length 两处）写反 — 该值是 mean(reactivity, deg_Mg_pH10, deg_Mg_50C)
  反应性/降解均值，**lower = more stable**，原文 "closer to 1.0 = higher
  stability" 方向反且无归一化依据；(3) sgrna 的 CRISOT 语义混淆 —
  CRISOT-Score 是 sgRNA–DNA 对切割活性评分（工作流配 on-target 对，higher =
  预测 on-target 活性强），基因组级脱靶特异性是独立的 CRISOT-Spec 分量。
- **过时内容同步（2026-08-20 评分权重审计之后未跟进）**: tertiary profile 的
  "carefully tuned defaults" 句与其 hints 声称 rhodesign_temperature=1e-5 /
  权重 0.5/0.5 — 实际 workflow 默认 0.1 / 0.30/0.50/0.50（三组分），补
  `weight_tm_score`；sgrna profile 补 `weight_crisot_specificity`（默认 0.3）；
  ires 的 `run_structural_validation` hint 由 "ViennaRNA structural
  validation" 更正为 LinearFold 主 / ViennaRNA 备的当前实现；siRNA GC 评审
  维度由 "30-60%" 对齐工作流自身门限 [mingc=0.25, maxgc=0.60]。
- **阈值证据化**: mrna_cds 的 CAI 评审维度由 "human >0.8 good / <0.4 poor"
  的悬空启发式改为 Exp-2/3 零模型证据（人类随机同义重抽 ≈0.67、优化设计
  ≈0.83），并强调物种相关；MFE 维度补长度归一化提示（MFE 随长度缩放，
  跨长度比较用 MFE/nt — 与 Exp-2 的分析约定一致）；CRGPT nn_score 删除
  "close to 1.0 excellent / >3.0 poor" 无依据阈值并标注为未剖析
  （governance=pending）的模型似然代理 — 与 standing fact "CRISOT+CRGPT
  data gap" 一致。
- **核对通过、未改动**: QualityAgent 默认 11 条规则（无阈值、与参数白名单
  机制一致）；secondary-structure 覆盖段的默认值（repeats=10/
  num_invocations=3/mode m/37 °C，与 workflow 一致）与分数语义
  （total_score = distance/length、smaller better，与 score() 实现一致；
  0.3 触发线与 Exp-4 证据不矛盾，保留）；aptamer profile 全部参数/边界/
  reference_point 键与工作流逐项一致，其 "Do NOT apply hard thresholds for
  EGARPS/pLDDT/ipTM" 与 E10–E13 重置结论一致保留；ires 的反通用阈值条款与
  Exp-5 一致保留；ClaimGate 抽取提示词的 oracle 示例（gemorna_5utr_mrl /
  egarps_native_probability / rnasmol）与 capability 枚举与 SelfModel/
  CapabilityKind 完全一致；CDS "GC/unpaired 不进排序分" 与
  score_mrna_candidate（−MFE + codon_count·log CAI）一致。
- **验证**: 6 profile 导入 + 默认提示词构建冒烟通过；测试套件
  **646 passed, 1 skipped**（= 基线）。

## 2026-08-28 — Exp 13 (Fig 3e): affinity calibration at anchor-set scale — chance-level, inversion does not survive scale

- **Driver** `experiments/exp13_affinity_calibration.py` (pre-registered
  docstring; pilot 6/6 → full 95/95, 0 failures, wall ≈ 4.4 h): the retained
  P2 pilot's question re-registered on `e1_anchor_set_v3.json` verbatim (95
  entries / 9 targets — the Fig-3b/c/d data source, user-confirmed); zero
  intervention (ToolExecutor.run_tool → deployed rhofold 8005 / proteinx
  8022 / egarps 8023, fixed protocol args only); CapGate advisory; every
  call audited; the retained P2 15-record reference recovered from git
  e601913 and embedded (12/15 ids live in v3, drops disclosed).
- **Results**: thrombin 6-point Kd series ρ = 0.4857 (sub-gate; retained
  4-point 0.40 re-measures 0.20 — realization variance); pooled
  binder-vs-negative AUROC **0.5225 (CI 0.391–0.652, 62 vs 28)** — gate
  fails, CI covers chance; **the retained pilot's below-chance 0.356 does
  not survive scale — the honest reading upgrades "directionally inverted"
  to "uncalibrated, chance-level"** (per-entry inversion reproduces:
  pegaptanib 1.27e-6 vs scrambled TBA 0.983); all three ridgeline classes
  span the full 9-order score range; legacy-12 1:1 median |Δnp| = 7e-4
  (3 large shifts = the disclosed EGARPS bimodal class); vs exp10_v3:
  RhoFold bit-identical, EGARPS median Δ 5.7e-4. Verdict: **NO-GO on both
  P2 gates — no validated affinity calibration**.
- **Figure** `experiments/plots/fig3e_affinity_calibration.py` →
  `output/fig3e_affinity_calibration.{pdf,png}` (Kd–score scatter with the
  thrombin series emphasized + horizontal ridgeline densities on the shared
  log-score axis, ridgeline style after SeFMol Fig. 3d; palette rev 7; the
  group legend as a centred row block under the axis, the fig2i
  convention).
- **Docs**: PAPER_DRAFT Fig-3e legend + Results sentence (anti-signal →
  noise, inversion → chance-level at scale with the per-entry inversion
  preserved), PAPER_FACT_SHEET (E13 section + key-number 11), FIGURE_PLAN_V5
  row e, MANUSCRIPT reset table (Exp 13 row).

## 2026-08-28 — Fig 2 panel-letter swap: audit trail ↔ runtime (h ↔ i; user-directed)

The audit-trail panel is now **Fig 2h** and the end-to-end runtime ECDF
is now **Fig 2i** (lettering-only change — no data, statistics or panel
content touched), which also restores strict a → i reading order in the
composite (the f–g–h equal-height row now precedes the full-width i).
Files renamed: `experiments/plots/fig2h_audit_trail.py` (was
`fig2i_audit_trail.py`), `experiments/plots/fig2i_runtime_ecdf.py` (was
`fig2h_runtime_ecdf.py`), plus the four
`experiments/plots/output/fig2{h,i}_*.{pdf,png}` outputs; script
docstrings, usage lines and save stems updated. References swapped
across `PAPER_DRAFT.md` (Results citations + the Fig. 2 legend, whose
(h)/(i) paragraphs also traded places so the legend still runs a → i;
the Results' end-to-end sentence likewise traded its audit and runtime
clauses so the citations run Fig. 2h → Fig. 2i — "the 241-run campaign
above" became "below"),
`FIGURE_PLAN_V5.md` (Fig-2 table rows h/i contents + the
diversification-paragraph chart-type references), `PAPER_FACT_SHEET.md`
(the Exp-9/audit and Exp-8/runtime sections retitled and reordered;
**legacy** no-space records `Fig2i_ires` / `Fig2h_small_molecule` /
`fig2h 17 pairs` / `fig2_summary.json fig2i` deliberately untouched —
they name pre-reset artifacts, not the current panels), `MANUSCRIPT.md`
(reset table), this log's historical entries (re-lettered to the new
convention), `AGENTS.md` (Exp-8/Exp-9 What's-New bullets),
`experiments/exp8_runtime.py` / `exp9_audit_stats.py` docstrings, and
the frozen `exp9_audit_stats/MANIFEST.json` `experiment` field
(metadata only — the SHA-256 corpus hash entries are untouched).
`fig2_composite.{pdf,png}` regenerated.

## 2026-08-28 — Fig 2 composite assembly (a–i)

`experiments/plots/fig2_assemble.py` added →
`experiments/plots/output/fig2_composite.{pdf,png}`: the nine finished
Fig. 2 panels combined into one figure on the Nature conventions surveyed
in `relevant_references/` (bold lowercase letters at each panel's
top-left corner, strict column grid, rows top-aligned so the letters
share one line). Panels are embedded as vectors; every panel already
carries the reset programme's single 6-pt ink-black text style, so all
panels share one scale unless a row must shrink to fit. Layout
(user-directed): a (tile carpet) full width; b c and d e two per row at
scale 1.0, centred in their columns; **f g h share one row drawn at one
equal height** (f's squarer aspect made it look bigger than g/h under a
uniform row scale; per-panel scales differ, ≈ 0.59/0.67/0.71, widths
follow their aspects and the leftover width becomes even gutters),
sized so the row fills edge to edge and the first revision's empty
bottom-right half-cell disappears; i (ECDF) closes the figure full
width. After the same-day h ↔ i letter swap (entry above) the composite
reads in strict lettering order a → i. Letters Helvetica-Bold 8 pt ink
black, drawn by the assembler at one size regardless of row scale. PNG
rendered from the composite PDF at 300 dpi.

## 2026-08-28 — Fig 2h figure revision (user-directed; no data change)

`experiments/plots/fig2h_audit_trail.py` revised and regenerated
(`fig2h_audit_trail.{pdf,png}`; the Exp-9 corpus, session selection and
numbers are unchanged): the composition donut dropped — it carried three
numbers the paper already states in the Results text and the Fig. 2h caption;
the in-figure panel titles removed (Nature style — the headline lives in the
caption and panels carry letters only, the fig2d/fig2f/fig2i convention);
every text element now shares one font size (6 pt) and one colour (ink black
— the old layout's 4.8–5.6 pt labels antialiased to a pale grey); the legend
moved from floating half-outside the axes into the empty upper-right of the
milestone track; geometry changed from the double-column two-panel layout to
the single-column panel size of fig2b–g. `PAPER_DRAFT.md` Fig 2h legend,
`FIGURE_PLAN_V5.md` row i and `PAPER_FACT_SHEET.md` Fig-2h figure line
updated to match.

## 2026-08-28 — Fig 2i figure revision (user-directed; no data change)

`experiments/plots/fig2i_runtime_ecdf.py` revised and regenerated
(`fig2i_runtime_ecdf.{pdf,png}`; the Exp-8 numbers are unchanged): the
in-figure title removed (Nature style — the headline lives in the caption and
panels carry letters only, the fig2d/fig2f convention); every text element
now shares one font size (6 pt) and one colour (ink black — the legend
entries were previously set in their pale workflow colours); the box inset —
which overlapped the ECDF curves — dropped entirely (it summarized the same
samples the ECDF already shows in full, and the legend carries the medians);
the legend moved from floating at the figure's right margin to a centred row
block under the x-axis, so it reads as part of the panel; axis wording
corrected target → run (the 241-run sample times whole PA sessions as single
runs); y-range headroom added above the y = 1 step so the curve tops no
longer touch the panel edge. `PAPER_DRAFT.md` Fig 2i legend and
`FIGURE_PLAN_V5.md` row h chart-type phrase updated to match.

## 2026-08-28 — anchor set v3 Part-A extension + Exps 10–11 v3 re-runs: 9 targets / 95 entries, 2/27 and 4/27 nominal passes, none reliable

User-sequenced second curation pass (after the Fig. 3d run). Survey
(2026-08-27) vs curation outcomes — the assertion gate arbitrated:
**admitted** FGF2 (10 binders, Jellinek 1993; sequences/Kd via the
Ribocentre transcription + family-motif nesting assertions — primary PDF
bot-walled, deviation registered), swine influenza H3N2 HA (4 binders +
printed negative HA1c, Wongphatcharachai 2013; protein surrogate
A/swine/Illinois/03040/2010 full-length HA0 — selection strain
GISAID-restricted, 95.1% identity to the MN/2008 partial, registered), and
IFN-γ (B1-4 + 5 in-silico mutants, Zhao 2022; every mutant DERIVED from
B1-4 by its registered point-mutation list and asserted equal to the SI
print; M5-5 cross-checked between SI Tables S1 and S5; printed
docking-negative mutant admitted as negative). **Rejected at curation**
(two survey verdicts overturned): SARS-CoV-2 RBD (Shekar 2025 — 83-sequence
SI zip without any printed ID mapping) and HIV-1 RT FANA (Ferreira-Bravo
2015 — sequences figure-only; a vision extraction contradicted the paper's
own text-printed primer flanks). Part-A 66 → 95 entries (v2 byte-verbatim),
9 targets; docking anchors byte-identical to the first-pass v3 (asserted —
the Fig. 3d measurement unaffected); generator deterministic (md5
`7b7a71b915a2c3a181673ea3d27bdd27`); SOURCES.md second-pass section added.

- **Exp 10 v3** (`EXP_ANCHOR_SET` override, results `*_v3/`; defaults and
  v2-run records untouched): **95/95, 0 failures** (pilot 6/6; first
  attempt crashed on a generator fasta-path convention bug at the first
  new-target entry — 66 v2 records unaffected, fixed, `--resume` continued).
  **27/27 cells: 2 nominal passes > 0.8** (proteinx × swH3-HA 0.833 CI
  0.333–1.0; egarps × IFN-γ 0.833 CI 0.5–1.0) — both small-n, **all 27 CIs
  cover chance**; sensitivity 10/7/2/0; FGF2 (widest Kd span, 2.25 orders)
  sub-gate 0.47/0.43/−0.18.
- **Exp 11 v3**: **54/54, 0 failures** (pilot 4/4). **27/27 cells: 4 nominal
  ρ ≥ 0.6, all CIs span zero** — egarps/proteinx/rhofold × IFN-γ
  (+0.714/−0.226–1.0, +0.657/−0.5–1.0, +0.600/−0.6–1.0; n=6, single
  in-silico-mutant family, Kd span 0.94 orders — within-family covariation
  caveat registered) + proteinx × Ang2 (n=3). Sensitivity 8/6/4/2. Vs the
  first reset run: 10/18 v2 cells identical, rest ProteinX-realization
  variance (egarps × PDGF-BB 0.67 → 0.10 — the disclosed instability
  class). Headline invariant: no oracle–target cell shows reliable ranking
  power.
- Figures 3b/3c re-rendered on the v3 summaries (9-target data-driven
  columns/rows via `FIG3_SUMMARY`; v2 regression render verified; fig3b
  cell values gained a white halo after a vision check found two truncated
  at minimal bubble size). Docs updated: PAPER_DRAFT (Results, Fig 3 b/c
  legends, Discussion counts), PAPER_FACT_SHEET (Fig 3b/c sections + key
  numbers), FIGURE_PLAN_V5 rows b/c, MANUSCRIPT reset table.

## 2026-08-27 — Exp 12 (Fig 3d) executed under the reset + anchor set v3: docking-power profile on the extended panel, 397/399, 0/19 native top-1

Two-part delivery. (1) **Anchor set v3** (`data/benchmarks/external_anchors/aptamers/e1_anchor_set_v3.json`,
generator `experiments/curate_e1_anchor_set_v3.py`, user-approved scope
"admit every qualifying complex"): docking anchors 5 → **19 complexes / 14
independent protein targets**; Part-A 66 entries carried byte-verbatim
(asserted). Survey backbone = Troisi 2023 (144 protein–aptamer PDB entries)
+ a full-text RCSB sweep of all post-2024 "aptamer" deposits; every admitted
entry chain-composition/meth­od/resolution-verified against the RCSB API at
generation time (the assertion screen itself caught that 6RTI A9g is
2′-F-modified, missed by the survey scan). Chemistry screen rejected
SOMAmer-class and mirror-image complexes with RCSB-chemcomp-verified reasons
(4ZBN/8J1Q/7YQ3/9SA8/5UC6/4NI7/7JTN/6TXR; 4WB2/4WB3/4R8I) plus redundant
families and out-of-scope systems — 18 rejection classes registered.
(2) **Exp 12** (`experiments/exp12_docking_capability.py`, pre-registered
docstring, pilot 3/3; evidence `experiments/results/exp12_docking_capability/`):
per complex, native pose + 20 seeded rigid-body decoys; decoy parameters
offline-calibrated so the 1HVU decoy-RMSD distribution matches the retained
Part-B evidence, and the contact computation reproduces the retained 1HVU
native n_contacts = 152 exactly (protocol anchors). Instrument zero-intervention:
ToolExecutor.run_tool → deployed egarps 8023 (`academic=False` only); CapGate
advisory; every call audited.

- **399 poses attempted, 397 scored** — 2 reproducible service-side failures
  (8ZBF decoy16, 5HRU decoy13; one disclosed retry reproduced the failure;
  those complexes analysed with 20 candidates). Wall ≈ 4.6 h, median 38 s/pose.
- **0/19 complexes rank the native pose top-1** (gate ≥ 2/3 fails
  decisively); native ranks 6–20 of 21; native scores below the median decoy
  in most complexes (1HVU 0.008 vs 0.34); within-decoy Spearman(np, −RMSD)
  −0.59…+0.44.
- Vs retained: 0/5 headline invariant under the union 0/19; native-np deltas
  ≤ 0.0058 (service variance); per-complex ranks shift under the regenerated
  decoy protocol (disclosed).
- Figure `experiments/plots/fig3d_docking_lollipop.py` →
  `fig3d_docking_lollipop.{pdf,png}` (lollipop + top-1 gate line, grouped by
  protein target; terracotta EGARPS colour across Fig. 3; open markers = the
  five v2-retained anchors). Docs updated: PAPER_DRAFT (Fig 3d legend +
  Results + Discussion counts), PAPER_FACT_SHEET (E12 section + key numbers),
  FIGURE_PLAN_V5 row d, MANUSCRIPT reset table, SOURCES.md v3 section.
- **Next (user-sequenced)**: the five surveyed Part-A targets (FGF2 /
  influenza HA / HIV-1 RT FANA / SARS-CoV-2 RBD / IFN-γ) enter the same v3
  set in a second curation pass, then Exps 10–11 re-run on v3 for Figs 3b–c.

## 2026-08-27 — Exp 11 (Fig 3c) executed under the reset: structure-oracle ranking-power profile, 34/34, no reliable ranking power

Zero-intervention ranking-power profiling on the affinity subsets of the
same anchor set (`experiments/exp11_oracle_ranking_power.py`, pre-registered
docstring, pilot 4/4; evidence
`experiments/results/exp11_oracle_ranking_power/`). Subset rule = per target,
binders with measured Kd gated by `ranking_eligible` (flag defaults True
where absent — pilot-3 targets carry none), giving the retained per-target
n 6/8/5/6/3/6 = 34 entries; the rule was pre-verified by recomputing the
nine retained v2 JSONL cells to max |Δρ| = 0. ρ = Spearman(oracle score,
−log10 Kd), gate 0.6 analysis-side only. Instrument identical to Exp 10
(`ToolExecutor.run_tool` → deployed rhofold/proteinx/egarps, GPU-pinned
0/1/2 inherited; fixed protocol args only); CapGate advisory; every call
audited to `platform_audit.jsonl`.

- **34/34 successful, 0 failures** (wall ≈ 1.7 h, 164–208 s/entry).
- **18/18 cells measured; no oracle shows reliable ranking power across
  targets** — 2/18 nominal ρ ≥ 0.6 passes, both small-n with vacuous
  uncertainty (egarps × PDGF-BB n = 5, ρ = +0.667, CI −0.40–1.0, an
  ordering of near-zero scores; proteinx × Ang2 n = 3, ρ = +1.0 with two of
  three entries flipping ~0 ↔ ~1 across complex realizations); no oracle
  passes on more than one target; sensitivity 6/4/2/1 at 0.4/0.5/0.6/0.7;
  the retained best cell (rhofold × PDGF-BB +0.5643) reproduces
  bit-identically and stays sub-gate.
- Vs retained evidence: **10/18 cells identical** (all 6 RhoFold
  bit-deterministic — also re-derives the pilot-3 targets' retained ρ
  exactly); 8 shifted by ProteinX-complex realization variance (largest
  Δρ +0.5). Vs Exp-10 per-entry scores (same 34 ids): RhoFold max |Δ| = 0,
  ProteinX median 0.005, EGARPS median 1.9e-5 with 5 bimodal entries
  (max 0.9998) — the disclosed instability class.
- Figure `experiments/plots/fig3c_oracle_ranking.py` →
  `fig3c_oracle_ranking.{pdf,png}` (Cleveland dot plot, 3 oracle blocks ×
  6 targets; zero line solid / 0.6 gate dashed with nominal-pass rings;
  retained open markers + dumbbell hairlines; palette rev 7).
  2026-08-29 user-directed revisions: retained-evidence open markers +
  dumbbell hairlines dropped, then the zero/gate reference lines and
  their tags removed as uninformative — the panel shows the reset run
  only; in-figure title removed (Nature convention), every text element
  one 6-pt ink-black style, printed ρ values in a fixed right-hand
  column. Same-day user direction: retained-evidence comparison
  narrative removed from PAPER_DRAFT text and legends (it stays in the
  internal registers).
  `PAPER_DRAFT.md` Fig 3c legend + Results reset sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row c, `MANUSCRIPT.md` reset
  table, `AGENTS.md` updated. Docking panel 3d remains on retained evidence
  pending its own reset re-run.

## 2026-08-27 — Exp 10 (Fig 3b) executed under the reset: structure-oracle screening-power profile, 66/66, 0/18 cells pass

Zero-intervention oracle profiling on the registered aptamer anchor set
(`experiments/exp10_structure_oracle_screening.py`, pre-registered docstring,
pilot 6/6; evidence `experiments/results/exp10_structure_oracle_screening/`).
Anchor set `e1_anchor_set_v2.json` verbatim (66 entries, 6 targets;
user-confirmed after the target-count review — 6 is the discipline-exhausted
maximum). Instrument = the platform production tool path
(`ToolExecutor.run_tool` → deployed rhofold/proteinx/egarps services; DNA
scored as RNA via T→U per the anchor-set convention); CapGate advisory
(regression convention — under default enforce the three oracles are
SelfModel-governed and blocked); every call audited to
`platform_audit.jsonl` (the driver activates the audit runtime via
`runtime_from_env()`; an initial unaudited ~8-record attempt was discarded
and the run restarted from scratch — disclosed).

- **66/66 successful, 0 failures** (wall ≈ 3.3 h, 165–225 s/entry).
- **18/18 cells measured, 0/18 pass AUROC > 0.8; all 18 bootstrap 95% CIs
  cover chance**; best cell 0.800 exactly (RhoFold pLDDT × PDGF-BB);
  sensitivity 5/2/0/0 cells above 0.6/0.7/0.8/0.9.
- Secondary ranking (descriptive): ρ ≥ 0.6 only on two n = 3 Angiopoietin-2
  SPR subsets — underpowered by pre-registration.
- Vs retained evidence: **11/18 cells identical** (RhoFold bit-deterministic,
  pilot cross-check bit-identical; 5/6 ProteinX); the 6 EGARPS cells + 1
  ProteinX cell shift by ProteinX-complex realization variance (largest
  Δ +0.476, egarps × Thrombin) — headline invariant.
- Figure `experiments/plots/fig3b_oracle_screening.py` →
  `fig3b_oracle_screening.{pdf,png}` (balloon matrix; size + colour
  dual-encode AUROC, printed values, chance/gate reference lines; palette
  rev 7). `PAPER_DRAFT.md` Fig 3b legend + Results reset sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row 3b, `MANUSCRIPT.md` reset
  table updated.

## 2026-08-27 — Exp 8 (Fig 2i) executed under the reset: end-to-end runtime by workflow, 241/241, minutes-to-1 h per target

Zero-intervention timing of the 11 workflows (`experiments/exp8_runtime.py`
+ orchestrator `experiments/exp8_run_all.sh`, pre-registered docstring,
pilot 4/4; evidence `experiments/results/exp8_runtime/`). Instrument = one
`cli/form_chat.py` subprocess per run through the user form entry, inputs
verbatim, no thresholds, CapGate advisory (the documented regression
convention); services pre-warmed and GPU-pinned 0/1/2 by
`exp1_bring_up_services.sh`, so per-run time measures the delivered
workflow (pre-flight → generate → evaluate → score → rank → advisory
review → writeout), not cold model loads; lanes strictly sequential
(gpu_aptamer → gpu_tertiary → cpu → PA batch) against cross-lane
contention. Successful runs only enter the distribution.

- **241/241 successful**: all 210 RNADesign-210 tasks + all 31 PA
  regression sessions (PA_006–PA_036, each timed as one whole form
  session). Pooled median **2.6 min** (mean 4.4).
- **Workflow medians**: mRNA scoring 2.5 s; small-molecule 0.23 min; ASO
  0.28; secondary structure 1.21; IRES 1.34; siRNA 2.61; sgRNA 3.20; CDS
  3.21; tertiary structure 3.87; full-length mRNA 4.32; aptamer 6.29.
- **Completion profile**: 76.3% ≤5 min, 92.9% ≤10 min, 98.3% ≤30 min,
  **240/241 ≤1 h**. The four >30-min runs are all multi-turn aptamer PA
  sessions (42.4/42.9/59.9/**98.6** min); the single >1 h run is the GenNav
  `navigation=true` aptamer session PA_028. Suite-task maximum 27.0 min.
- **Disclosed amendment (registered before the PA_028 re-run)**: the
  PA-arm timeout (3600 s, calibrated on suite-task maxima) under-covered
  multi-turn navigation sessions — PA_027 finished at 3593 s and PA_028 was
  killed at 3600 s while progressing normally; the timeout's
  kill-only-the-direct-child semantics orphaned its turn-2 grandchild,
  which then completed (~5740 s total), exposing a driver defect now fixed
  (process-group kill). Amended budget 10800 s; PA_028 re-run once under
  it (**5917.2 s**, consistent with the orphan reconstruction); the
  original censored record retained in `pa_batch.jsonl`; the orphan's
  overlap window with PA_029 verified uncontaminating (42.63 s vs siblings
  42.15/42.52 s).
- Figure `experiments/plots/fig2i_runtime_ecdf.py` →
  `fig2i_runtime_ecdf.{pdf,png}` (log-axis ECDF per workflow + box inset,
  1 h reference line; palette rev 7 unchanged). `PAPER_DRAFT.md`,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md`, `MANUSCRIPT.md`, `AGENTS.md`
  updated.

## 2026-08-26 — Exp 7 (Fig 2g) executed under the reset: RNAsmol two-sided boundary, every registered metric reproduced

Zero-intervention re-run of the small-molecule oracle's two-sided profile
(`experiments/exp7_rnasmol_boundary.py`, pre-registered docstring, pilot
37/37; evidence `experiments/results/exp7_rnasmol_boundary/`). Instrument =
the deployed RNAsmol microservice exactly as the platform ships it (CPU
default via its own `start.sh`), one call per pair, sequences and SMILES
verbatim and **case-preserving** — the official held-out splits encode
modified bases in lowercase, and the agent tool layer's uppercase+T→U
normalization would silently re-introduce the v0.2.0 fidelity-defect class,
so the service endpoint is the fidelity-correct instrument (the retained
evidence's protocol; no ToolExecutor calls, hence no CapGate audit entries
at this layer). Checkpoint auto-selection via data-provenance hints only
(robin/pdb + molperturbation; FMN→pdb, MALAT1→robin; OOD no hints →
platform default); no thresholds, no tuning.

- **3,545/3,545 pairs scored, 0 failures**: robin test 1,492 + pdb test 170
  + FMN decoys 1,601 + MALAT1 decoys 265 + OOD panel 17.
- **Every registered metric of the retained 2026-08-11 evidence reproduced
  exactly**: robin AUROC 0.9744 (0.9678–0.9803), pdb 0.9828 (0.9607–0.9970;
  ≤500-nt subset 0.9788, n=126, 44 truncated service-side); decoy true-binder
  ranks 2/1601 (0.125 pct) and 7/265 (2.642 pct); OOD binder-vs-random-chem
  0.7222 (0.2778–1.0) and binder-vs-near-cognate 0.5625 (0.0625–1.0) — both
  CIs span chance. Verdict GO on all three axes.
- **Per-pair cross-check** vs the retained JSONL: medians ~1e-6 (MALAT1
  ≤3.8e-5, OOD ≤6.3e-4); a minority of near-decision-boundary inputs amplify
  inference-backend arithmetic (robin max 0.021 at 1/1492 pairs >1e-3; pdb
  0.047 at 1/170; FMN 0.367 at 53/1601 — one unstable near-0.5-band decoy,
  idx 367, re-scored bit-identical to confirm this run's determinism; the
  retained run's device is unrecorded). No registered metric moves. The
  cross-check tolerance was amended from bit-level to the disclosed
  4-decimal-AUROC + decoy-rank criterion **before** the full run (docstring
  records the amendment).
- Figure `experiments/plots/fig2g_rnasmol_boundary.py` →
  `fig2g_rnasmol_boundary.{pdf,png}` (forest dot + CI; khaki in-distribution
  / dark-warm-grey OOD; chance + 0.8 screening-gate reference lines; palette
  rev 7 unchanged). `PAPER_DRAFT.md` Fig 2g legend + Results sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row g and `MANUSCRIPT.md`
  reset-run table updated with the re-run as the numbers of record.

## 2026-08-25 — Platform fix: species-resolved LinearDesign codon tables; Exp 2+3 (Fig 2b–c) re-run

User-reported defect (the Exp 2+3 E. coli outliers): ``cai_species`` only
reached the CAI evaluator — LinearDesign always designed against the
service's bundled human table regardless of species (GFP / β-galactosidase
designed CAI ≈ 0.60 scored against their E. coli tables). Fixed at the
platform layer, not the driver:

- **Species-resolved codon tables**: 11 LinearDesign-format CSVs generated
  from the same Kazusa tables the CAI evaluator uses
  (``agent_core/data/codon_usage_lineardesign/``; generator
  ``scripts/gen_lineardesign_codon_tables.py`` with a ``--check`` drift
  guard used by the test suite). ``mrna_cds_design`` resolves
  ``cai_species → codon_usage_path`` on **both** the golden path and the
  GenNav navigation path; an explicit ``lineardesign_codon_usage_path``
  still wins. Human designs now use the platform Kazusa table (verified to
  produce the same argmax sequences as the bundled table). Unresolvable
  species fail fast at the input layer with a clear message instead of
  silently designing against the human table. ``full_length_mrna_design``
  inherits the fix (it delegates CDS generation to the same workflow). The
  audit trail records the codon table on every LinearDesign call (verified
  on the live run). Note: LinearDesign λ=0 is pure-MFE, so the table only
  influences λ>0 designs — confirmed live before the re-run.
- **Tests**: +10 (``tests/test_lineardesign_species_wiring.py``); the old
  "unsupported species still runs" contract test rewritten to the new
  fail-fast contract; suite **646 passed, 1 skipped**. Folded in a repair of
  a pre-existing reset breakage: ``agent_core/calibrated/
  profiling_metrics.py`` still imported the deleted
  ``experiments/analysis/stats_utils`` — ``bootstrap_auroc_ci`` inlined
  verbatim from git history.
- **Exp 2+3 re-run** (driver docstring updated; pre-fix run archived at
  ``exp2_cds_nulls_prefix/``, session prefixes ``exp2d_/exp2s_`` vs the
  re-run's ``exp2rd_/exp2rs_``): 20/20 design + 240/240 scoring, 0 failures.
  CAI medians **0.832 / 0.729 / 0.675** (designed-vs-WT P = 6.9e-4,
  δ = 0.63; WT-vs-random P = 6.8e-7, δ = 0.67; designed-vs-random
  P = 2.2e-13, δ ≈ 1.0); MFE/nt medians **−0.336 / −0.051 / −0.047**
  (designed vs both nulls δ = −1.0; WT-vs-random NS P = 0.29). E. coli
  targets after the fix: GFP 0.597 → 0.701 (above its WT 0.560),
  β-galactosidase 0.603 → 0.740 (above its WT 0.729). Figures refreshed
  (``fig2b_cai``, ``fig2c_mfe_per_nt``); PAPER_DRAFT / FIGURE_PLAN_V5 /
  MANUSCRIPT §3.0 numbers updated.

## 2026-08-25 — Exp 5 (Fig 2e) executed under the reset: IRES literature panel at chance on the default path

Paper §2.2 experiment 5 re-run against the frozen gated platform
(`experiments/exp5_ires_literature_panel.py`, pre-registration in its
docstring; pilot 6/6 then the full panel, `RNADA_CAPGATE=advisory`):

- **Panel (user-approved expansion before any run)**: positives extended
  from 3 to **9 literature IRES 5′UTRs** — the original EMCV/HCV/poliovirus
  plus FMDV (NC_004004.1:1-1058), HRV-A1 (NC_038311.1:1-626), BVDV-1
  (NC_001461.1:1-385) and the three cellular IRES the asset table had
  promised but never landed (c-myc NM_002467.6:1-363, Bip/GRP78
  NM_005347.5:1-217, VEGF-A NM_001025366.3:1-496; ranges = 1..CDS_start−1,
  provenance recorded in the anchor `SOURCES.md`); negatives unchanged (50
  GENCODE v46 200-nt 5′UTR windows). n = 59.
- **Zero-intervention rule (user-directed)**: one `ires_prediction`
  workflow run per sequence with platform defaults; the only deviation is
  `probability_threshold=0.0`, registered before the pilot — the threshold
  is a labelling knob (the service computes every fragment's probability
  regardless), and 0.0 merely disables the label filter so raw
  probabilities reach the workflow's score/rank layer for below-threshold
  sequences. Threshold-free AUROC over the raw scores; ROC + pointwise 95%
  TPR band via stratified bootstrap (10⁴ replicates, seed 20260825).
- **Primary result (pre-registered mode-0 arm — the workflow default)**:
  59/59 scored, 0 failures; **AUROC 0.478 (95% CI 0.311–0.649),
  Mann–Whitney P = 0.841 — indistinguishable from chance**. 20/50
  negatives score above 0.5 (median 0.449); score–length correlation
  r = 0.018 (not a length artifact). The legacy 3-positive-panel 0.762
  does **not** reproduce: the legacy-3 subset against the same 50
  negatives scores 0.513 (legacy protocol unrecoverable — deleted in the
  reset; this re-derivation is the number of record).
- **Disclosed mode-2 addendum arm** (registered after the primary was
  known, never substituted for it): sliding-window scanning at upstream
  defaults (window 174 / step 50 — the native regime; removes the
  341–1058-nt-vs-200-nt regime mismatch between positives and negatives).
  **AUROC 0.673 (95% CI 0.467–0.862), P = 0.102** — directionally better,
  CI still spans 0.5, and the estimate sits exactly where E16 graded the
  oracle on IRESfinder's own held-out sets (0.68/0.73/0.76, all below the
  0.8 screening gate → enforce-gated). The calibrated self-knowledge and
  the literature panel agree: the deployed IRES oracle has ~0.7
  discrimination at best and the default full-sequence path has none.
- Evidence `results/exp5_ires_panel/` (`panel_runs.jsonl`,
  `panel_runs_mode2.jsonl`, `summary.json`, `roc_points_{mode0,mode2}.csv`);
  figures `experiments/plots/fig2e_ires_roc.py` →
  `plots/output/fig2e_ires_roc.{pdf,png}` and
  `fig2e_ires_roc_mode0.{pdf,png}` (all palette rev 7; the workflow's warm
  grey `#B7B0A2`, chance diagonal in neutral grid). **Figure endpoint
  re-registered to the mode-2 scanning arm (user direction, 2026-08-26)**:
  the canonical `fig2e_ires_roc.*` now renders mode-2 (AUROC 0.673) — it is
  the legacy panel's protocol (legacy per-sequence scores match this arm
  exactly, confirmed against `PAPER_FACT_SHEET.md`) and the oracle's native
  window regime; the pre-registered mode-0 default-path result stays the
  primary analysis record and its figure is archived as
  `fig2e_ires_roc_mode0.*`. No scores were recomputed.
- `docs/MANUSCRIPT.md` asset table + §3.0 programme table updated;
  `docs/FIGURE_PLAN_V5.md` row 2e and the `PAPER_DRAFT.md` Fig. 2e
  legend/Results observation (3) updated to the measured numbers (and the
  stale "EMCV 0.808, poliovirus 0.891 literature-panel reproduction"
  parenthetical dropped — those were task-protocol scores, not panel
  scores).

## 2026-08-25 — Exp 4 (Fig 2d) executed under the reset: inverse folding 21/25 exact

Paper §2.2 experiment 4 re-run against the frozen gated platform
(`experiments/exp4_inverse_folding.py`, pre-registration in its docstring;
pilot 5/5 then the full 25-task matrix, `RNADA_CAPGATE=advisory`):

- **Zero-intervention rule (user-directed)**: the platform is measured
  as-is — no threshold presets, no objective tuning, no parameter sweeps;
  task inputs fed verbatim from RNADesign-210
  `06_rna_secondary_structure` (25 targets, 9–54 nt, 4–70 °C, function
  modes m/p/mp, start-sequence constraints). The single arm is the
  `rna_secondary_structure_design` golden path (RNAinverse ×N → RNAfold
  fold-back validation + GC → scoring → ranking).
- **Primary metric**: best-ranked candidate dot-bracket Hamming distance to
  the target (the platform's own `structure_distance`; 0 = exact recovery).
  Secondary: base-pair distance (analysis-side), per-candidate profile,
  any-candidate-exact (generation vs delivery).
- **Results**: 25/25 runs successful; **21/25 exact recovery** (dot-bracket
  distances 0×21, 2, 2, 4, 6; base-pair distances of the four misses
  1, 2, 3, 1 — at most 3 of 10–14 target pairs). All four misses are
  mp-mode / combined-parameter / extreme-temperature / longest-target edge
  tasks (015, 018, 021, 024); no candidate in any miss's ranked set was
  exact (generation-limited, not ranking-limited). Categories: basic 1/1,
  edge 19/21, full 1/3. The pre-reset run and the Exp-1 lane had observed
  22/25 (different stochastic realization; RNAinverse is stochastic) —
  this run's 21/25 is the number of record.
  Evidence `results/exp4_inverse_folding/` (`pilot.jsonl`, `records.jsonl`,
  `summary.json`); figure `experiments/plots/fig2d_inverse_folding.py` →
  `plots/output/fig2d_inverse_folding.{pdf,png}` (strip + step cumulative
  curve; exact dots in the workflow's grey green `#8DA290`, misses in the
  reserved dark warm grey `#7A7672`, cumulative curve slate blue
  `#6B7B8D` — all from palette rev 7).
- Driver fix during analysis: base-pair distance corrected to the standard
  |P₁ Δ P₂| definition (an integer-halving slip mis-scored asymmetric
  stem extensions; recomputed from the stored structure strings, no
  platform re-run).
- `docs/PAPER_DRAFT.md` Results §2.2 observation (2) and the Fig. 2d
  legend updated to 21/25; `docs/FIGURE_PLAN_V5.md` row 2d re-pointed to
  the new evidence path.

## 2026-08-25 — Exp 2+3 (Fig 2b–c) executed under the reset; fig 2c re-registered as a three-arm panel

Paper §2.2 experiments 2 and 3 merged into one driver and re-run against the
frozen gated platform (`experiments/exp2_cds_null_model.py`, pre-registration
in its docstring; pilot 3/3 then full matrix, `RNADA_CAPGATE=advisory`):

- **Designed arm = the system's CDS golden path as-is** (user-directed):
  `mrna_cds_design` with `design_tool="all"` — LinearDesign λ∈{0,1,4,10} +
  RNARL + GEMORNA, each candidate folded (LinearFold), GC/CAI/RNASTOP-scored
  and ranked; the best-ranked candidate is the arm's data point. No λ or
  codon-table tuning (the legacy "pure-CAI LinearDesign" attribution is not
  reconstructible and is replaced by this registration).
- **Null arms**: WT = the 20 NCBI RefSeq `wt_cds/` anchors; random = 10
  seeded synonymous resamples per WT (n = 200, uniform over the standard
  code, seed `exp2:<target>:<draw>`, deterministic). One scoring path for
  all 240 sequences (`mrna_sequence_scoring`: CAI via Kazusa tables,
  species-resolved + GC + LinearFold MFE).
- **Results**: design 20/20, scoring 240/240, zero failures. CAI medians
  **0.830 / 0.729 / 0.675** (designed > WT > random gate PASS;
  designed-vs-WT P = 7.1e-3 δ = 0.50; WT-vs-random P = 6.8e-7 δ = 0.67).
  MFE/nt medians **−0.336 / −0.051 / −0.047** (designed vs both nulls
  P ≤ 7e-8, δ = −1.0; WT-vs-random NS P = 0.29).
- **Fig 2c re-registered (user-directed)**: the legacy WT-vs-random-only
  folding control becomes a full three-arm MFE/nt panel — the designed CDSs
  lead on codon adaptation and structure simultaneously, and the WT≈random
  null contrast shows the CAI ordering is not a folding artifact. Evidence
  `results/exp2_cds_nulls/` (`design_runs.jsonl`, `fig2_cds_nulls.jsonl`,
  `summary.json`); figures `experiments/plots/fig2bc_cds_nulls.py` →
  `plots/output/fig2b_cai.{pdf,png}`, `fig2c_mfe_per_nt.{pdf,png}`.
- **Palette**: `ARM_COLORS` semantic slots added to `experiments/plots/palette.py`
  under rev 7 (designed = terracotta `#C08B7C`, WT = sage `#A3B18A`,
  random = the reserved dark warm grey `#7A7672`); Fig 2a re-rendered.
- `docs/PAPER_DRAFT.md` Results §2.2 observation (1) and the Fig. 2 legend
  rewritten to the reset numbers; `docs/FIGURE_PLAN_V5.md` rows 2b/2c and
  `docs/MANUSCRIPT.md` §3.0 register updated. Known recorded caveats: the
  two E. coli targets (GFP, β-galactosidase) are designed against
  LinearDesign's default human codon table (frozen-platform behaviour,
  documented in the driver docstring) and the Influenza HA WT anchor derives
  from a different strain than the benchmark protein (pre-existing anchor
  documentation).

## 2026-08-25 (z) — Experiment-programme reset: legacy campaigns deleted, RNADesign-210 audited+repaired, Exp 1 re-run 210/210

User-directed reset (DECISIONS (z)): the architecture moved too much since
the legacy campaigns, so **all paper experiments re-run against the frozen
gated platform** with newly written drivers and figures; the legacy campaign
drivers (`run_platform_quality_benchmark.py`, `run_e16_e17_e18_oracle_profiling.py`,
`curate_*`), the `experiments/analysis` helpers, the `experiments/plots/paper_v5`
figure programme and the legacy campaign results (fig2–fig7, E3–E15, P0–P3,
junction line, PA regressions, caches/logs) are deleted. Retained: the
packaged-SelfModel evidence chain (`e1_*_v2`, `e7_*`, `rnasmol_boundary_panel*`,
`e16_e17_e18/`, `build_default_self_model.py`), `codon_tables/`,
`tool_inventory.json`, `MODEL_API_USAGE.md`, the workspace audit trail.

**RNADesign-210 dataset audit and repair** (`experiments/audit_rnadesign210.py`
+ `fix_rnadesign210.py`, report `results/rnadesign210_audit.json`): all 210
task inputs validate against the current workflow Input models; benchmark
manifest recounts (208→210, tertiary 18→20); category taxonomy normalized to
basic/edge/full (was 14 ad-hoc values incl. BMC-era labels); the 12 IRES tasks
rebuilt on real IRES-positive anchors (poliovirus 5′UTR for mode 0 — the old
synthetic 5′UTR scores 0.458 < its own 0.5 task threshold and mode-0 scores
of canonical IRES 5′UTRs peak ≈0.48, so the two mode-0 detection tasks use
0.45 with the rationale recorded in-task; EMCV 5′UTR for mode 2; best window
251–424 for mode 1); absolute IRES paths → repo-relative; stale junction-tool
expected chains dropped; all expected chains regrounded from observed traces
(`reground_tool_chains.py`; re-audit: 0 issues / 0 warnings).

**Exp 1 (paper §2.2 experiment 1, Fig. 2a) executed**: pilot 10/11 (the one
failure was the IRES data defect, fixed and verified 12/12 against the live
service), then the full matrix — **210/210 successful across the 11 workflows**
(primary arm `RNADA_CAPGATE=advisory`; five parallel lanes; GPU-pinned services
via `experiments/exp1_bring_up_services.sh`; records and per-workflow medians
in `results/exp1_rnadesign210/`). A 4-task **enforce probe** documents the
gated-platform boundary as data: IRES tasks refuse with an explicit
`GatedActionError`, small-molecule tasks fail cleanly with both oracles gated
(`enforce_probe.jsonl`). **Fig 2a** rendered (per-task tile carpet + horizontal
bar summary) from the new **unified palette**
(`experiments/plots/palette.py`). Palette history: rev 1 = the ten mandated
colours; rev 2 = a 12-colour replacement (withdrawn same day); rev 3 = ten
colours + two in-family extensions (withdrawn same day); rev 4 = twelve
colours extracted from a user reference figure (withdrawn same day);
rev 5 = the user's muted Morandi set (withdrawn same day);
rev 6 = the user's cool pastel set (withdrawn same day);
**rev 7 (final, user-confirmed 2026-08-25)** = the earthy Morandi
twelve-colour set, supplied directly (`#B5838D #D3B5B0 #C08B7C #D9C3A9
#CDBF9E #A3B18A #8DA290 #8FA6BB #6B7B8D #A99AAF #B7B0A2 #7A7672`) — eleven
identify the workflows (#7A7672 dark warm grey held out, reserved for
neutral-dark semantics such as failed tiles); warm and cool tones alternate,
slate blue separates the palest warms. All subsequent experiment figures use
rev 7 exclusively (DECISIONS (z)).

## 2026-08-25 — Paper figure-lettering unification (doc-only)

All six figure legends in `docs/PAPER_DRAFT.md` re-lettered to
`docs/FIGURE_PLAN_V5.md` (the operative build plan for
`experiments/plots/paper_v5/`). The v5 figure rebuild had updated the
Results body citations and the built figures, but the legends kept
pre-rebuild lettering — stale in Figs. 1 (b/c/f), 2 (g–i), 3 (f–i),
4 (c–i), 5 (d–i) and 6 (missing g–i). Body text gained citations for
previously unreferenced panels (Fig. 1c,f; 2g; 4g,i; 6g–i); the
representative-claims examples moved from main Fig. 4 to the planned
Supplementary Table S1, now registered in the figure plan alongside the
GenNav aptamer supplementary archive. Draft endnote panel counts corrected
(6 + 9×5; "End of draft v4.3" → v4.5). No numbers changed — lettering and
cross-references only. Same day, the first Results subsection was split
into a system-design subsection ("Overview of the RNADesignAgent platform",
Fig. 1) and the RNADesign-210 biological-validity results subsection
(Fig. 2), so experimental results begin with the second Results
subsection; content unchanged apart from the new heading. A legacy→v5
panel-lettering map was added to `docs/PAPER_FACT_SHEET.md` (legacy letters
double as `fig2_summary.json` keys and are kept verbatim), and the AGENTS.md
What's New index records the pass.

## 2026-08-22 (i) — Repo-wide simplification pass: workspace scratch isolation, demo tool retired, historical outputs purged

User-directed cleanliness pass over everything outside `external_repos/`
(code as the source of truth, no git archaeology):

- **Test-suite workspace leak fixed (real bug).** Every test run leaked
  scratch artifacts (`save_sequence` / `save_text_file` without a session
  context) into the real `workspace/` root — **141k files / 1.3 GB**
  accumulated. `tests/conftest.py` now redirects all default workspace bases
  to a per-run `workspace/_tests` scratch (removed afterwards); the redirect
  is inherited by subprocesses via the new `RNADA_WORKSPACE_BASE` env
  override honoured by `WorkspaceManager.__init__` (also useful for
  deployments). Literal-path test writers (`test_compute_*`) now write into
  the isolated base. Verified: full suite runs leave zero new files in the
  workspace root.
- **Demo tool removed**: `workflow_demo_echo` and the
  `build_default_tool_registry(include_demo=...)` parameter are gone —
  **41 registered tools, all production** (manifest regenerated:
  `experiments/results/tool_inventory.json`). Tests use local mock tools.
- **Layer-4 test dedup**: the identical QualityAgent retry-semantics blocks
  duplicated across the secondary/tertiary layer-4 modules moved to one
  parametrized module (`tests/test_layer4_agent_semantics.py`).
- **Documentation dedup in code**: 39 `tools.py` wrapper docstrings dropped
  their `Args/Returns/Raises` sections (verbatim duplicates of the Input-model
  `Field` descriptions); stale comments referencing deleted experiment
  drivers removed (`tools.py`, `evaluators.py`, `rna_aptamer_design.py`).
- **Historical outputs purged**: superseded figure generations
  (`experiments/plots/{paper,paper_v4,fig*_panels,fig*.png}`, ~24 MB),
  archived experiment rounds (`e5_s1_*_archive/`, `e14_audit_v{1,2}/`,
  versioned `e14/e8` re-run files, `codon_tables_e6/`, ~12 MB), orphaned
  `__pycache__`, and 141k leaked workspace scratch files + stale service-run
  intermediates (`workspace/*_service_runs` contents, 634 MB of RhoFold
  intermediates). **Repository shrank from 4.3 GB to 2.0 GB** (the remainder is dominated by 1.2 GB of required reference-genome data and the retained audit trail). Everything
  under `workspace/{audit,sessions}/` and every `*_fresh_audit_*` evidence
  directory is retained (audit trail untouched).
- Codonw-slim stub entries still present in two full-length-mRNA test files
  were removed with their tool (deleted 2026-08-18).
- Suite after the pass: **635 passed, 1 skipped** (the −1 is the merged
  demo-registration test); PA_006–PA_019 re-run green end-to-end.

## Condensed register: the 2026-08-18 → 2026-08-22 era

Each row: what changed, the defect count fixed on live-fetched data, the
evidence directory, and the DECISIONS.md entry. Suite counts are the
post-entry regression-suite size.

| Date | Change | Evidence | DECISIONS |
|------|--------|----------|-----------|
| 08-18 | System simplification: BMC framework removed after triple-falsified coordination gain; 12 dead tools purged (54→42 specs) + codonw_slim_service; E1–E15 experiment machinery and drivers deleted (evidence JSONs kept); bowtie2_ma type fix | git `1b45138` | (a), (m) |
| 08-19 | GenNav constraint navigation became the production opt-in on `rna_aptamer_design` v2.1.0 (`navigation` field; deterministic, zero-LLM; full trace in `_state_writeback["_gennav_trace"]`); batch-B fresh-data re-verification (PA_025–PA_036, 12/12); `tool_call` audit lines now carry `session_id` + `task_type` | `experiments/results/pa_regression_batchB_2026-08-19/`, `gennav_live_verification_2026-08-19/` | (n) |
| 08-20 | ASF/Pareto ranking generalized to five workflows + adversarial surfacing tests; paper_v5 figure programme (51 panels, `experiments/plots/paper_v5/`) | `docs/FIGURE_PLAN_V5.md` | (o) |
| 08-21 | Ranking governance: ASF objectives assembled from CapGate verdicts (deterministic, mode-independent; `agent_core/calibrated/objective_assembly.py`; `RNADA_CAPGATE=off` disables); Layer-0 tool audit (4 defects, e.g. EGARPS posting workspace-relative paths); Layer-1 capability audit (252 checks, EGARPS path fix); Layer-2 workflow audit (12/12 green on live-fetched data) | `workspace/tool_layer_audit_2026-08-21/`, `layer1_fresh_audit_2026-08-21/`, `layer2_fresh_audit_2026-08-21/`, `docs/RANKING_GOVERNANCE.md` | (p), (k) |
| 08-22 (b) | Layer-3 service-orchestration audit (45 checks, 3 defects: degraded-service pre-flight hole, `__all__` export bug, missing exec bit) | `workspace/layer3_fresh_audit_2026-08-22/` | (r) |
| 08-22 | GenNav-λ production wiring on `mrna_cds_design` v1.2.0 (`navigation` field replaces the static λ grid); ASO ordering converted to shared ASF ranking (v1.1.0, Borda → diagnostics); CDS runs attach the CAI×MFE/nt Pareto annotation | `tests/test_gennav_mrna_core.py` etc. | (q) |
| 08-22 (c) | Layer-4 multi-agent + CapGate + ranking-governance audit (5 defects: dropped ranking audit events, pipeline crash on dangling bindings, IRES swallowing tool failures, retry counting, int-enum overrides) | `workspace/layer4_fresh_audit_2026-08-22/` | (s) |
| 08-22 (d) | Layer-5 persistence audit (3 WorkspaceManager defects: `delete_session("")` rmtree of the sessions tree, unvalidated session-id path joins, `list_files` creating directories) | `workspace/layer5_fresh_audit_2026-08-22/` | (t) |
| 08-22 (e) | Layer-6 façade/CLI/API audit (6 defects: pipeline session-scoping leak, API success misreporting, task_id echo, dropped progress events, dead step events, bare `input()` on the non-tty pipeline path) | `workspace/layer6_fresh_audit_2026-08-22/` | (u) |
| 08-22 (f) | Interface Lock Policy removed repo-wide (~1,250 lines pure deletion; behavioural contracts remain pinned by `WORKFLOWS.md`, the regression suite and the PA drivers) | — | (v) |
| 08-22 (g) | Oracle version stamps: all 11 managed-oracle descriptors declare `oracle_version`; packaged SelfModel records carry the profiling-time stamp; drift warns + audits, never blocks | `tests/test_oracle_version_stamps.py` | (w) |
| 08-22 (h) | Full-platform E2E fresh-data audit — whole stack, all 11 workflows through all three entry points (56 checks; 3 defects: opaque sgrna seed failure, `stream_form` raising on hard failure, ViennaRNA inverse-fold accepting pseudoknot brackets → SIGSEGV) | `workspace/e2e_fresh_audit_2026-08-22/` | (x) |
| 08-22 (i) | Repo-wide simplification pass (this entry) | — | (y) |

## Current interface state

- **Tool count**: 41 registered specs, all production (`python -m
  agent_core.tool_inventory`).
- **Workflows**: 11, all plain `BaseDomainWorkflow` implementations; six rank
  by Achievement Scalarizing Function (DECISIONS (o)/(q)); GenNav navigation
  is an opt-in on `rna_aptamer_design` (length lattice) and `mrna_cds_design`
  (GenNav-λ).
- **Microservices**: 21 mapped services, ports 8003–8024.
- **No BMC interface anywhere**; no automatic workflow router — selection is
  explicit (CLI menu / `--workflow` / `explicit_workflow` / `--pipeline-file`).
- **Governance**: `RNADA_CAPGATE` = `off|advisory|enforce` (default
  `enforce`); packaged SelfModel 29 records; the CapGate audit trail lives at
  `workspace/audit/platform_audit.jsonl` (every `tool_call` line stamped with
  `session_id` + `task_type`).
