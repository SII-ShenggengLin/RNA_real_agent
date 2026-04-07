# GerNA-Bind Integration Notes

## Current status

`GerNA-Bind` has been cloned into:

```text
rna_agent_system/external_repos/GerNA-Bind
```

Static review shows the upstream repo is promising for RNA-ligand scoring, but it is not directly production-ready inside this project without a wrapper layer.

## What was added

A project-local microservice scaffold now exists at:

```text
rna_agent_system/microservices/gernabind_service/
```

It provides:

- `GET /health`
- `POST /score`
- `POST /predict-binding-site`

The Agent layer was also updated so that requests explicitly mentioning `GerNA-Bind` or `gernabind` can route to the new scoring tool.

## Why a wrapper is needed

The upstream repository has several issues that make direct Agent invocation fragile:

- `train_model.py` and `test_model.py` contain hard-coded dataset paths under `/data/...`
- `inference_affinity.py` expects `Model/Robin_Model_baseline.pth`, but the upstream download script provides `Model/Robin_random.pth`
- `inference_binding_site.py` expects `Model/Hariboss_Model_baseline.pth`, but that weight is not downloaded by `Model/get_weights.sh`
- preprocessing depends on RNA 2D + 3D features, so this tool is heavier than `RNAsmol`

## Integration approach

The wrapper does not modify the upstream repo.

Instead it:

1. imports GerNA-Bind model code from `external_repos/GerNA-Bind`
2. computes RNA-FM embeddings locally
3. runs `RNAfold` locally for 2D structure if needed
4. asks the existing `rhofold_service` for a PDB if the caller did not provide one
5. loads GerNA-Bind checkpoints and returns structured JSON

This keeps the project aligned with the main architecture:

- upstream code in `external_repos/`
- serving logic in `microservices/`
- Agent calls through HTTP only

## Linux deployment checklist

On the Linux server:

1. create the GerNA-Bind service environment from `microservices/gernabind_service/environment.yml`
2. install matching PyG wheels if the base environment is not enough
3. download affinity checkpoints with:

```bash
bash rna_agent_system/external_repos/GerNA-Bind/Model/get_weights.sh
```

4. make sure `rhofold_service` is already running
5. start:

```bash
bash rna_agent_system/microservices/gernabind_service/start.sh
```

## Known limitation

The binding-site endpoint is scaffolded, but it still depends on a binding-site checkpoint such as:

```text
rna_agent_system/external_repos/GerNA-Bind/Model/Hariboss_Model_baseline.pth
```

That file is referenced by the upstream repo, but is not fetched by the included weight download script.
