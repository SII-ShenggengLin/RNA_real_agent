# HANDOFF 2026-08-09 — E6 探针 P1–P5 全部出结论,待用户拍板 3 点后落驱动代码

**上一会话:** HANDOFF_2026-08-09_E6_PLANNED.md(E6 规划完成,计划已批准)
**本会话:** 编写 probe_e6_gennav.py → 修复 4 处探针缺陷 → 真实运行 P1–P5 全部出结论 → 探针结论已汇报,等待用户拍板
**下一会话目标:** 用户拍板 3 点(①D2 判据 ②frac/floor 标定 ③R3 轴内语义)→ 落 gennav_core.py / run_e6_gennav.py / test_gennav_core.py → 同步文档 → E6 S0/S1/S2

---

## 0. 当前状态(2026-08-09,会话关闭时)

- **无实验在跑**(所有后台任务已 completed;探针运行结束 EXIT=0)。
- **git**:main = b6dad08,与 origin/main 同步;418 行非 E5 改动保持原样;**`experiments/probe_e6_gennav.py` 为未跟踪新文件**(48.8KB,git 操作先问用户)。
- **pytest**:649 passed 基线未变(本会话未改任何已跟踪文件)。
- 微服务健康(gemorna 8004 / lineardesign 8014 / linearfold 8015);勿杀任何服务;jupyter + GPU_get.py 在跑。
- **探针产物全部在** `/tmp/e5_probe_carm/e6_*`(5 个 JSON + e6_ld_probe_cache.json 20 键 + e6_ld_cds_cache.json)。

## 1. 探针结论(P1–P5 真实运行,产物时间戳 2026-08-09 13:07)

### P1 可行性区间(真实 LD 20 次,产物 e6_p1_feasibility.json)✅
| 靶 | 可行档 | 探测成本 |
|---|---|---|
| A1AT | {2,4,8,10,20,50} | 4 LD |
| Insulin | **{2,8,20}**(E5 仅 {4,10};λ4/10 当前阈值 C6 失败) | 4 LD |
| EPO | {1,2,4,8,10,20,50} | 4 LD |
| GFP | {4,8,10,20,50} | 4 LD |
| IL-2 | {2,8,20,50} | 4 LD |

- 5 靶全 tier=≥3,verdict 全绿(all_ge3_or_bisect / ld_probe_le5 / **gfp_lambda50_open**)
- λ-CAI 曲线单调;GFP λ50 CAI=1.0 全约束过 → 开采确认

### P2 方向轴 R3 构造性(真实档位,产物 e6_p2_axis.json)✅(含 3 处修复)
探针发现并修复 3 个生成层缺陷(均为探针内修复,已生效):
1. **frac 轴 CAI 结构性不足**:纯 fraction 加权在 A1AT 0.77/Insulin 0.69 < CAI_MIN 0.8 → 整轴空交付 → 半倾斜混合(每 aa 位 0.5 概率取 max-fraction,否则 fraction 加权)+ 接受重试 [0.88,0.92](`axis_frac_tuned`,64 种子内实测 12–26 次命中)
2. **cai_floor 与扩展器叠加跌破硬约束**:floor 压 0.8 下沿 + 多样度扩展器 10% 密度(≈0.02 降幅)→ CAI<0.8 → stability 整轴空交付 → floor 目标参数化 **0.85**(`axis_cai_floor(floor_target=0.85)`,留扩展余量;硬约束 CAI_MIN 0.8 不变)
3. **轴派生与源档 CDS 无关 + 格种子碰撞**:轴 CDS 从 protein 重新生成(丢失档位特征),cell_seed 不含源 idx(GM 行同 λ 同种子 → CDS 碰撞趋同 → D1=0.0);且真实 LD 探测档不在 survey → Insulin 格只剩 GM 行 → 修复:frac 轴在**源 CDS 上应用**(`axis_apply_frac`,0.5 保留源密码子)+ **cell_seed 含 src/idx**(`_seed(f"{target}|{src}|{lam}|{idx}|{axis}")`)+ 源 CDS 表并入 e6_ld_probe_cache

修复后(A1AT/Insulin):
- 三轴 CAI 1.0 / 0.90 / 0.85;格 pass A1AT 315/315、Insulin 159/234
- R3 分离:A1AT 3/3、Insulin 2/3(≥1/3 达标)✓
- D1 全 True(pairwise 0.021–0.149 ≥ 0.02)✓
- **D2 全 False(结构性,见拍板点①)**:轴锁定交付集中画像偏好档(expression→rank0、stability→max rank、balanced→median rank),len(lams)≥3 或跨度≥2 不可达

### P3 多样度扩展器(产物 e6_p3_diversity.json)✅
- 密度 **0.10** 标定(两靶 pairwise≥3%;cai_keep/local_keep 全 1.0),远低于 30% 上限
- 密度扫描曲线:Insulin min_pairwise [0.0177, 0.0526, 0.0741, 0.0902, 0.1322, 0.1339]、A1AT [0.0235, 0.0471, 0.0724, 0.0945, 0.1148, 0.119]

### P4 物种上下文(产物 e6_p4_context.json)✅
- 18/18 host 表命中;GFP/Luciferase/Ovalbumin 记 host-based approximation;显式失败路径验证

