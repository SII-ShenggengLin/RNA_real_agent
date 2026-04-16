# `design_sirna_with_evitar`

## 工具身份

- **name**: `design_sirna_with_evitar`
- **version（本仓库微服务）**: `0.1.0`
- **source**: `https://github.com/dingyaozhang/Evitar`
- **type**: HTTP microservice wrapper
- **default endpoint**: `http://127.0.0.1:8016/design`

## 能力边界

- **capabilities**
  - 通过 Evitar CLI 包装做 siRNA/Cas13 guide 设计，返回候选列表与输出文件
- **limitations**
  - 上游 `bin/` 为 Linux 可执行文件（macOS 无法闭环）
  - 不提供“siRNA efficacy 预测/脱靶评估”的生产级实现（只返回 Evitar 产物）

## 输入 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tools.py:EvitarDesignInput`
- **核心字段**
  - `filepath`（必填）：输入 FASTA
  - `mode`（默认 `existing`）：`existing` / `predesign`
  - `predict`（默认 `predsi`）：`predsi` / `rnaxs` / `CRISPR`
  - `strains_path`（可选）：existing-virus 模式需要
  - `off_target`（默认 false）、`ncores`（默认 1）

## 输出 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tool_specs.py:EvitarDesignOutput`
- **关键字段**
  - `output_filepath`：结果文件（尽量复制到 `workspace/`）
  - `result_count` / `top_results`
  - `command`：服务端执行命令（用于审计）

## 失败模式

- **工具不可用**：8016 服务未启动/超时/非 2xx
- **参数错误**：服务端校验失败（Pydantic）
- **外部依赖缺失**：Evitar 上游依赖/数据库缺失时服务端返回错误

