# Evitar Integration Guide

## 1. What was added

- Upstream location prepared: `rna_agent_system/external_repos/Evitar` (as submodule).
- New microservice: `rna_agent_system/microservices/evitar_service/`
  - `main.py`
  - `environment.yml`
  - `start.sh`
- New agent tool: `design_sirna_with_evitar(...)` in `agent_core/tools.py`.
- Rule routing updates in `agent_core/nodes.py`:
  - detects `evitar`, `predesign`, `cas13`, `rnaxs`, `predsi`
  - routes to `sirna_specialist`
  - dispatches Evitar tool call

Default service endpoint: `http://127.0.0.1:8016/design`.

## 2. Linux server setup

Your server project path:

`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`

Run on server:

```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent
git pull
git submodule update --init --recursive
```

If `external_repos/Evitar` does not contain `Evitar.pl`, replace it with the official upstream:

```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/external_repos
rm -rf Evitar
git clone https://github.com/dingyaozhang/Evitar.git Evitar
```

## 3. Start the Evitar microservice

```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/microservices/evitar_service
conda env create -f environment.yml
conda activate evitar_service_env
bash start.sh
```

Important runtime note:

- Evitar upstream `bin/` contains Linux executables.
- On macOS, you may see `cannot execute binary file`; this is expected.
- Final validation should be done on your Linux server.

Health check:

```bash
curl http://127.0.0.1:8016/health
```

Expected key fields:

- `status=ok` (only when Linux runtime + `perl` + required Evitar binaries are executable)
- `linux_runtime=true`
- `evitar_script_exists=true`
- `binaries.*.exists=true` and `binaries.*.executable=true`

## 4. Direct API example

Existing-virus mode:

```bash
curl -X POST http://127.0.0.1:8016/design \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "rna_agent_system/external_repos/Evitar/test/genome.fa",
    "strains_path": "rna_agent_system/external_repos/Evitar/test/strains.fa",
    "mode": "existing",
    "predict": "predsi",
    "ncores": 1
  }'
```

If `/design` returns 500 with a message containing `cannot execute binary file`, check:

1. Service is running on Linux (not macOS).
2. `external_repos/Evitar/bin/*` keeps executable permission.
3. `EVITAR_ROOT` points to the correct Evitar checkout when using a custom path.

Predesign (future-virus) mode:

```bash
curl -X POST http://127.0.0.1:8016/design \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "rna_agent_system/external_repos/Evitar/test/exist_viruses.fa",
    "mode": "predesign",
    "predict": "predsi",
    "ncores": 1
  }'
```

## 5. Agent prompt examples

- `请用 Evitar 做 future virus predesign，输入文件 rna_agent_system/external_repos/Evitar/test/exist_viruses.fa`
- `用 Evitar 设计已有病毒 siRNA，input=.../genome.fa strains=.../strains.fa`
- `用 Evitar 的 rnaxs 模式设计，input=... strains=...`
- `请用 Evitar 走 Cas13，input=... strains=...`
