# Agent Guidelines for RNA_real_agent

> **This file has been consolidated.**  
> All authoritative documentation now lives in `rna_agent_system/docs/`:
> - `README.md` — project overview, quick start, capability summary
> - `ARCHITECTURE.md` — architecture, core module APIs, five-layer design, routing strategy
> - `WORKFLOWS.md` — all domain workflows: pipelines, scoring formulas, critic design
> - `TOOLS.md` — per-tool specs, port registry, microservice deployment notes
> - `BMC_FRAMEWORK.md` — Bounded Multi-Module Coordination: Type-I/Type-II motivation and strategy
> - `INTERFACE_LOCKS.md` — Interface Lock Policy, canonical references, sync checklists
> - `DEPLOYMENT.md` — environment setup, testing recipes, curl examples
> - `CHANGELOG.md` — locked interface changes and major workflow introductions
> - `CONTRIBUTING.md` — coding standards, new-tool procedure, commit conventions

## Project Phase

The codebase uses a **five-layer architecture** with an **LLM-driven planner** at Layer 3:
- Layer 0: Tool wrappers, specs, registry, executor (`tools.py`, `tool_specs.py`, `tool_registry.py`, `tool_executor.py`, `tool_runtime.py`)
- Layer 1: `Capability` + `CapabilityRegistry` + declarative writebacks (`capabilities/`)
- Layer 2: `BaseDomainWorkflow` + 11 domain workflows including `FullLengthMrnaDesignWorkflow` and `RnaAptamerDesignWorkflow` with BMC (`workflows/`)
- Layer 3: `DeterministicRouter` + `LLMPlanner` + `ExecutionController` + `Critic` (`planning/`)
- Layer 4: `SessionMemory` + `WorkspaceManager` (in-memory, swappable)
- Layer 5: `AgentRunner` unified façade (CLI / FastAPI)

## LLM Configuration

Set the following environment variables (or add them to `rna_agent_system/.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API key (primary) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API endpoint |
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | `deepseek-v4-pro` (strong) or `deepseek-v4-flash` (fast) |
| `OPENAI_API_KEY` | — | OpenAI API key (optional) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (optional) |
| `DASHSCOPE_API_KEY` | — | Alibaba DashScope API key (optional) |
| `GOOGLE_API_KEY` | — | Google Gemini API key (optional) |

Switch provider via:
```python
from agent_core.planning.factory import build_planner
planner = build_planner(provider="openai", model="gpt-4")
```

The `.env` file is gitignored and safe for secrets.

## LLM Critic

Critic采用双重机制：**BaseLLMCritic**（LLM驱动的通用质量诊断，适用于8个工作流）和 **BMC Coordinator**（确定性规则协调器，专用于full-length mRNA和RNA aptamer设计）。

### 配有Critic的Workflow（8个）

| Workflow | Critic Class |
|----------|-------------|
| `mrna_cds_design` | `MrnaCdsDesignLLMCritic` |
| `sirna_design` | `SirnaDesignLLMCritic` |
| `sgrna_design` | `SgRnaDesignLLMCritic` |
| `rna_aptamer_design` | `RnaAptamerDesignLLMCritic` |
| `ires_prediction` | `IresPredictionLLMCritic` |
| `rna_secondary_structure_design` | `RnaSecondaryStructureDesignLLMCritic` |
| `rna_tertiary_structure_design` | `RnaTertiaryStructureDesignLLMCritic` |
| `full_length_mrna_design` | `FullLengthMrnaDesignLLMCritic` |

### 故意不配Critic的Workflow（3个）

| Workflow | 原因 |
|----------|------|
| `mrna_sequence_scoring` | 确定性评估任务，retry不会改善结果 |
| `aso_target_screening` | 确定性筛选任务，retry不会改善结果 |
| `rna_small_molecule_interaction` | 确定性预测任务，retry不会改善结果 |

### 配置

通过 `AgentRunner` 的 `llm_critic_enabled` 参数控制开关：

```python
runner = AgentRunner(
    planner=planner,
    executor=executor,
    llm_critic_enabled=True,  # 默认开启
)
```

### 降级机制

如果LLM API调用失败，Critic会自动降级为"不retry"，不会导致workflow崩溃。

## Interface Lock Policy (retained here for visibility)

This project uses **INTERFACE LOCK** comments to prevent accidental breaking changes to tool contracts.

**Do NOT modify any function signature, Pydantic field, return dict key, or state field** inside an INTERFACE LOCK block without updating **all** files listed in the lock comment and re-running the full test suite.

### Currently locked interfaces

| Tool / Module | Version | Lock reference |
|---------------|---------|----------------|
| `compute_rna_sequence_gc_content` | v0.1.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §3 |
| `compute_dot_bracket_unpaired_fraction` | v0.1.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §4 |
| `compute_rna_sequence_u_content` | v0.1.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §5 |
| `compute_cai_for_cds_sequence` | v0.1.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §6 |
| `run_blastn_similarity_search` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sirna_with_evitar` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `score_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| CRISOT suite (8 tools) | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_mrna_cds_with_lineardesign` | v0.2.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §7 |
| ViennaRNA suite | v0.4.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| LinearFold suite | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `MrnaCdsDesignWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §8 |
| `RnaSmallMoleculeInteractionWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §9 |
| `SirnaDesignWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §10 |
| `SgRnaDesignWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §11 |
| `AsoTargetScreeningWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §12 |
| `IresPredictionWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §13 |
| `FullLengthMrnaDesignWorkflow` | v2.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §14 |
| `RnaAptamerDesignWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §15 |
| `RnaSecondaryStructureDesignWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §16 |
| `RnaTertiaryStructureDesignWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §17 |
| `MrnaSequenceScoringWorkflow` | v1.0.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §18 |

## Microservice Runtime Dependencies

> Moved to [`rna_agent_system/docs/DEPLOYMENT.md`](rna_agent_system/docs/DEPLOYMENT.md) §4.

## Testing

Run the full agent-core test suite before committing:

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x --ignore=tests/integration -m "not integration"
```
