#!/usr/bin/env python3
"""Resident-model ODesign inference service (2026-09-04, user-directed
throughput fix: keep the model weights on the GPU instead of paying the
~85-s subprocess load per request).

Mirrors ``scripts/inference.py`` exactly — same configs/inference.yaml exp
block, same checkpoint/invfold loading, same ``InferRunner.run()`` loop and
``seed_everything(deterministic=True)`` seeding — but builds the model ONCE
at startup and serves each request by rebinding ``input_json_path`` and the
per-request dataloader.  Requests are serialized behind a lock (torch
inference on one device); the per-request cost drops to the featurization
of the single input.

Requests arrive in the existing wrapper's payload shape (input_json_path,
n_sample, seeds, model overrides); responses carry the prediction cif
filepaths (service-managed unique dump dirs).
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

# ── locate the ODesign repo the same way the existing service does ──
HERE = Path(__file__).resolve().parent
ODESIGN_ROOT = HERE.parent.parent / "external_repos" / "ODesign"

import sys
sys.path.insert(0, str(ODESIGN_ROOT))   # inference.py appends project_dir;
# modules import as src.* from the repo root

import torch  # noqa: E402
from omegaconf import OmegaConf  # noqa: E402
from ml_collections import ConfigDict  # noqa: E402

app = FastAPI()

_STATE: dict = {}


class InferenceRequest(BaseModel):
    input_json_path: str
    n_sample: int = 1
    seeds: list[int] = Field(default_factory=lambda: [42])
    infer_model_name: str = "odesign_base_na_rigid"
    design_modality: str = "rna"
    use_msa: bool = False
    num_workers: int = 2
    invfold_topk: int = 1
    invfold_temp: float = 1.0
    invfold_use_beam: bool = True


class InferenceResponse(BaseModel):
    prediction_filepaths: list[str] = []
    prediction_count: int = 0
    error_filepaths: list[str] = []
    elapsed_seconds: float = 0.0
    output_dir: str = ""   # the tool contract requires both keys present
    model: str = "odesign-resident"


def _build_runner(model_name: str, design_modality: str):
    """One-time model + runner construction (the expensive part we keep
    resident): mirrors inference.py's main() minus hydra."""
    from src.data.dataloader import get_inference_dataloader  # noqa: F401
    from src.utils.inference.infer_runner import InferRunner
    from src.model.odesign import ODesign

    # exact hydra composition of the subprocess invocation — the exp group
    # itself has nested defaults (/model, /data, ...) that manual merging
    # cannot reproduce; compose() resolves the identical config tree.
    from hydra.experimental import initialize_config_dir, compose
    overrides = [
        f"exp=train_{model_name}",
        f"exp.infer_model_name={model_name}",
        f"exp.design_modality={design_modality}",
        "exp.input_json_path=/dev/null",      # rebound per request
        "exp.seeds=[42]",
        "exp.use_msa=false",
        "exp.num_workers=2",
        "exp.exp_name=resident",
        "exp.model.sample_diffusion.N_sample=1",  # rebound per request
        "exp.model.inference_noise_schedulers.coordinate.partial_diffusion.enable=false",
        "exp.model.inference_noise_schedulers.coordinate.partial_diffusion.snr=0.1",
        "exp.invfold_topk=1", "exp.invfold_temp=1.0", "exp.invfold_use_beam=true",
        f"data_root_dir={ODESIGN_ROOT / 'data'}",
        f"ckpt_root_dir={ODESIGN_ROOT / 'ckpt'}",
    ]
    with initialize_config_dir(config_dir=str(ODESIGN_ROOT / "configs")):
        OmegaConf.register_new_resolver("eval", eval, replace=True)
        cfg = compose(config_name="inference", overrides=overrides,
                      return_hydra_config=False)
        # resolve INSIDE the context: hydra restores the resolver registry
        # on exit, which would drop the custom eval resolver again
        exp = OmegaConf.to_container(cfg.exp, resolve=True)
    assert "N_cycle" in exp["model"], list(exp["model"].keys())
    configs = ConfigDict(exp)
    device = torch.device("cuda:0")
    torch.cuda.set_device(device)

    class _StubDumper:
        """Reuse DataDumper semantics via the real class per request."""
        pass

    from src.utils.inference.dumper import DataDumper  # noqa: F401

    # the checkpoint/invfold loaders read these env vars
    os.environ.setdefault(
        "CKPT_ROOT_DIR",
        str(ODESIGN_ROOT / "ckpt"))
    os.environ.setdefault(
        "DATA_ROOT_DIR",
        str(ODESIGN_ROOT / "data"))

    model = ODesign(configs).to(device)
    runner = InferRunner.__new__(InferRunner)  # bypass __init__ dl/ckpt side
    runner.configs = configs
    runner.dump_dir = None
    runner.error_dir = None
    runner.device = device
    runner.infer_dl = None
    runner.model = model
    runner.dumper = None
    runner.load_checkpoint()
    runner.load_invfold_module()
    return runner, configs, device


