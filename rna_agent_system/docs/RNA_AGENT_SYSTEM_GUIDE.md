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

- `rhofold_service/`
  - RhoFold 的 RNA 三级结构预测服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8005`
  - 当前默认走单序列预测模式，不依赖本地 MSA 数据库

### 4.3 `external_repos/`

这里放第三方原始仓库。

当前已有：

- `GEMORNA/`
- `RhoFold/`

**重要：**

- `external_repos/GEMORNA` 应作为 **git submodule** 管理
- `external_repos/RhoFold` 也应作为 **git submodule** 管理
- 不要把外部仓库当普通目录直接 `git add .`
- `NuFold` 曾被评估过，但当前不纳入正式接入路线，原因见后文

### 4.4 `workspace/`

存放运行中间文件，例如：

- 原始 RNA 序列
- 生成后的 CDS
- 结构字符串文件
- `RhoFold` 生成的 `pdb` / `ct` / `npz` / `log`
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

- 如果文本中包含 `mrna`、`design`、`protein`、`cds`、`utr`、`structure`、`fold`、`gemorna`、`rhofold`、`3d`、`tertiary`、`三级结构`、`三维结构` 等关键词
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
  - 如果用户请求里还包含结构语义，当前会在 GEMORNA 设计完成后继续自动调用结构预测工具
- 如果用户文本偏“结构预测型”
  - 触发：
    - `mock_codon_optimization(filepath)`
    - `predict_rna_secondary_structure(filepath)`
  - 如果用户文本里还包含 `rhofold`、`3d`、`tertiary`、`三级结构`、`三维结构`、`pdb`
    - 还会额外触发 `predict_rna_tertiary_structure_with_rhofold(filepath)`

另外，如果先做了 `GEMORNA` 设计，而用户请求中又包含结构预测语义，当前 `tool_execution_node` 会在拿到 GEMORNA 输出后，继续自动调用：

- `predict_rna_secondary_structure`
- `predict_rna_tertiary_structure_with_rhofold`

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
- `tertiary_structure_filepath`
- `tertiary_structure_ct_filepath`
- `tertiary_results_filepath`
- `tertiary_log_filepath`
- `mean_plddt`

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
- `8005`: `rhofold_service`

后续新增工具也建议继续顺延，例如：

- `8006`: 新工具 A
- `8007`: 新工具 B

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

## 10. RhoFold 的接入方式

### 10.1 上游源码层

目录：

```text
external_repos/RhoFold
```

来源：

- 上游仓库：[ml4bio/RhoFold](https://github.com/ml4bio/RhoFold)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库直接 vendoring 进主仓库历史

### 10.2 为什么当前采用 RhoFold 而不是 NuFold

`NuFold` 已做过前期评估，但当前不作为正式接入方案，主要原因是：

- 它更强依赖外部前处理链路
- 需要 `rMSA`
- 需要 `IPknot`
- `rMSA` 数据库量级约 `~2TB`
- 原始脚本更偏向固定 `CUDA` 运行，工程接入门槛更高

相对而言，`RhoFold` 当前更适合本项目：

- 支持 **single sequence prediction**
- 可以先不接本地 MSA 数据库
- 已在 Linux + GPU 服务器上成功跑通微服务接口
- 更适合作为当前阶段“真实 3D RNA 结构工具”的第一接入点

### 10.3 当前微服务能力

目录：

```text
microservices/rhofold_service/
```

当前已封装接口：

- `GET /health`
- `POST /predict`

输入：

- `sequence`
- `single_seq_pred`，当前默认 `true`
- `checkpoint_path`（可选）
- `device`（可选）
- `relax_steps`

输出：

- `output_pdb_path`
- `secondary_structure_ct_path`
- `results_npz_path`
- `log_path`
- `service_output_dir`
- `mean_plddt`

### 10.4 当前 Agent 工具能力

工具函数：

- `predict_rna_tertiary_structure_with_rhofold(filepath, service_url="http://127.0.0.1:8005/predict", relax_steps=0)`

输入：

- `filepath`，其中保存的是 RNA 序列

输出：

- `output_pdb_filepath`
- `secondary_structure_ct_filepath`
- `results_npz_filepath`
- `log_filepath`
- `mean_plddt`

当前实现会把 `RhoFold` 生成的关键结果文件复制回主项目 `workspace/`，这样上层 Agent 仍然只传 `filepath`，不直接在消息里搬运大结果。

### 10.5 RhoFold 的实际运行注意事项

#### Python 与依赖版本

当前 `rhofold_service` 的环境固定为：

- `python=3.7.12`
- `pytorch=1.10.2`
- `cudatoolkit=11.3.1`
- `fastapi==0.95.2`
- `pydantic==1.10.13`
- `uvicorn==0.22.0`

这样做的原因是：

- 上游 `RhoFold` 环境本身偏旧
- 新版 `pydantic` / `fastapi` 组合在 `python=3.7` 下更容易出现兼容性问题
- 当前微服务代码已专门改成 Python 3.7 兼容写法

#### checkpoint

微服务当前会优先检查这些路径：

```text
external_repos/RhoFold/pretrained/RhoFold_pretrained.pt
external_repos/RhoFold/pretrained/rhofold_pretrained_params.pt
external_repos/RhoFold/pretrained/model_20221010_params.pt
```

如果推理时可以正常访问 Hugging Face，部分依赖文件会自动拉取；如果自动下载失败，建议直接手动把权重放到：

```text
external_repos/RhoFold/pretrained/RhoFold_pretrained.pt
```

#### 单序列模式优先

当前推荐部署方式是：

- `single_seq_pred=true`
- 不接本地 MSA 数据库

原因：

- 接入成本低
- 已能产生有效的 3D 结构结果
- 适合当前项目阶段的“工具先跑通”目标

如果后续需要更高精度，再单独扩展：

- 用户自带 `.a3m`
- 或服务器本地维护数据库并启用 MSA 模式

### 10.6 当前验证状态

`RhoFold` 微服务已在 Linux + GPU 服务器上完成最小闭环验证：

- `POST /predict` 成功
- `cuda:0` 推理成功
- 成功生成 `unrelaxed_model.pdb`
- 成功生成 `ss.ct`
- 成功生成 `results.npz`
- 成功生成 `log.txt`
- 已成功返回 `mean_plddt`

这意味着：

- `RhoFold` 已经通过“上游命令封装 -> 微服务接口”这一层验证
- 后续如果 Agent 集成侧报错，优先怀疑的是编排层或环境层，不再是 `RhoFold` 本体是否能跑

---

## 11. 新增生信工具时的标准流程

以后如果要新增新的第三方工具或仓库，统一按下面流程走。

### 11.1 先判断工具类型

判断这个工具属于哪类：

- 命令行工具
- Python 库工具
- 深度学习模型工具
- 需要大权重 / GPU 的工具

### 11.2 第三方源码层落地

如果是独立仓库：

- 克隆到 `external_repos/`
- 优先用 `submodule` 管理

例如：

```text
external_repos/new_tool_repo/
```

### 11.3 不要直接耦合上游实现到 Agent

主项目不要直接从 `agent_core/` 去 import 第三方仓库内部代码。

正确方式：

1. 先做 `microservices/new_tool_service/`
2. 再在 `agent_core/tools.py` 中通过 HTTP 封装

### 11.4 每个微服务都按统一模板建立

以后新的微服务目录至少应包含：

```text
microservices/new_tool_service/
├── environment.yml
├── main.py
└── start.sh
```

### 11.5 工具层统一只传 filepath

原则：

- 长序列不直接作为 tool 参数传
- 一律先写到 `workspace/`
- tool 入参尽量是 `filepath`

### 11.6 接入 Agent 的最小改动点

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

### 11.7 测试顺序固定

建议统一按这三层测试：

1. 先测上游原始命令
2. 再测微服务接口
3. 最后测 Agent 调用

不要一开始就直接点 Streamlit，这样很难定位问题。

---

## 12. 代码与仓库传输规范

你当前不是在本地最终运行，而是在另一台 Linux 服务器上运行，因此要特别注意“仓库怎么传”和“哪些文件不应该靠 Git 传”。

### 12.1 开发机与运行机分离

当前推荐的实际工作方式是：

- macOS 机器只负责开发、改代码、提交到 GitHub
- 带 GPU 的 Linux 服务器负责 `git pull` 后创建环境、启动微服务和运行 Agent
- 如果 Linux 服务器运行时报错，应以服务器上的真实报错为准进行排查

这样做的原因是：

- 当前多个生信工具依赖 Linux / CUDA / Conda
- macOS 更适合作为代码编辑与仓库中转环境
- 不应把“在 macOS 上无法运行”误判为工具本身无法接入

### 12.2 主仓库传输

主仓库正常 `git push / git pull`

### 12.3 submodule 传输

像下面这些外部源码仓库，应通过 submodule 管理：

- `GEMORNA`
- `RhoFold`

新 clone：

```bash
git clone --recurse-submodules <repo-url>
```

已有 clone：

```bash
git pull
git submodule update --init --recursive
```

如果某次正在修复 submodule 指针，或临时遇到坏的 submodule 引用导致 `git pull` 卡住，可以临时用：

```bash
git -c submodule.recurse=false pull
git submodule update --init --recursive
```

### 12.4 大文件传输

大权重文件不建议依赖主仓库传输。

例如：

- `checkpoints/*.pt`

典型包括：

- `external_repos/GEMORNA/checkpoints/*.pt`
- `external_repos/RhoFold/pretrained/*.pt`
- `external_repos/RhoDesign/checkpoint/*.pth`

推荐方案：

- 用上游 `git lfs pull`
- 或你手动复制到服务器对应目录

当前 `RhoDesign` 也属于这种情况。

例如你在本机已经放好的：

- `external_repos/RhoDesign/checkpoint/ss_apexp_best.pth`
- `external_repos/RhoDesign/checkpoint/no_ss_apexp_best.pth`

不应默认指望通过主仓库 Git 历史传到 Linux 服务器，更推荐在服务器侧单独补齐，或确认是否需要额外的大文件传输方案。

### 12.5 应该避免提交的内容

以下内容不要继续进入主仓库：

- `__pycache__/`
- `*.pyc`
- `.DS_Store`
- 本地临时日志
- 本地下载的大权重缓存
- `workspace/` 运行期输出
- 误加入索引的外部仓库目录

当前主仓库已经补了基础 `.gitignore`，但历史上误提交的缓存文件如果仍在索引中，需要后续手动清理。

### 12.6 提交流程建议

这个仓库里同时存在：

- submodule
- `workspace/`
- 外部模型权重

因此**不建议默认使用 `git add .`**。

更推荐的流程是：

```bash
git status --short
git submodule status
git add <具体文件或目录>
git commit -m "meaningful message"
git push origin main
```

### 12.7 GEMORNA 权重导致子模块脏状态时的处理

`GEMORNA` 的 `checkpoints/*.pt` 可能因为本地真实权重文件而表现为“子模块脏状态”，但这不一定代表代码真的变了。

如果你希望：

- 保留本地权重
- 又不想让主仓库一直显示 `m rna_agent_system/external_repos/GEMORNA`

可以在本机对子模块执行：

```bash
git -C rna_agent_system/external_repos/GEMORNA update-index --assume-unchanged \
  checkpoints/3utr.pt \
  checkpoints/5utr.pt \
  checkpoints/gemorna_3utr.pt \
  checkpoints/gemorna_5utr.pt \
  checkpoints/gemorna_cds.pt
```

这只是**本地 Git 状态技巧**，不会同步到远端，也不会传给别的机器。

---

## 13. 推荐测试顺序

### 13.1 单工具测试

例如测试 ViennaRNA：

1. 启动 `viennarna_fold`
2. `curl /health`
3. `curl /fold`

例如测试 GEMORNA：

1. 先直接跑 `src/generate.py`
2. 再启动 `gemorna_service`
3. 再 `curl /generate/cds`

例如测试 RhoFold：

1. 启动 `rhofold_service`
2. `curl /health`
3. `curl /predict`

推荐优先测试 payload：

```json
{
  "sequence": "AUGGCUACGUAGCUAGCUAGCUAGCUGA",
  "single_seq_pred": true,
  "relax_steps": 0,
  "device": "cuda:0"
}
```

### 13.2 智能体集成测试

在微服务都启动后，再启动：

- `frontend/app.py`

推荐从仓库根目录启动：

```bash
streamlit run rna_agent_system/frontend/app.py --server.fileWatcherType none
```

说明：

- 当前 `frontend/app.py` 已在代码中自动补了父目录到 `sys.path`
- 因此正常情况下不再需要手动设置 `PYTHONPATH`
- 某些 Linux 服务器上 `inotify watch limit` 偏小，因此建议保留 `--server.fileWatcherType none`

然后测试：

- siRNA 请求
- mRNA 结构预测请求
- GEMORNA 设计请求
- GEMORNA 设计 + RNAfold 联合请求
- RNA 三级结构预测请求
- GEMORNA 设计 + RhoFold 联合请求

---

## 14. 当前已知风险与限制

### 14.1 Router / Specialist / Critic 目前是规则模式

优点：

- 稳定
- 可控
- 易调试

缺点：

- 灵活性不如 LLM
- 复杂自然语言理解能力有限

### 14.2 `mock_codon_optimization` 仍然是假的

当前 mRNA 分支里：

- `predict_rna_secondary_structure` 已是真实 ViennaRNA
- `design_mrna_cds_with_gemorna` 已是真实 GEMORNA 接入
- 但 `mock_codon_optimization` 仍是模拟工具

后续可以替换成真实密码子优化工具。

### 14.3 GEMORNA 输出解析仍可继续增强

当前是通过解析 `stdout` 抽取生成序列。  
如果后续发现输出格式变化，建议把解析逻辑改得更稳：

- 返回多候选
- 明确打分
- 明确输出文件

### 14.4 `GEMORNA` 的二进制 `.so` 对 Python 版本敏感

必须优先保证：

- Linux
- Python 3.10

否则可能出现 ABI 兼容性报错。

### 14.5 `RhoFold` 当前默认只接了单序列模式

当前已经接通的是：

- `single_seq_pred=true`

这意味着：

- 结构预测已经可用
- 但还没有把本地 MSA 数据库模式纳入主项目标准部署流程

后续如果要追求更高精度，可再扩展：

- 用户显式提供 `.a3m`
- 或服务器侧本地建库

### 14.6 前端当前仍然比较轻量

当前 `frontend/app.py` 主要是一个最小可用调试界面：

- 展示节点执行进度
- 展示简化后的 `final_report`

它暂时还不是一个产品级 UI，因此：

- 结果展示较粗糙
- 大结果文件的可视化仍有增强空间
- 更适合作为当前接入阶段的调试入口

### 14.7 `RhoFold` 首次运行可能需要网络访问

虽然推荐手动放好 checkpoint，但 `RhoFold` 运行时仍可能因为上游实现而访问 Hugging Face 拉取附属文件。

因此：

- 首次运行建议保证服务器网络可访问相关源
- 或后续在服务器上做好本地缓存

---

## 15. 后续最推荐的发展路线

建议按下面顺序继续推进：

1. 先把工具链接全，优先真实工具替换 mock 工具
2. 保持规则模式，先把每个工具独立跑通
3. 先在 Agent 层把 `RhoFold` 的一句话调用链路稳定下来
4. 等工具生态稳定后，再恢复可配置的 LLM 模式
5. 再逐步引入：
   - 更细的 specialist
   - 更强的 critic
   - 结果排序 / 候选集筛选
   - 多工具串联规划
6. 后续再考虑：
   - 用真实密码子优化工具替换 `mock_codon_optimization`
   - 为 `RhoFold` 增加可选的 MSA 模式
   - 优化前端结果展示与文件下载体验

---

## 16. 一句话总结

当前这个项目的核心设计可以概括为：

**上层 Agent 只负责规则路由与工作流编排，下层所有复杂生信能力都通过 `Conda + FastAPI` 微服务隔离运行，长序列统一走 `workspace filepath` 传递，第三方源码通过 `external_repos/` 的 submodule 方式独立管理。**

以后新增工具时，统一按下面的固定动作做：

1. 放到 `external_repos/`
2. 建 `microservices/<tool>_service/`
3. 在 `agent_core/tools.py` 封装 HTTP 工具
4. 在 `nodes.py` 接 specialist
5. 先测原始命令，再测微服务，再测 Agent
6. 如果仓库里有 submodule 和运行时输出，不要默认 `git add .`

