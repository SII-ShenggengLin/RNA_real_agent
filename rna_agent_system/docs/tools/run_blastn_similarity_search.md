# BLAST+ blastn 接口契约文档

> **INTERFACE LOCK (v0.2.0)** — 本文件为 BLAST+ 工具的**权威接口定义**。  
> 任何字段的增删改都必须同步修改以下六个位置，否则会导致 Agent 层、微服务层和 ToolSpec 注册层不一致。

## 同步清单

修改前必须同步检查并更新：

1. **`microservices/blast_service/main.py`**
   - `BlastnRequest` / `BlastnResponse` Pydantic 模型
   - `run_blastn` 核心计算函数
   - `_resolve_host_path` 路径解析逻辑
   - FastAPI `/blastn` endpoint

2. **`agent_core/tools.py`**
   - `BlastnSearchInput` Pydantic 输入模型
   - `run_blastn_similarity_search` `@tool` 包装函数返回值字典键名

3. **`agent_core/tool_specs.py`**
   - `BlastnSearchOutput` Pydantic 输出模型
   - `run_blastn_similarity_search` ToolSpec 注册项

4. **`agent_core/state.py`**
   - BLAST+ 相关 state 字段（`blast_hit_count`、`blast_tabular_tsv_filepath`、`blast_subject_mode`、`blast_hits_preview`、`blast_preview_truncated`、`blast_blastn_command`、`blast_resolved_query_path`、`blast_resolved_subject`）

5. **`agent_core/nodes.py`**
   - `_needs_blast_search` 路由判断
   - `_build_blast_tool_args` 参数解析逻辑
   - `_extract_blast_path_token` 辅助函数
   - `tool_execution_node` 中 BLAST 结果回写逻辑
   - `critic_node` 中 BLAST 字段的 summary 输出

6. **本文档**（`docs/tools/run_blastn_similarity_search.md`）

---

## 微服务架构

| 属性 | 值 |
|------|-----|
| 服务目录 | `microservices/blast_service/` |
| 启动脚本 | `start.sh`（conda 环境 `blast_service_env`，端口 8019） |
| 上游仓库 | [NCBI BLAST+](https://blast.ncbi.nlm.nih.gov/Blast.cgi) |
| 安装方式 | `conda env create -f environment.yml`（bioconda `blast` 2.17.0+） |
| 计算设备 | **纯 CPU**（BLAST+ 是序列比对算法，不使用 GPU） |

---

## 端点一览

| # | Endpoint | 方法 | 说明 |
|---|----------|------|------|
| 1 | `/health` | GET | 检查 blastn / makeblastdb 是否可执行 |
| 2 | `/blastn` | POST | 执行 blastn 比对，返回比对结果与元数据 |

---

## 输入模型（`BlastnSearchInput` / `BlastnRequest`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `filepath` / `query_filepath` | `str` | **必填** | 查询序列文件路径（workspace 相对路径或绝对路径） |
| `subject_fasta_path` | `Optional[str]` | `None` | 目标 multi-FASTA 文件路径（与 `subject_db` 二选一） |
| `subject_db` | `Optional[str]` | `None` | 已有 BLAST 核苷酸数据库前缀路径（与 `subject_fasta_path` 二选一） |
| `task` | `str` | `"blastn-short"` | blastn 任务模式：`blastn-short` / `blastn` / `megablast` / `dc-megablast` |
| `evalue` | `float` | `10.0` | Expect value 阈值 |
| `word_size` | `Optional[int]` | `None` | 可选 word size（短查询手动调优建议） |
| `max_target_seqs` | `int` | `50` | 最大比对目标序列数 |
| `perc_identity` | `Optional[float]` | `None` | 最小百分比一致性过滤 |
| `strand` | `str` | `"both"` | 链方向：`both` / `plus` / `minus` |
| `outfmt` | `Optional[str]` | `None` | 可选 blastn `-outfmt` 覆盖（默认 tabular format 6） |
| `service_url` | `str` | `"http://127.0.0.1:8019/blastn"` | 微服务 POST 端点 URL |

**约束**：`subject_fasta_path` 与 `subject_db` 必须且只能提供其一。

---

## 输出模型（`BlastnSearchOutput` / `BlastnResponse`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `hit_count` | `int` | 比对命中数 |
| `hits_preview` | `str` | 前 30 行比对结果预览 |
| `preview_truncated` | `bool` | 预览是否被截断 |
| `tabular_output_truncated` | `bool` | 完整 tabular 输出是否被截断（>500KB 时截断） |
| `blastn_command` | `str` | 实际执行的 blastn 命令行 |
| `makeblastdb_command` | `Optional[str]` | 实际执行的 makeblastdb 命令行（`subject_db` 模式时为 `null`） |
| `stderr` | `str` | blastn / makeblastdb 的 stderr 输出（截取前 4000 字符） |
| `subject_mode` | `str` | `"fasta"` 或 `"db"` |
| `resolved_query_path` | `str` | 解析后的查询文件绝对路径 |
| `resolved_subject` | `str` | 解析后的目标文件/数据库绝对路径 |
| `model` | `str` | 固定为 `"ncbi-blastn"` |
| `query_filepath` | `str` | 原始传入的查询文件路径（相对路径） |
| `tabular_tsv_filepath` | `str` | 保存到 workspace 的完整 tabular 结果 TSV 文件路径 |

---

## 路径解析策略

`_resolve_host_path` 的解析顺序：

1. 去除首尾引号 `"` / `'`
2. 如果是**绝对路径**，直接 `resolve()`
3. 如果以 `rna_agent_system/` 开头，自动去除该冗余前缀
4. 拼接 `RNA_AGENT_SYSTEM_ROOT / text` 并 `resolve()`
5. 如果 `candidate.exists()` 或 `candidate.parent.exists()`，返回 `candidate`
6. 否则回退到 `Path(text).resolve()`（当前工作目录下的相对路径）

**注意**：BLAST DB 前缀不是一个单一文件，因此第 5 步使用 `candidate.parent.exists()` 来保证数据库路径正确解析。

---

## 示例

### 示例 1：使用 subject FASTA

```bash
curl -sS -X POST http://127.0.0.1:8019/blastn \
  -H 'Content-Type: application/json' \
  -d '{
    "query_filepath": "workspace/blast_test_query.fa",
    "subject_fasta_path": "workspace/blast_test_subject.fa",
    "task": "blastn-short",
    "evalue": 10
  }'
```

### 示例 2：使用已有 BLAST 数据库

```bash
curl -sS -X POST http://127.0.0.1:8019/blastn \
  -H 'Content-Type: application/json' \
  -d '{
    "query_filepath": "workspace/blast_test_query.fa",
    "subject_db": "workspace/blast_test_subject_db",
    "task": "blastn-short",
    "evalue": 10
  }'
```

### 示例 3：自定义输出格式

```bash
curl -sS -X POST http://127.0.0.1:8019/blastn \
  -H 'Content-Type: application/json' \
  -d '{
    "query_filepath": "workspace/blast_test_query.fa",
    "subject_fasta_path": "workspace/blast_test_subject.fa",
    "task": "blastn-short",
    "outfmt": "6 qseqid sseqid length pident"
  }'
```

---

## 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v0.2.0 | 2026-04-25 | 接口完整重构：补全输出模型 13 个字段、暴露 `outfmt`、新增 5 个 state 字段、添加 INTERFACE LOCK、修复 `subject_db` 路径解析 bug、删除遗留 `off_target_blast` 目录 |
| v0.1.0 | — | 初始实现（状态为 `partial`，输出模型不完整） |
