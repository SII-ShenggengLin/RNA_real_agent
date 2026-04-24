# `design_sirna_with_evitar`

> **接口冻结声明 (v0.2.0)** —— 禁止单方面变更
>
> 关联文件清单（修改时必须全部同步）：
> - `microservices/evitar_service/main.py`
> - `agent_core/tools.py`
> - `agent_core/tool_specs.py`
> - `agent_core/state.py`
> - `agent_core/nodes.py`
> - `docs/tools/design_sirna_with_evitar.md` ← 本文件
>
> 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。本次修改的基准日期：2026-04-24。

## 工具身份

- **name**: `design_sirna_with_evitar`
- **version（本仓库微服务）**: `0.2.0`
- **source**: `https://github.com/dingyaozhang/Evitar`
- **type**: HTTP microservice wrapper
- **default endpoint**: `http://127.0.0.1:8016/design`

## 能力边界

- **capabilities**
  - 通过 Evitar CLI 包装做 siRNA/Cas13 guide 设计，返回候选列表与输出文件
  - 支持 existing-virus 模式（单病毒/多株系覆盖）和 future-virus predesign 模式
  - 支持 off-target 分析（需转录组 / 3'UTR / 组织特异性权重文件）
  - 支持 GC 含量过滤、allow/ban 列表、SGAR/greedy 选择算法
- **limitations**
  - 上游 `bin/` 为 Linux 可执行文件（macOS 无法闭环）
  - **CRISPR 模式 (`--predict CRISPR`) 需要服务器安装 R (>=3.4) 运行时；缺少 `Rscript` 时会报错**
  - off-target 分析需要用户自行提供转录组 FASTA 和 3'UTR FASTA（未随仓库捆绑）
  - 真实的组织特异性 off-target 权重文件已在 `Evitar/GenomeData/weightedgene/` 下捆绑

## 部署依赖

| 依赖 | 必需 | 说明 |
|---|---|---|
| Linux | ✅ | `bin/` 下均为 Linux ELF 可执行文件 |
| Perl 5 | ✅ | Evitar.pl 本身需要 Perl |
| ViennaRNA | ✅ | `RNAfold` / `RNAplfold` / `RNAduplex` 已捆绑在 `Evitar/bin/` |
| MUSCLE | ✅ | 已捆绑在 `Evitar/bin/`（predesign 模式使用） |
| R (>=3.4) | ⚠️ | **仅 CRISPR 模式需要**，siRNA 模式不需要 |
| 人类转录组 FASTA | ⚠️ | **仅 off-target 分析需要**。运行 `GenomeData/GenomeData.sh` 自动生成 `transcripts.fa` 和 `utrs.fa` |
| 组织权重文件 | ✅ | `GenomeData/weightedgene/*.txt` 已捆绑（如 `Lung.txt`） |

## 输入 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tools.py:EvitarDesignInput`
- **核心字段**
  - `filepath`（必填）：输入 FASTA
  - `mode`（默认 `existing`）：`existing` / `predesign`
  - `predict`（默认 `predsi`）：`predsi` / `rnaxs` / `CRISPR` / `multifapredsi`
  - `strains_path`（可选）：existing-virus 模式下用于跨株系覆盖
  - `off_target`（默认 false）：启用脱靶分析
  - `ncores`（默认 1）：线程数
- **Off-target 分析文件**
  - `p3utr_path`：3'UTR FASTA
  - `transcriptome_path`：转录组 FASTA
  - `weight_path`：基因权重文件（三列：ENSEMBL ID, Gene Symbol, weight）
- **Predesign 模式参数**
  - `sumtype`：`SGAR`（上游默认）或 `greedy`
  - `limitnum`：输出 siRNA/gRNA 数量上限（上游默认 50）
  - `repeatnum`：Multi-siRNA 惩罚因子（上游默认 2）
- **脱靶阈值**
  - `pmcuff`：perfect-match cutoff（上游默认 1）
  - `umcuff`：imperfect-match score cutoff（上游默认 20）
  - `mircuff`：miRNA-like score cutoff（上游默认 20000）
- **GC 含量过滤**
  - `maxgc`（上游默认 0.6）、`mingc`（上游默认 0.25）、`middlegc`（上游默认 0.55）
- **Allow / Ban 列表**
  - `allow_path`：实验验证的 siRNA 列表（每行一个序列，无表头）
  - `ban_path`：要排除的 siRNA 列表（每行一个序列，无表头）

## 输出 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tool_specs.py:EvitarDesignOutput`
- **关键字段**
  - `output_filepath`：结果文件（尽量复制到 `workspace/`）
  - `result_count` / `top_results`
  - `command`：服务端执行命令（用于审计）
  - 所有传入的上游参数都会回显到输出中，便于状态追踪

## 失败模式

- **工具不可用**：8016 服务未启动/超时/非 2xx
- **参数错误**：服务端校验失败（Pydantic）
- **外部依赖缺失**：Evitar 上游依赖/数据库缺失时服务端返回错误
- **文件不存在**：off-target 或 allow/ban 指定的文件不存在时返回 400

