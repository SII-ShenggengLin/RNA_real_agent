# `design_sgrna_handle_with_crgpt` / `score_sgrna_handle_with_crgpt`

> **INTERFACE LOCK (v0.3.0)**: 本工具的接口已被锁定。任何字段增删、函数签名变动、
> 返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：
> - `microservices/sgrna_design_service/main.py`
> - `agent_core/tools.py`
> - `agent_core/tool_specs.py`
> - `agent_core/state.py`
> - `agent_core/nodes.py`
> - `docs/tools/design_sgrna_handle_with_crgpt.md` ← 本文件
>
> 违反此规则的提交将被回退。基准日期：2026-04-24。

- **source**: `https://github.com/bitguolab/sgrna_design`
- **design endpoint**: `http://127.0.0.1:8017/design`
- **score endpoint**: `http://127.0.0.1:8017/score`
- **design input schema**: `rna_agent_system/agent_core/tools.py:SgRNADesignInput`
- **design output schema**: `rna_agent_system/agent_core/tool_specs.py:SgRNADesignOutput`
- **score input schema**: `rna_agent_system/agent_core/tools.py:SgRNADesignScoreInput`
- **score output schema**: `rna_agent_system/agent_core/tool_specs.py:SgRNADesignScoreOutput`

## 能力边界

- **capabilities**：
  - `design_sgrna_handle_with_crgpt`: 从 seed/handle 序列生成候选 handle，并给出 best candidate 与输出文件
  - `score_sgrna_handle_with_crgpt`: 对单个 sgRNA handle 序列进行评分（nn_score + log_likelihood + structure metrics）
- **limitations**：依赖模型权重与 torch 运行时限制；MCMC 模式需要 ViennaRNA；评分端点需要模型已加载

