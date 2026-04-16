# `compute_sirna_duplex_binding_vienna`

## 工具身份

- **name**: `compute_sirna_duplex_binding_vienna`
- **version（本仓库微服务）**: `0.2.0-port8003`
- **source**: `https://github.com/ViennaRNA/ViennaRNA`
- **type**: HTTP microservice wrapper
- **default endpoint**: `http://127.0.0.1:8003/sirna-duplex`

## 能力边界

- **capabilities**
  - 计算一对 sense/antisense 链的 duplex 共折叠结构与 MFE（单位：kcal/mol）
- **limitations**
  - 不做 siRNA efficacy 预测
  - 不做基因组级 off-target 搜索
  - 输入必须提供两条链（见输入约束）

## 适用任务

- `sirna_duplex_energy`
- `rna_secondary_structure`

## 输入 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tools.py:SirnaDuplexViennaInput`
- **核心字段**
  - `filepath`（必填）：包含两条链的文件
    - 支持两条 FASTA 记录（第一条 = sense，第二条 = antisense）
    - 或两行纯序列（第一行 = sense，第二行 = antisense）
  - `service_url`（可选）：默认 `http://127.0.0.1:8003/sirna-duplex`

## 输出 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tool_specs.py:ViennaDuplexOutput`
- **关键字段**
  - `structure`：cofold dot-bracket（含 `&` 分隔）
  - `mfe_kcal_per_mol`：duplex MFE（越小越稳定）
  - `sense` / `antisense`
  - `backend` / `model`

## 失败模式

- **参数/输入错误**
  - duplex 文件少于两条链 / 解析失败 → wrapper 抛出 `ValueError`
- **工具不可用**
  - 8003 服务未启动/超时/非 2xx → wrapper 抛出 `ValueError`
- **空结果/字段缺失**
  - 响应缺 `mfe`/`structure` → wrapper 抛出 `ValueError`

## 执行约束

- 经验耗时：取决于 ViennaRNA 服务实现与序列长度（通常很快）
- 环境：需要 `microservices/viennarna_fold` 可运行

## agent 使用说明（不等同于工具能力）

- 常见位置：siRNA duplex/cofold 能量评估步骤
- 典型串联：
  - Step（候选已给定 sense/antisense）→ 本工具算 duplex 能量 → 作为过滤/排序指标之一

