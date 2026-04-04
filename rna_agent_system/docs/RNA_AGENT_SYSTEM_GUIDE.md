# RNA Design Multi-Agent System Guide

## 1. 文档目的

本文档用于说明当前 `RNA_real_agent` 项目的整体架构、已有能力、目录规范、部署方式，以及后续新增生信工具时的标准流程。

目标读者包括两类：

- 人类开发者：快速理解项目的设计思路、当前状态和后续开发方式
- 后续接手的大模型：读完后能够立即知道项目结构、工具接入方式、调试顺序和扩展规范

本文档描述的是**当前真实代码状态**，不是最初设想中的理想状态。

---

## 2. 项目目标

本项目希望实现一个 RNA 设计智能体系统：

- 输入：自然语言任务、RNA 序列、蛋白序列
- 输出：调用底层生信工具得到设计结果、评分结果、结构预测结果
- 方式：上层 Agent 负责路由与编排，下层工具通过本地微服务隔离运行

核心原则：

- 长序列不直接在 Agent 上下文中传递
- Agent 与工具之间尽量通过 `workspace/` 文件路径通信
- 复杂生信依赖与主 Agent 环境隔离
- 主 Agent 层只通过 HTTP API 调用工具，不直接耦合底层仓库实现

---

## 3. 当前架构总览

当前项目采用：

- `Agent orchestration`: `LangGraph`
- `UI`: `Streamlit`
- `Tool interface`: `LangChain @tool`
- `Tool runtime`: `FastAPI`
- `Dependency isolation`: `Conda environment + FastAPI`
- `External repos`: 放在 `external_repos/`，优先作为独立上游源码层管理

当前主逻辑已经从“LLM 驱动节点”切换为“**规则驱动节点**”，原因是当前阶段重点是验证工具链是否可接入，而不是验证 LLM 推理效果。

也就是说：

- `Router` 目前是规则判断
- `Specialist` 目前是规则触发工具调用
- `Critic` 目前是规则判定 pass / retry
- 后续在工具链稳定后，可以再切回可配置的 LLM 模式

---

## 4. 当前目录结构与职责

建议从内层应用根目录理解项目，也就是：

```text
rna_agent_system/
```

当前关键目录如下：

```text
rna_agent_system/
├── agent_core/                     # Agent 编排逻辑
├── frontend/                       # Streamlit 前端
├── microservices/                  # 我们维护的微服务封装层
├── external_repos/                 # 第三方源码仓库层
├── workspace/                      # 运行中间文件
├── docs/                           # 项目文档
└── .env                            # LLM 配置（当前可不用）
```

### 4.1 `agent_core/`

主要文件：

- `state.py`
  - 定义 `AgentState`
  - 记录 `messages`、`current_filepath`、`workspace_files`、`retry_count`、`active_specialist`、`mfe`、`cai_score` 等状态

- `file_manager.py`
  - `save_sequence(content, prefix)`
  - `read_sequence(filepath)`
  - 是整个项目“长序列走文件、不走 prompt”的核心基础设施

- `tools.py`
  - 把微服务 HTTP 接口封装为 Agent 工具
  - 当前主要工具：
    - `predict_sirna_efficiency`
    - `check_off_target`
    - `mock_codon_optimization`
    - `predict_rna_secondary_structure`
    - `design_mrna_cds_with_gemorna`

- `nodes.py`
  - Router / Specialist / Tool Execution / Critic 的核心逻辑
  - 当前是**规则模式**

- `graph.py`
  - 用 `LangGraph` 组装工作流图

### 4.2 `microservices/`

这里放的是**我们自己的服务封装**，而不是第三方原始仓库。

当前已有：

- `sirna_attsioff/`
  - Mock siRNA 效率预测服务
  - FastAPI
  - 默认端口 `8001`

- `off_target_blast/`
  - Mock 脱靶检查服务
  - FastAPI
  - 默认端口 `8002`

- `viennarna_fold/`
  - ViennaRNA 的二级结构 / MFE 预测服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8003`

- `gemorna_service/`
  - GEMORNA 的 mRNA CDS 设计服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8004`

