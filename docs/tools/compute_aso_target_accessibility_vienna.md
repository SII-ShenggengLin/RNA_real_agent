# `compute_aso_target_accessibility_vienna`

- **source**: `https://github.com/ViennaRNA/ViennaRNA`
- **endpoint**: `http://127.0.0.1:8003/aso-accessibility`
- **input schema**: `rna_agent_system/agent_core/tools.py:AsoAccessibilityViennaInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:ViennaAsoAccessibilityOutput`

## 能力边界

- **capabilities**：用 RNAplfold 估计目标 RNA 指定区间的可及性（unpaired 概率摘要）
- **limitations**：需要足够长的目标上下文；结果为模型估计，不等同实验可及性

