# HANDOFF — 2026-08-14: E12 完成(主终点 NO-GO,但 discordance 接近显著),下一会话接续点

**会话背景**:用户目标"让 GenNav 在 aptamer 侧同预算下赢"。本会话完成 E12
(判据书 → S0 → S1 → S2 全程纪律执行):矩阵扫掠封闭矩阵轴 → 格增密 + S1
先验 + 面板门的新设计 → S2 主终点 NO-GO,但 McNemar 从 E10 的 9:4 (P=0.267)
推进到 9:2 (P=0.0654,差一格)。**所有实验已结束,无后台任务。**

---

## 1. 当前状态一览

| 实验 | 状态 | 关键结果 |
|---|---|---|
| **E12 S0**(机制门, Thrombin) | ✅ GO | 机制块全过(raw=47/48, LLM 3/4, 门全禁);Thrombin compact HER2 与扫掠一致 |
| **E12 S1**(19 候选靶全量探针) | ✅ GO | 增密格 17 长度 × n2 全部生成;面板门(补遗 v1, rate-based)通过:her2 靶 1/19(BSA), NAV=24, A-fail=26 |
| **E12 S2**(12 靶主终点) | ✅ 完成(NO-GO) | **McNemar b=9, c=2, P=0.0654**;C e2e=0.25(A e2e=0.00);机制块全过,零违规 |
| E12 判据书 + 补遗 | ✅ 已提交 | 7890e77(判据书)、dd60d09(补遗 v1 rate-based NAV)、f0e50f1(结果+补遗 v2) |

**无运行中的实验进程**(已确认)。全部证据已 git 提交。

## 2. 关键文件索引

### E12 产物(判据书 → 结果,全部已提交)
- 判据书(driver docstring 预注册): `experiments/run_e12_gennav_aptamer.py`
- 判定书: `experiments/results/e12_verdict_s{0,1,2}.json`
- 运行记录: `experiments/results/e12_runs_s{0,1,2}.jsonl`(append-only)
- 生成缓存: `experiments/results/e12_odesign_cache.jsonl`(读 E8∪E9∪E10∪E12)
- 审计轨迹: `experiments/results/e12_audit/`
- 判据书前分析: `experiments/analysis/e12_matrix_sweep.py`(324 变体扫掠)、
  `experiments/analysis/e12_protocol_variants_sim.py`(协议网格 V0-V5)

### 设计文档
- `docs/FIX_2026-08-12_DUAL_GENERALIZATION.md`:
  - 附录 H: E11 模拟(对称重定标/面板扩充封闭)
  - 附录 I: E12 方向分析(e2e 天花板 0.667 数学硬顶;协议空间穷尽;三杠杆配方)
  - 附录 J: E12 矩阵扫掠(0/324 决定性;格增密=唯一剩余杠杆)
  - 附录 K: E12 S2 结果(补遗 v2:面板门聚合约束 vs 每靶修复容量)
- `docs/CHANGELOG.md` 2026-08-14 条目;`docs/DECISIONS.md` Part 2 行 11 + 时间线

### 论文
- `docs/PAPER_DRAFT.md` — **尚未同步 E12**(E12 的 P=0.0654/e2e=0.25 数字与
  边界表述需要进 GenNav aptamer 段;若走"接受边界"路线必须改第 67 行末句;
  若走 E13 路线则等 E13 结果再改)
- `docs/PAPER_FACT_SHEET.md` — E9/E10/E11 行已有,**E12 行待补**

## 3. 科学结论(aptamer 侧最终边界,论文口径)

1. **机制杠杆已验证**: 格增密(17 长度)+ S1 实测先验在同预算 48-raw 下把
   c 4→2、P 0.267→0.0654(4 倍改善)、e2e 天花板 1.0(面板门 her2=0)。
2. **P 门差一格**: b=9/c=2;RNase_A compact(rate-based 判可修)未获轮次 →
   若修复则 P=0.039;c 细胞为 Pepsin compact、Thrombin standard(带优先饿死
   老面孔)→ 若保住则 P=0.004。3 轮预算恰在临界线上。
3. **e2e 门结构性封顶**(补遗 v2): 48-raw 每靶修复能力 ≈1-2 格;面板 7/12
   双 A-fail 靶 → 双修复+零反失+保留全过在预算内不可靠;面板门聚合 NAV
   约束没按每靶修复容量建模。
4. **最终表述**: "同预算下导航在 discordant 之战接近显著(9:2),但双门
   判据(P<0.05 ∧ C e2e≥0.8)在 48-raw 修复能力下不可同达"。

## 4. 下一步选项(等用户拍板,勿自行启动大规模实验)