@app.on_event("startup")
def _startup() -> None:
    from src.utils.train.distributed import DIST_WRAPPER  # world size 1
    assert DIST_WRAPPER.world_size == 1
    t0 = time.time()
    runner, configs, device = _build_runner(
        os.environ.get("ODESIGN_RESIDENT_MODEL", "odesign_base_na_rigid"),
        os.environ.get("ODESIGN_RESIDENT_MODALITY", "rna"),
    )
    _STATE.update(runner=runner, configs=configs, device=device,
                  lock=__import__("threading").Lock())
    print(f"[resident] model loaded on {device} in {time.time()-t0:.0f}s",
          flush=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok" if _STATE else "loading",
            "resident": True,
            "device": str(_STATE.get("device"))}


@app.post("/design/from-json", response_model=InferenceResponse)
def design_from_json(payload: InferenceRequest) -> InferenceResponse:
    if payload.design_modality not in {"rna", "dna", "protein", "ligand"}:
        return InferenceResponse(error_filepaths=[], prediction_count=0)
    t0 = time.time()
    with _STATE["lock"]:
        from src.data.dataloader import get_inference_dataloader
        from src.utils.inference.dumper import DataDumper

        # the tool passes project-root-relative paths; the original wrapper
        # resolved them from the repo root, we run from the service dir
        json_path = Path(payload.input_json_path)
        if not json_path.is_file():
            json_path = ODESIGN_ROOT.parent.parent / payload.input_json_path
        if not json_path.is_file():
            return InferenceResponse()
        payload.input_json_path = str(json_path)

        runner = _STATE["runner"]
        configs = _STATE["configs"]
        run_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        dump_dir = HERE / "resident_outputs" / run_id
        error_dir = dump_dir / "errors"
        dump_dir.mkdir(parents=True, exist_ok=True)
        error_dir.mkdir(parents=True, exist_ok=True)

        configs.input_json_path = payload.input_json_path
        configs.seeds = list(payload.seeds)
        configs.use_msa = payload.use_msa
        configs.num_workers = payload.num_workers
        configs.model.sample_diffusion.N_sample = int(payload.n_sample)
        configs.invfold_topk = payload.invfold_topk
        configs.invfold_temp = payload.invfold_temp
        configs.invfold_use_beam = payload.invfold_use_beam
        configs.dump_dir = str(dump_dir)

        runner.dump_dir = str(dump_dir)
        runner.error_dir = str(error_dir)
        runner.dumper = DataDumper(base_dir=str(dump_dir))
        runner.infer_dl = get_inference_dataloader(configs=configs)
        runner.run()

        preds = sorted(str(p) for p in dump_dir.glob("**/predictions/*.cif"))
        errs = sorted(str(p) for p in error_dir.glob("*.txt"))
    return InferenceResponse(
        prediction_filepaths=preds,
        prediction_count=len(preds),
        error_filepaths=errs,
        elapsed_seconds=round(time.time() - t0, 1),
        output_dir=str(dump_dir),
    )