### P5 S2 功效预演(产物 e6_p5_power.json)✅
- 54 对(5 已知靶 15 对 + 13 MC 靶 39 对),discordant 全单向 13(0 A-pass/C-fail)
- mcnemar_p=0.00024 <0.05;复合得分 Wilcoxon p=1.4e-8
- MC 模型:构造修复单向 C≥A(fix_rate=0.85×d;A 过时 C 偶发反例 0.05)

## 2. 待用户拍板(探针结论 → 落驱动代码前必须拍板)

**① D2 判据修订**(判据变更):
- 现状:轴锁定交付下每画像交付集中偏好档,`len(lams)≥3 或跨度≥2` 结构性不可达;多样度已由 D1(pairwise≥2%,扩展器保证)+ 轴 CAI 梯度(0.85–1.0)承载
- 选项 A(推荐):D2 改为「交付多样度复合判据」= D1 ∧ 交付内 CAI 跨度≥0.05;C 臂 λ 档覆盖改由 E14_gen_lattice 格级声明(格内档数≥3)
- 选项 B:D2 原判据仅考核 A/B 臂(E5 语义),C 臂豁免
- 选项 C:交付不轴锁定(E5 按 U 取 5)——R3 分离变脆,不推荐

**② frac/floor 轴标定**(组件 2 内部,方法细节):frac=半倾斜混合+接受重试 [0.88,0.92]、floor 目标 0.85(硬约束 0.8 不变、分离阈值 0.05 不变)——建议采纳,写入判据书注记(E13_gen_axis)

**③ R3 轴内语义确认**(计划 C3):R3 top-1 按轴锁定交付取,分离由构造保证——探针实证 2–3/3 对达标

## 3. 后续动作(拍板后,按序)

1. **实现 `agent_core/generation/gennav_core.py`**(组件 1–4 纯函数;复用 run_e5_constraint_nav 纯函数 import 零复制;轴函数从 probe 升格——注意 probe 是探针实现,正式化时按拍板后口径重写)
2. **实现 `experiments/run_e6_gennav.py`**(三臂分层池 A/B=静态配方池/C=导航格;gate_action 第 5 道闸 request_generate;判据书 v8 六项:①e2e C≥0.8 且 C≥A 平局算过 ②约束率 C≥0.9 ③R1-R4(R3 注记 E13_gen_axis)④D1-D3(按拍板后 D2 口径;E14_gen_lattice)⑤方向性 C≥A 4/5 ⑥预算)
3. **实现 `tests/test_gennav_core.py`**(动态档序/取档计划/三方向确定性/多样度接受/CodonContext 18 靶 fixture;pytest 基线 649 + 新增全绿)
4. **同步文档**(本地产物不入库):PREREG 追加 §20「E6 决议注记」(C1–C6 + D2 拍板决议 + 轴标定注记);MODEL_API_USAGE §2 新增 E6 行(LD 探测 5/靶 + 细化 0–2 + C 臂 ≤3 ≈ 90–160;GEMORNA CDS 30→10 缓存零新调用)
5. **E6 S0**(Insulin×C 臂×3 重复,机制验证)→ **S1**(5 靶×3 臂,判据 v8 六项,S1 全过才 S2)→ **S2**(18 靶双终点:JCD-pass McNemar 主 + 连续复合得分 Wilcoxon 辅)
6. 复现锚点:e6_ld_cds_cache.json(键含 csv_hash)+ e6_gemorna_cds_cache.json + 池内 lattice_plan 快照;UTR 复用 e5_gemorna_cache.json

## 4. 纪律重申

- git 操作必须先问用户;判据/阈值/处置变更必须拍板 + 同步 PREREG §20 与 MODEL_API_USAGE §2
- 工作目录可能被外部切换 → 一律绝对路径(仓库根 `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`)
- 勿杀微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 PYTHONPATH=<rna_agent_system>)
- 勿动旧链路:run_e5_constraint_nav.py / codon_tables/CSV / sequence_utils.py / mrna_cds_design.py / lineardesign_service 零改动
- e5_s1_round3_archive/ 与 e5_s1_r2_rnarl_down_archive/ 勿删;e5_s1_r4.log / e5_s1.log / e5_s1_r5.log 勿覆盖;IL-2 探针勿重跑
- E5 已证伪路径勿重复:A 分支(λ 网格扩展修 R3)、C 分支(GEMORNA 30→60)、B1 作为补救、λ 加档修 D1
- 探针产物写 /tmp/e5_probe_carm/e6_*;探针缓存 e6_ld_probe_cache.json(20 键)是 E6 运行缓存的种子,勿删

## 5. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/probe_e6_gennav.py | **E6 探针(未跟踪,48.8KB)**;含 P1–P5 与修复后的轴函数(axis_frac_tuned / axis_apply_frac / axis_cai_floor(floor_target=0.85)/ build_mini_lattice / utility_dyn / _fold_check 缓存) |
| /tmp/e5_probe_carm/e6_p1..p5_*.json | 探针产物(结论见 §1) |
| /tmp/e5_probe_carm/e6_ld_probe_cache.json | 20 键 LD 缓存(键 {target}|{lam}|{csv_hash}) |
| /root/.claude/plans/gleaming-honking-ladybug.md | **E6 已批准计划(执行依据)** |
| run_e5_constraint_nav.py / probe_e5_generation_optimization.py | 复用源(零改动) |
