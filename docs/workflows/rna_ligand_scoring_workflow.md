# 工作流：`rna_ligand_scoring`

## 基础链（最稳）

- **Step 1 输入校验**：RNA 文件可读；SMILES 非空
- **Step 2 预处理**：无（由服务端/模型处理）
- **Step 3 候选生成**：无
- **Step 4 评估**：二选一或两者都跑
  - `score_rna_ligand_binding_with_rnasmol`
  - `score_rna_ligand_binding_with_gernabind`
- **Step 5 过滤**：可按 `probability` 阈值
- **Step 6 排序**：按 `probability` 降序（越高越可能为正类）
- **Step 7 格式化**：输出概率/标签与模型信息