### 4.3 `external_repos/`

这里放第三方原始仓库。

当前已有：

- `GEMORNA/`

**重要：**

`external_repos/GEMORNA` 当前应作为 **git submodule** 管理，而不是普通目录直接硬拷入主仓库。

### 4.4 `workspace/`

存放运行中间文件，例如：

- 原始 RNA 序列
- 生成后的 CDS
- 结构字符串文件
- 其他中间输出

所有长序列原则上都应先保存到 `workspace/`，然后在 Agent 内只传 `filepath`。

---

## 5. 当前智能体工作流逻辑

当前工作流图结构如下：

```text
User Input
  -> Router
  -> Specialist (siRNA or mRNA)
  -> Tool Execution
  -> Critic
  -> End 或回到对应 Specialist
```

### 5.1 Router

当前是**规则路由**，不调用 LLM。

基本逻辑：

- 如果文本中包含 `mrna`、`design`、`protein`、`cds`、`utr`、`structure`、`fold`、`gemorna` 等关键词
  - 路由到 `mrna_specialist`
- 如果包含 `sirna`、`脱靶`、`off-target`
  - 路由到 `sirna_specialist`
- 默认也偏向 `mrna_specialist`

### 5.2 siRNA Specialist

规则式地产生两个工具调用：

- `predict_sirna_efficiency(filepath)`
- `check_off_target(filepath)`

### 5.3 mRNA Specialist

分两种模式：

- 如果用户文本偏“设计型”
  - 触发 `design_mrna_cds_with_gemorna(filepath)`
  - 输入文件保存的是蛋白序列
- 如果用户文本偏“结构预测型”
  - 触发：
    - `mock_codon_optimization(filepath)`
    - `predict_rna_secondary_structure(filepath)`

另外，如果先做了 `GEMORNA` 设计，而用户请求中又包含结构预测语义，当前 `tool_execution_node` 会在拿到 GEMORNA 输出后，继续自动调用 `predict_rna_secondary_structure`

### 5.4 Tool Execution

负责真正执行工具调用，并把结果写回 `AgentState`。

当前会更新的关键状态包括：

- `current_filepath`
- `workspace_files`
- `candidate_sequence`
- `efficiency_score`
- `off_target_genes`
- `cai_score`
- `mfe`
- `structure_filepath`

### 5.5 Critic

当前是**规则 Critic**，不调用 LLM。

逻辑：

- siRNA：
  - 如果 `off_target_genes > 0`，则 reject 并重试
- mRNA 结构预测：
  - 如果用户请求里有结构相关语义，并且 `mfe > -20.0`，则 reject 并重试
- 否则 pass

最大重试次数：

- `max_retries = 3`

---

## 6. 当前工具与端口分配

建议维持固定端口表：

- `8001`: `sirna_attsioff`
- `8002`: `off_target_blast`
- `8003`: `viennarna_fold`
- `8004`: `gemorna_service`

后续新增工具也建议继续顺延，例如：

- `8005`: 新工具 A
- `8006`: 新工具 B

这样主 Agent 层的工具地址稳定，不会频繁冲突。

---

## 7. LLM 当前状态

### 7.1 当前代码状态

虽然项目里仍保留 `.env` 和 `llm_config.py`，但**当前节点逻辑已经切换为规则模式**，暂时不依赖 LLM。

这样做的原因：

- 现在的重点是验证复杂工具链接入
- 工具接入阶段如果 LLM 不稳定，会增加调试噪音
- 先保证规则编排 + 工具链跑通，再恢复 LLM 更合理

### 7.2 未来如何恢复 LLM

建议后续做成配置开关，例如：

- `USE_LLM_ROUTER=true/false`
- `USE_LLM_SPECIALIST=true/false`
- `USE_LLM_CRITIC=true/false`

这样可以：

- 工具调试阶段用规则
- 产品化阶段再切回 LLM

---

## 8. ViennaRNA 的接入方式

ViennaRNA 已经成功接入，作为“真实工具接入模板”。

### 8.1 微服务层

目录：

```text
microservices/viennarna_fold/
```

文件：

