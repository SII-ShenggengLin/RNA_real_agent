# 下一会话提示词（复制粘贴即可）

先读交接文档：`rna_agent_system/experiments/results/HANDOFF_2026-08-07_E5_SURVEY_RUNNING_WAIT_PINBOARD.md`（含完整背景、根因、文献依据、纪律）,严格按其中 §3 步骤执行。

**当前任务一句话**：S0 验证发现池通过率异常（Insulin 6/36、A1AT/EPO 0/36）,根因是 C2（6x 同聚物）/C4（克隆位点）与 LinearDesign 生成分布结构性冲突（生成端无 DFA 约束,只能判定层处置）。用户已拍板"先停,查文献定 C2/C4 方案"。全 20 靶点池级扫描正在后台跑（PID 1043348,日志 `experiments/results/e5_pool_survey.log`,输出 `e5_pool_survey.json`,预计 40–60min）。

**第一步（按序执行,勿跳过）**：
1. 确认扫描进程：`pgrep -f e5_pool_survey`;挂后台 until 循环等日志出现 `DONE`（或进程退出）,`until grep -q "^DONE" rna_agent_system/experiments/results/e5_pool_survey.log || ! pgrep -f e5_pool_survey >/dev/null; do sleep 30; done`,完成/退出后 tail 日志确认 20 靶点齐全。
2. 跑离线重放矩阵：`cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python /tmp/e5_survey_replay.py`（零微服务调用,输出现状 vs 各 C2×C4×C6 组合通过率分布、zero-targets、每靶点明细、λ 多样性）。
3. **将重放矩阵 + 交接文档 §1.3 文献依据呈用户,拍板 C2/C4（±C6）方案**（候选：C2 6→7/8;C4 降软约束[类比 C5 先例:体外转录无克隆];C6 10→12/14[Insulin 特例];或组合）。**拍板前不改驱动、不跑 S0**。
4. 拍板后按交接文档 §3 第 4 步实施：改驱动 → pytest 全量（基线 649 passed, 1 skipped）→ Insulin 池重放 ×1 确认（`/tmp/e5_pool_replay.py`）→ 同步 PREREG（§4 注记、§7.1 分母、§9、§13-1,只增不改原拍板文本）→ 重跑 S0（setsid nohup + 日志落盘 + pgrep 确认 + until 等 `e5_verdict_s0.json`）→ 呈判定书 → 用户确认后 S1（5 靶点 × 3 臂）→ S2（20 靶点,2 分片串行）。
5. 当天更新 `experiments/results/MODEL_API_USAGE.md` 实测行。

**纪律**：git 操作先问用户（当前 run_e5_constraint_nav.py 与 calibrated/models.py 修改均未 commit）;改代码必跑 pytest 全量;预注册项改动先呈用户;微服务 8004/8014/8015 为实验拉起的勿杀;命令用绝对路径或同条内 cd（Bash cwd 每次重置）。
