# 任务目录（按代码为准）

> 本目录只收录“本仓库代码可证实存在入口 + 非 mock 工具链”的任务。
>
> 任务定义的“支持状态”与 `ToolSpec.status` 一致：
> - `available`：代码链路闭合且不依赖特殊环境即可运行（以仓库默认假设为准）
> - `partial`：代码链路闭合，但依赖 Linux/GPU/权重/参考库等外部条件
> - `unavailable`：无实现或依赖不闭合
> - `mock`：返回伪造结果（不计入真实支持）

## 任务列表

### siRNA / antisense

- `sirna_duplex_energy` → `docs/tasks/sirna_duplex_energy.md`
- `sirna_design_evitar` → `docs/tasks/sirna_design_evitar.md`

### RNA 二级结构

- `rna_secondary_structure_viennarna` → `docs/tasks/rna_secondary_structure_viennarna.md`
- `rna_secondary_structure_linearfold` → `docs/tasks/rna_secondary_structure_linearfold.md`
- `aso_accessibility_viennarna` → `docs/tasks/aso_accessibility_viennarna.md`
- `inverse_folding_viennarna` → `docs/tasks/inverse_folding_viennarna.md`

### mRNA/CDS

- `cds_codon_metrics` → `docs/tasks/cds_codon_metrics.md`
- `protein_to_cds_design` → `docs/tasks/protein_to_cds_design.md`
- `mrna_stability_prediction` → `docs/tasks/mrna_stability_prediction.md`
- `ires_prediction` → `docs/tasks/ires_prediction.md`
- `blastn_similarity_search` → `docs/tasks/blastn_similarity_search.md`

### RNA 3D / design / ligand

- `rna_tertiary_structure_prediction` → `docs/tasks/rna_tertiary_structure_prediction.md`
- `rna_structure_to_sequence_design` → `docs/tasks/rna_structure_to_sequence_design.md`
- `rna_ligand_scoring` → `docs/tasks/rna_ligand_scoring.md`
- `odesign_inference` → `docs/tasks/odesign_inference.md`

### CRISPR

- `crispr_offtarget_scoring` → `docs/tasks/crispr_offtarget_scoring.md`
- `crispr_specificity_csv` → `docs/tasks/crispr_specificity_csv.md`
- `crispr_offtarget_search` → `docs/tasks/crispr_offtarget_search.md`
- `crispr_sgrna_optimization` → `docs/tasks/crispr_sgrna_optimization.md`
- `sgrna_handle_design` → `docs/tasks/sgrna_handle_design.md`

