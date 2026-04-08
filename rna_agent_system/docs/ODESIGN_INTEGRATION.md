# ODesign Integration Notes

## What Was Added

`ODesign` has been added to `rna_agent_system/external_repos/ODesign` as a git submodule.

This repo now also includes:

- `microservices/odesign_service/`
- `agent_core.tools.run_odesign_inference()`
- rule-based routing for explicit `ODesign` requests

Current Agent-side support is intentionally conservative:

- explicit ODesign JSON input via filepath
- simple RNA backbone generation via natural language length request
- protein-binding RNA generation from natural language plus structure file

Other complex ODesign tasks should currently still be prepared as an input JSON file first, then passed to the Agent or microservice.

## Why ODesign Is Usable Here

For this project, ODesign is a **server-side tool**, not a macOS local tool.

That fits the current repository architecture:

- macOS machine: edit code and push to GitHub
- Linux GPU server: install environments, download checkpoints/data, run microservices

ODesign itself is suitable for this workflow because:

- upstream officially targets `python=3.10`
- upstream inference depends on CUDA 12.1
- it supports RNA design with `odesign_base_na_rigid`
- it already works from a JSON-spec input, which matches the project's filepath-first design style

## Required Server Assets

Before starting `odesign_service` on Linux, prepare:

- `external_repos/ODesign/ckpt/odesign_base_na_rigid.pt`
- `external_repos/ODesign/ckpt/oinvfold_rna.ckpt`
- `external_repos/ODesign/data/components.v20240608.cif`
- `external_repos/ODesign/data/components.v20240608.cif.rdkit_mol.pkl`

The service checks for these files before running inference.

For upstream downloads:

- model checkpoints: `https://huggingface.co/The-Institute-for-AI-Molecular-Design/ODesign`
- inverse-folding checkpoints: `https://huggingface.co/The-Institute-for-AI-Molecular-Design/OInvFold/tree/main`
- inference data files: upstream Google Drive link documented in `external_repos/ODesign/README.md`

## Environment Setup

From `rna_agent_system/microservices/odesign_service/`:

```bash
conda env create -f environment.yml
conda activate odesign_service_env
pip install -r ../../external_repos/ODesign/requirements.txt \
  -f https://data.pyg.org/whl/torch-2.3.1+cu121.html
bash start.sh
```

Default service port:

- `8012`

## Microservice API

### Health Check

`GET /health`

Returns whether:

- the upstream repo exists
- default checkpoint/data paths exist
- CUDA is available

### Inference Endpoint

`POST /design/from-json`

Main request fields:

- `input_json_path`
- `infer_model_name`
- `design_modality`
- `exp_name`
- `seeds_json`
- `n_sample`
- `use_msa`

The response includes:

- output directory
- generated `*.cif` prediction files
- `run.log`
- error files when present

## Current Agent Usage

### 1. JSON-driven ODesign request

Example style:

```text
请用 ODesign 跑这个 JSON:
rna_agent_system/workspace/odesign_input_xxx.json
```

### 2. Simple RNA backbone request

Example style:

```text
请用 ODesign 设计一个 50 nt 的 RNA backbone
```

The rule-based node will automatically create a minimal ODesign JSON file in `workspace/` and submit it to `odesign_service`.

### 3. Protein-binding RNA request

Example style:

```text
请用 ODesign 做 protein-binding RNA 设计，
ref_file=/absolute/path/to/target.cif
hotspot=C/18,C/90,C/79,C/49
length=61
```

You may also provide:

- `protein_chain=C`
- `protein_segment=C/1-96`
- `sample_name=my_case`

If `protein_segment` is omitted, the rule-based node will try to infer it from the reference structure file automatically.

## Current Limitation

The Agent still does **not** try to auto-assemble every ODesign task from free-form natural language.

For unsupported tasks, the recommended workflow is:

1. prepare the upstream ODesign JSON explicitly
2. store it in `workspace/` or another repo path
3. ask the Agent to run ODesign using that JSON filepath