- `environment.yml`
- `main.py`
- `start.sh`

接口：

- `GET /health`
- `POST /fold`

输入：

- `sequence`

输出：

- `structure`
- `mfe`

### 8.2 Agent 工具层

工具函数：

- `predict_rna_secondary_structure(filepath, service_url="http://localhost:8003/fold")`

当前返回格式是字符串：

```text
filepath=...; structure=...; mfe=...
```

之后如果需要更稳健，建议改成 JSON 风格的结构化返回。

---

## 9. GEMORNA 的接入方式

### 9.1 上游源码层

目录：

```text
external_repos/GEMORNA
```

来源：

- 上游仓库：[RainaBio/GEMORNA](https://github.com/RainaBio/GEMORNA)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库直接 vendoring 进主仓库历史

### 9.2 当前微服务能力

目录：

```text
microservices/gemorna_service/
```

当前已封装接口：

- `POST /generate/cds`

输入：

- `protein_sequence`

输出：

- `generated_sequence`
- `raw_output`

### 9.3 当前 Agent 工具能力

工具函数：

- `design_mrna_cds_with_gemorna(filepath, service_url="http://127.0.0.1:8004/generate/cds")`

输入：

- `filepath`，其中保存的是蛋白序列

输出：

- `generated_sequence`
- `output_filepath`
- `raw_output`

### 9.4 GEMORNA 的实际运行注意事项

这是当前最重要的工程细节之一。

#### 权重文件

`GEMORNA` 的 `checkpoints/*.pt` 很大，且原仓库通过 Git LFS 管理。

两种可行策略：

- 策略 A：服务器上执行 `git lfs pull`
- 策略 B：手动把真实 `.pt` 文件放入：

```text
external_repos/GEMORNA/checkpoints/
```

当前项目已经支持这两种方式。

如果 checkpoint 仍然是 LFS pointer，`gemorna_service/main.py` 会主动报错提示。

#### Python 版本

`GEMORNA` 官方环境要求：

- `python=3.10`

**不要用 `py39` 跑 GEMORNA。**

原因：

- 它依赖预编译的 `.so` 二进制扩展
- Python ABI 不匹配时会出现类似：
  - `undefined symbol: PyDescr_IsData`

因此 `gemorna_service` 一定要在独立 `python=3.10` 环境中运行。

#### Linux 优先

`GEMORNA` 更适合在 Linux 服务器上运行，特别是带 GPU 的环境。

你当前实际的推荐运行环境是：

- Linux
- Conda
- Python 3.10
- NVIDIA GPU（例如 4090）

---

## 10. 新增生信工具时的标准流程

以后如果要新增新的第三方工具或仓库，统一按下面流程走。

### 10.1 先判断工具类型

判断这个工具属于哪类：

- 命令行工具
- Python 库工具
- 深度学习模型工具
- 需要大权重 / GPU 的工具

### 10.2 第三方源码层落地

如果是独立仓库：

- 克隆到 `external_repos/`
- 优先用 `submodule` 管理

例如：

```text
external_repos/new_tool_repo/
```

### 10.3 不要直接耦合上游实现到 Agent

主项目不要直接从 `agent_core/` 去 import 第三方仓库内部代码。

正确方式：

1. 先做 `microservices/new_tool_service/`
2. 再在 `agent_core/tools.py` 中通过 HTTP 封装

### 10.4 每个微服务都按统一模板建立

以后新的微服务目录至少应包含：

```text
microservices/new_tool_service/
├── environment.yml
├── main.py
└── start.sh
```

### 10.5 工具层统一只传 filepath

原则：

- 长序列不直接作为 tool 参数传
- 一律先写到 `workspace/`
- tool 入参尽量是 `filepath`

### 10.6 接入 Agent 的最小改动点

新增工具时通常只需要看这几个位置：

- `agent_core/tools.py`
  - 新增 `@tool`
- `agent_core/nodes.py`
  - 把工具加进某个 specialist
  - 补解析逻辑
- `agent_core/state.py`
  - 如果有新的关键指标，补状态字段
- `agent_core/graph.py`
  - 如果要新增 specialist，则补节点和边

### 10.7 测试顺序固定

建议统一按这三层测试：

1. 先测上游原始命令
2. 再测微服务接口
3. 最后测 Agent 调用

不要一开始就直接点 Streamlit，这样很难定位问题。

---

## 11. 代码与仓库传输规范

你当前不是在本地最终运行，而是在另一台 Linux 服务器上运行，因此要特别注意“仓库怎么传”和“哪些文件不应该靠 Git 传”。

### 11.1 主仓库传输

主仓库正常 `git push / git pull`

### 11.2 submodule 传输

像 `GEMORNA` 这种外部源码仓库，应通过 submodule 管理。

新 clone：

```bash
git clone --recurse-submodules <repo-url>
```

已有 clone：

```bash
git pull
git submodule update --init --recursive
```

### 11.3 大文件传输

大权重文件不建议依赖主仓库传输。

例如：

- `checkpoints/*.pt`

推荐方案：

- 用上游 `git lfs pull`
- 或你手动复制到服务器对应目录

### 11.4 应该避免提交的内容

以下内容不要继续进入主仓库：

- `__pycache__/`
- `*.pyc`
- `.DS_Store`
- 本地临时日志
- 本地下载的大权重缓存

当前主仓库已经补了基础 `.gitignore`，但历史上误提交的缓存文件如果仍在索引中，需要后续手动清理。

---

## 12. 推荐测试顺序

### 12.1 单工具测试

例如测试 ViennaRNA：

1. 启动 `viennarna_fold`
2. `curl /health`
3. `curl /fold`

例如测试 GEMORNA：

1. 先直接跑 `src/generate.py`
2. 再启动 `gemorna_service`
3. 再 `curl /generate/cds`

### 12.2 智能体集成测试

在微服务都启动后，再启动：

- `frontend/app.py`

然后测试：

- siRNA 请求
- mRNA 结构预测请求
- GEMORNA 设计请求
- GEMORNA 设计 + RNAfold 联合请求

---

## 13. 当前已知风险与限制

### 13.1 Router / Specialist / Critic 目前是规则模式

优点：

- 稳定
- 可控
- 易调试

缺点：

- 灵活性不如 LLM
- 复杂自然语言理解能力有限

### 13.2 `mock_codon_optimization` 仍然是假的

当前 mRNA 分支里：

- `predict_rna_secondary_structure` 已是真实 ViennaRNA
- `design_mrna_cds_with_gemorna` 已是真实 GEMORNA 接入
- 但 `mock_codon_optimization` 仍是模拟工具

后续可以替换成真实密码子优化工具。

### 13.3 GEMORNA 输出解析仍可继续增强

当前是通过解析 `stdout` 抽取生成序列。  
如果后续发现输出格式变化，建议把解析逻辑改得更稳：

- 返回多候选
- 明确打分
- 明确输出文件

### 13.4 `GEMORNA` 的二进制 `.so` 对 Python 版本敏感

必须优先保证：

- Linux
- Python 3.10

否则可能出现 ABI 兼容性报错。

---

## 14. 后续最推荐的发展路线

建议按下面顺序继续推进：

1. 先把工具链接全，优先真实工具替换 mock 工具
2. 保持规则模式，先把每个工具独立跑通
3. 等工具生态稳定后，再恢复可配置的 LLM 模式
4. 再逐步引入：
   - 更细的 specialist
   - 更强的 critic
   - 结果排序 / 候选集筛选
   - 多工具串联规划

---

## 15. 一句话总结

当前这个项目的核心设计可以概括为：

**上层 Agent 只负责规则路由与工作流编排，下层所有复杂生信能力都通过 `Conda + FastAPI` 微服务隔离运行，长序列统一走 `workspace filepath` 传递，第三方源码通过 `external_repos/` 独立管理。**

以后新增工具时，统一按下面的固定动作做：

1. 放到 `external_repos/`
2. 建 `microservices/<tool>_service/`
3. 在 `agent_core/tools.py` 封装 HTTP 工具
4. 在 `nodes.py` 接 specialist
5. 先测原始命令，再测微服务，再测 Agent

