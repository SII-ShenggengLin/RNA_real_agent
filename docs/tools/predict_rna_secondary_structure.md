# `predict_rna_secondary_structure`

## 工具身份

- **name**: `predict_rna_secondary_structure`
- **version（本仓库微服务）**: `0.2.0-port8003`
- **source**: `https://github.com/ViennaRNA/ViennaRNA`
- **type**: HTTP microservice wrapper
- **default endpoint**: `http://127.0.0.1:8003/fold`

## 能力边界

- **capabilities**
  - 对单条 RNA 序列预测二级结构与 MFE（热力学模型）
- **limitations**
  - 不做序列设计/优化
  - 不保证对超长序列的性能；限制由服务端实现决定

## 输入 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tools.py:MrnaToolInput`
- **核心字段**
  - `filepath`：RNA 序列文件
  - `service_url`：可覆盖 endpoint

## 输出 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tool_specs.py:ViennaFoldOutput`
- **关键字段**
  - `structure`（dot-bracket）
  - `mfe_kcal_per_mol`（kcal/mol；越小越稳定）
  - `backend`（RNAlib / RNAfold-cli）

## 失败模式

- **工具不可用**：8003 服务未启动/超时/非 2xx
- **非法序列**：服务端拒绝或返回缺字段