1. **E13(判据书级修正)**: 面板规则改为"每靶 A-fail ≤1(≤2 靶例外)"——
   1-fail 靶的修复(1 轮 + 保留 2 带)在预算内可靠 → e2e 门可达,P 门同面板
   下 b 供给略降但仍可能过。补遗 v2 已写设计教训。成本: 一整轮 S0-S2
   (~2 天 GPU)。**这是不改判据的情况下唯一接近"赢"的路径,但预期仍是
   边缘组合而非保证。**
2. **接受当前边界**: 论文 GenNav aptamer 段同步 E12(P 4 倍改善 + 双门结构
   边界);PAPER_FACT_SHEET 补 E12 行。成本最低。
3. **判据层裁决**(用户专属权限): 例如主终点改单门(P<0.05)或 e2e 门降
   至 0.5——属"降低标准",只有用户能决定。

## 5. 已知事项(下个会话注意)

1. **判据书补遗 v1**(用户拍板, dd60d09): 面板门 NAV 测量 = laplace 率 ×
   NAV_DEPTH=11(S2 可达深度),非探针深度 raw 交付数(S1 探针 n2 下 raw-count
   系统性低估 → nav_frac=0.0 伪影)。
2. **判据书补遗 v2**(f0e50f1): 面板门聚合 NAV 约束不建模每靶修复容量 →
   e2e 门在双 A-fail 靶面板下结构性不可达;E13 若启动,面板规则须约束
   每靶 A-fail ≤1。
3. **LLM 配置**: DeepSeek via .env(DEEPSEEK_API_KEY),model 名不能传
   "deepseek"(必须 deepseek-v4-pro 或由 get_deepseek_llm() 默认读取)。
4. **服务**: ODesign(8012 GPU)、LinearFold(8015)可经 ensure_e12_services()
   自动启动;ODesign 调用 ~120-160s/次(新长度真实生成)。
5. **PAPER_DRAFT 未同步 E12**(见 §2)——是已知缺口,不是遗漏。
6. **E12 缓存已含全部 19 靶增密格**(s42 n2)+ A 格 + S0/S2 轮次格——若 E13
   启动,探针部分全部缓存命中,主要成本在轮次格与 LLM。

## 6. 下一个会话的提示词

```text
你是 RNADesignAgent 项目的延续会话。背景: 为了让 GenNav 在 aptamer 侧
同预算(48-raw 两臂同 cap)下赢过静态格,上一会话完成了 E12 全程:
矩阵扫掠(324 变体,0 决定性 → 矩阵轴封闭)后,采用"矩阵 v3(7/9/12)+
17 长度增密格 + S1 实测先验 + 面板门"设计(判据书 run_e12_gennav_aptamer.py
docstring 预注册),S0/S1 机制门 GO、面板门通过(her2 靶仅 BSA),S2 主终点
NO-GO: McNemar b=9/c=2/P=0.0654(差一格;E10 为 9:4/0.267),C e2e=0.25
(A e2e=0.00),e2e≥0.8 门结构性不可达(48-raw 每靶修复能力撑不起双 A-fail
靶全交付)。所有实验已结束,无后台任务。完整背景见
docs/FIX_2026-08-12_DUAL_GENERALIZATION.md 附录 H-K(含判据书补遗 v1/v2)
与本交接文档 docs/HANDOFF_2026-08-14_E12_COMPLETE.md;证据已全部 git 提交
(7890e77/dd60d09/f0e50f1);论文 docs/PAPER_DRAFT.md 的 GenNav aptamer 段
尚未同步 E12(已知缺口)。

你的任务:
1. 先读本交接文档与 FIX 附录 K,确认无遗留实验;
2. 向用户汇报当前状态与三个下一步选项(见交接文档 §4):
   A) E13: 面板规则改"每靶 A-fail ≤1"重预注册(补遗 v2 的设计教训;
      e2e 门可达、P 门边缘,预期非保证);
   B) 接受当前边界: 同步 PAPER_DRAFT(GenNav aptamer 段写入 E12 数字与
      双门结构边界)+ PAPER_FACT_SHEET 补 E12 行 + git 提交;
   C) 判据层裁决(用户专属): 主终点改单门或 e2e 门调整——属降低标准,
      仅用户可决定。
3. 等用户拍板后再行动;若选 A,必须按仓库纪律写新判据书(driver docstring
   预注册)→ S0 → S1 → S2,任何实现问题记录为判据书补遗,禁止事后改判据;
   判断改动是否属于"降低标准"由用户确认。
```

---

*本交接文档由 E12 收尾会话生成(2026-08-14),替代 2026-08-13 的
E10 交接文档作为当前接续点。*
