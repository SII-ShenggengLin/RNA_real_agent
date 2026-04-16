# `run_blastn_similarity_search`

## 工具身份

- **name**: `run_blastn_similarity_search`
- **version（本仓库微服务）**: `0.1.0`
- **source**: `https://blast.ncbi.nlm.nih.gov/Blast.cgi`
- **type**: HTTP microservice wrapper
- **default endpoint**: `http://127.0.0.1:8019/blastn`

## 能力边界

- **capabilities**
  - 对 query 序列执行 `blastn`，subject 可为“现场 makeblastdb 的 FASTA”或“已有 BLAST DB 前缀”
  - 返回 hit 计数、预览、tabular 输出（写入 `workspace/`）
- **limitations**
  - 这是通用相似性搜索工具，不等同于“siRNA 脱靶生产评估 pipeline”
  - subject 数据质量/范围由调用方保证

## 输入 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tools.py:BlastnSearchInput`
- **互斥字段**
  - `subject_fasta_path` 与 `subject_db` **必须二选一**

## 输出 schema（严格）

- **代码定义**: `rna_agent_system/agent_core/tool_specs.py:BlastnSearchOutput`
- **关键字段**
  - `hit_count`
  - `tabular_tsv_filepath`（`workspace/blastn_out_*.tsv` 或空字符串）
  - `blastn_command` / `makeblastdb_command`（用于审计）

## 失败模式

- **参数错误**：subject 参数不满足二选一 → wrapper 直接 `ValueError`
- **工具不可用**：8019 服务或服务器 BLAST+ 不可用
- **空结果**：`hit_count=0`，tabular 可能为空

