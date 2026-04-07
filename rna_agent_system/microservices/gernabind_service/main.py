"""GerNA-Bind microservice for RNA-ligand affinity scoring and binding-site prediction."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Tuple

import fm
import numpy as np
import requests
import torch
from Bio.PDB import PDBParser
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rdkit import Chem
from rdkit.Chem import AllChem
from torch_geometric.data import Batch, Data

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GERNABIND_ROOT = PROJECT_ROOT / "external_repos" / "GerNA-Bind"
GERNABIND_MODEL_DIR = GERNABIND_ROOT / "Model"
DEFAULT_RHOFOLD_SERVICE_URL = os.environ.get("GERNABIND_RHOFOLD_URL", "http://127.0.0.1:8005/predict")

if str(GERNABIND_ROOT) not in sys.path:
    sys.path.insert(0, str(GERNABIND_ROOT))

import utils.features as fea  # noqa: E402
from net.model import GerNA  # noqa: E402
from utils.net_utils import get_mask, pack1D, pack2D  # noqa: E402

app = FastAPI(
    title="GerNA-Bind Service",
    description="Serve GerNA-Bind RNA-ligand affinity scoring and binding-site prediction.",
    version="0.1.0",
)

ATOM_ID = {
    "C": 1,
    "N": 2,
    "Br": 3,
    "O": 4,
    "S": 5,
    "Cl": 6,
    "F": 7,
    "P": 8,
    "I": 9,
    "As": 9,
    "K": 9,
    "Na": 9,
    "Ge": 9,
    "Se": 9,
    "Au": 9,
    "Pt": 9,
    "Sr": 9,
    "Mg": 9,
    "B": 9,
    "Co": 9,
    "Ca": 9,
    "Rh": 9,
    "unknown": 9,
}


class ScoreRequest(BaseModel):
    rna_sequence: str = Field(..., min_length=1, description="RNA sequence or FASTA-like text.")
    smiles: str = Field(..., min_length=1, description="Ligand SMILES string.")
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional GerNA-Bind affinity checkpoint path override.",
    )
    pdb_path: Optional[str] = Field(
        default=None,
        description="Optional precomputed RNA PDB path. When omitted the service asks RhoFold for one.",
    )
    secondary_structure: Optional[str] = Field(
        default=None,
        description="Optional dot-bracket RNA secondary structure. When omitted the service runs RNAfold.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device such as `cuda:0` or `cpu`.",
    )
    rhofold_service_url: Optional[str] = Field(
        default=None,
        description="Optional RhoFold service endpoint override.",
    )


class ScoreResponse(BaseModel):
    rna_sequence: str
    smiles: str
    probability_positive: float
    predicted_label: int
    raw_alpha: List[float]
    checkpoint_path: str
    preprocessing_pdb_path: str
    secondary_structure: str
    device: str
    model: str = "GerNA-Bind"


class BindingSiteRequest(BaseModel):
    rna_sequence: str = Field(..., min_length=1, description="RNA sequence or FASTA-like text.")
    smiles: str = Field(..., min_length=1, description="Ligand SMILES string.")
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional GerNA-Bind binding-site checkpoint path override.",
    )
    pdb_path: Optional[str] = Field(
        default=None,
        description="Optional precomputed RNA PDB path. When omitted the service asks RhoFold for one.",
    )
    secondary_structure: Optional[str] = Field(
        default=None,
        description="Optional dot-bracket RNA secondary structure. When omitted the service runs RNAfold.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device such as `cuda:0` or `cpu`.",
    )
    rhofold_service_url: Optional[str] = Field(
        default=None,
        description="Optional RhoFold service endpoint override.",
    )


class BindingSiteResponse(BaseModel):
    rna_sequence: str
    smiles: str
    per_residue_scores: List[float]
    checkpoint_path: str
    preprocessing_pdb_path: str
    secondary_structure: str
    device: str
    model: str = "GerNA-Bind-binding-site"


def _normalize_rna_sequence(raw_text: str) -> str:
    sequence_lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(sequence_lines).upper().replace("T", "U")
    sequence = re.sub(r"[^A-Z]", "", merged)
    if not sequence:
        raise HTTPException(status_code=400, detail="RNA sequence is empty after normalization.")
    return sequence


def _resolve_device(device_name: Optional[str]) -> torch.device:
    resolved_name = device_name or os.environ.get("GERNABIND_DEVICE", "").strip()
    if not resolved_name:
        resolved_name = "cuda:0" if torch.cuda.is_available() else "cpu"
    if resolved_name.startswith("cuda") and not torch.cuda.is_available():
        raise HTTPException(
            status_code=503,
            detail=f"Requested device `{resolved_name}` but CUDA is not available.",
        )
    return torch.device(resolved_name)


def _resolve_path(path_str: str) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / path_str


def _resolve_affinity_checkpoint(checkpoint_path: Optional[str] = None) -> Path:
    candidates: List[Path] = []
    if checkpoint_path:
        candidates.append(_resolve_path(checkpoint_path))

    env_path = os.environ.get("GERNABIND_AFFINITY_CHECKPOINT_PATH")
    if env_path:
        candidates.append(_resolve_path(env_path))

    candidates.extend(
        [
            GERNABIND_MODEL_DIR / "Robin_random.pth",
            GERNABIND_MODEL_DIR / "Biosensor_random.pth",
            GERNABIND_MODEL_DIR / "Robin_Model_baseline.pth",
        ]
    )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    raise HTTPException(
        status_code=503,
        detail=(
            "No GerNA-Bind affinity checkpoint was found. "
            "Run `bash rna_agent_system/external_repos/GerNA-Bind/Model/get_weights.sh` on the Linux server "
            "or set `GERNABIND_AFFINITY_CHECKPOINT_PATH`."
        ),
    )


def _resolve_binding_checkpoint(checkpoint_path: Optional[str] = None) -> Path:
    candidates: List[Path] = []
    if checkpoint_path:
        candidates.append(_resolve_path(checkpoint_path))

    env_path = os.environ.get("GERNABIND_BINDING_SITE_CHECKPOINT_PATH")
    if env_path:
        candidates.append(_resolve_path(env_path))

    candidates.append(GERNABIND_MODEL_DIR / "Hariboss_Model_baseline.pth")

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    raise HTTPException(
        status_code=503,
        detail=(
            "No GerNA-Bind binding-site checkpoint was found. "
            "The upstream repo references `Model/Hariboss_Model_baseline.pth`, so place that file on the Linux "
            "server or set `GERNABIND_BINDING_SITE_CHECKPOINT_PATH`."
        ),
    )


@lru_cache(maxsize=1)
def _load_rna_fm():
    model, alphabet = fm.pretrained.rna_fm_t12()
    model.eval()
    return model, alphabet


def _get_rna_embeddings(rna_sequence: str) -> torch.Tensor:
    model, alphabet = _load_rna_fm()
    batch_converter = alphabet.get_batch_converter()
    _, _, batch_tokens = batch_converter([("RNA", rna_sequence)])
    with torch.no_grad():
        results = model(batch_tokens, repr_layers=[12])
    return results["representations"][12][0][1:-1]


def _run_rnafold(fasta_path: Path) -> str:
    try:
        result = subprocess.run(
            ["RNAfold", "-i", str(fasta_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="`RNAfold` was not found. Install ViennaRNA in the GerNA-Bind service environment.",
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=503, detail=f"RNAfold failed: {exc.stderr.strip()}") from exc

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 3:
        raise HTTPException(status_code=503, detail="RNAfold output did not contain a secondary structure line.")
    return lines[2].split()[0]


def _extract_atom_coordinates(pdb_file: Path, atoms_to_extract: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    rna_atom_id = {atoms_to_extract[i]: i + 1 for i in range(len(atoms_to_extract))}
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("structure", str(pdb_file))

    coordinates_list = []
    atom_list = []
    for model in structure:
        for chain in model:
            for residue in chain:
                if residue.get_id()[0] == " ":
                    atoms = {atom.name: atom for atom in residue.get_atoms()}
                    coordinates = [
                        atoms[atom_name].get_coord()
                        for atom_name in atoms
                        if atom_name in atoms_to_extract
                    ]
                    atom_name_list = [
                        atoms[atom_name].name for atom_name in atoms if atom_name in atoms_to_extract
                    ]
                    atom_list.extend([rna_atom_id[name] for name in atom_name_list])
                    coordinates_list.extend(coordinates)

    return np.array(atom_list), np.array(coordinates_list)


def _binarize(x: torch.Tensor) -> torch.Tensor:
    return torch.where(x > 0, torch.ones_like(x), torch.zeros_like(x))


def _n_hops_adj(adj: torch.Tensor, n_hops: int) -> torch.Tensor:
    adj_mats = [
        torch.eye(adj.size(0), dtype=torch.long, device=adj.device),
        _binarize(adj + torch.eye(adj.size(0), dtype=torch.long, device=adj.device)),
    ]
    for i in range(2, n_hops + 1):
        adj_mats.append(_binarize(adj_mats[i - 1] @ adj_mats[1]))
    extend_mat = torch.zeros_like(adj)
    for i in range(1, n_hops + 1):
        extend_mat += (adj_mats[i] - adj_mats[i - 1]) * i
    return extend_mat


def _get_las_distance_constraint_mask(mol: Chem.Mol) -> torch.Tensor:
    adj = Chem.GetAdjacencyMatrix(mol)
    adj_tensor = torch.from_numpy(adj)
    extend_adj = _n_hops_adj(adj_tensor, 2)
    for ring in Chem.GetSymmSSSR(mol):
        for i in ring:
            for j in ring:
                if i != j:
                    extend_adj[i][j] += 1
    return _binarize(extend_adj)


def _parse_rna_structure(structure: str) -> List[Tuple[int, int]]:
    edges = []
    stack = []
    for i, symbol in enumerate(structure):
        if symbol == "(":
            stack.append(i)
        elif symbol == ")" and stack:
            opening_bracket_index = stack.pop()
            edges.append((opening_bracket_index, i))
            edges.append((i, opening_bracket_index))

    for i in range(len(structure) - 1):
        edges.append((i, i + 1))
        edges.append((i + 1, i))
    return edges


def _inner_smi2coords(smi: str, seed: int = 42, mode: str = "fast", remove_hs: bool = True):
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        raise HTTPException(status_code=400, detail=f"Invalid SMILES: {smi}")
    mol = Chem.AddHs(mol)
    atoms = [atom.GetSymbol() for atom in mol.GetAtoms()]
    try:
        res = AllChem.EmbedMolecule(mol, maxAttempts=5000, randomSeed=-1)
        if res == 0:
            try:
                AllChem.MMFFOptimizeMolecule(mol)
            except Exception:
                pass
            coordinates = mol.GetConformer().GetPositions().astype(np.float32)
        elif res == -1 and mode == "heavy":
            AllChem.EmbedMolecule(mol, maxAttempts=5000, randomSeed=seed)
            try:
                AllChem.MMFFOptimizeMolecule(mol)
                coordinates = mol.GetConformer().GetPositions().astype(np.float32)
            except Exception:
                AllChem.Compute2DCoords(mol)
                coordinates = mol.GetConformer().GetPositions().astype(np.float32)
        else:
            AllChem.Compute2DCoords(mol)
            coordinates = mol.GetConformer().GetPositions().astype(np.float32)
    except Exception:
        coordinates = np.zeros((len(atoms), 3), dtype=np.float32)

    if remove_hs:
        idx = [i for i, atom in enumerate(atoms) if atom != "H"]
        atoms_no_h = [atom for atom in atoms if atom != "H"]
        coordinates_no_h = coordinates[idx]
        return atoms_no_h, coordinates_no_h
    return atoms, coordinates


def _request_rhofold_pdb(
    sequence: str,
    rhofold_service_url: Optional[str],
) -> Path:
    service_url = rhofold_service_url or DEFAULT_RHOFOLD_SERVICE_URL
    try:
        response = requests.post(
            service_url,
            json={"sequence": sequence, "single_seq_pred": True, "relax_steps": 0},
            timeout=1800,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = ""
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            try:
                detail = str(response_obj.json())
            except ValueError:
                detail = response_obj.text
        suffix = f"; detail={detail}" if detail else ""
        raise HTTPException(
            status_code=503,
            detail=f"GerNA-Bind preprocessing failed to call RhoFold service: {exc}{suffix}",
        ) from exc

    payload = response.json()
    output_pdb_path = payload.get("output_pdb_path")
    if not output_pdb_path:
        raise HTTPException(
            status_code=503,
            detail="RhoFold service response is missing `output_pdb_path`.",
        )

    pdb_path = Path(output_pdb_path)
    if not pdb_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"RhoFold service returned a PDB path that does not exist: {output_pdb_path}",
        )
    return pdb_path


def _build_single_example(
    rna_sequence: str,
    smiles: str,
    pdb_path: Optional[str],
    secondary_structure: Optional[str],
    rhofold_service_url: Optional[str],
) -> Tuple[Tuple[object, ...], str, str]:
    with TemporaryDirectory(prefix="gernabind_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        fasta_path = tmp_dir_path / "input.fasta"
        fasta_path.write_text(f">query\n{rna_sequence}\n", encoding="utf-8")

        used_secondary_structure = secondary_structure or _run_rnafold(fasta_path)

        if pdb_path:
            used_pdb_path = _resolve_path(pdb_path)
        else:
            used_pdb_path = _request_rhofold_pdb(rna_sequence, rhofold_service_url)

        if not used_pdb_path.exists():
            raise HTTPException(status_code=503, detail=f"PDB file does not exist: {used_pdb_path}")

        rna_embedding = _get_rna_embeddings(rna_sequence)
        edge_index = torch.tensor(
            np.array(_parse_rna_structure(used_secondary_structure)).T,
            dtype=torch.long,
        )
        rna_graph = Data(x=rna_embedding, edge_index=edge_index)

        rna_3_coords = _extract_atom_coordinates(used_pdb_path, ["C4'", "N1", "P"])
        rna_c4_coords = _extract_atom_coordinates(used_pdb_path, ["C4'"])

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise HTTPException(status_code=400, detail=f"Invalid SMILES: {smiles}")

        atoms, coords = _inner_smi2coords(smiles)
        atom_ids = [ATOM_ID.get(atom, ATOM_ID["unknown"]) for atom in atoms]

        example = (
            rna_embedding,
            fea.simplify_atom_to_graph_data_obj(mol),
            rna_graph,
            rna_3_coords[0],
            rna_c4_coords[1],
            rna_3_coords[1],
            atom_ids,
            np.array(coords),
            _get_las_distance_constraint_mask(mol),
        )
        return example, str(used_pdb_path), used_secondary_structure


def _custom_collate_fn(batch):
    batch_rna_repre = []
    batch_mol_graph = []
    batch_rna_graph = []
    batch_rna_feats = []
    batch_rna_c4_coors = []
    batch_rna_coors = []
    batch_mol_feats = []
    batch_mol_coors = []
    batch_mol_las = []

    for item in batch:
        (
            rna_repre,
            mol_graph,
            rna_graph,
            rna_feats,
            rna_coors_c4,
            rna_coors,
            mol_feats,
            mol_coors,
            mol_las,
        ) = item

        batch_rna_repre.append(rna_repre)
        batch_mol_graph.append(mol_graph)
        batch_rna_graph.append(rna_graph)
        batch_rna_feats.append(rna_feats)
        batch_rna_c4_coors.append(rna_coors_c4)
        batch_rna_coors.append(rna_coors)
        batch_mol_feats.append(mol_feats)
        batch_mol_coors.append(mol_coors)
        batch_mol_las.append(mol_las)

    batch_seq_mask = torch.tensor(np.array(get_mask(batch_rna_repre))).float()
    batch_rna_repre = torch.tensor(np.array(pack2D(batch_rna_repre))).float()
    batch_mol_graph = Batch.from_data_list(batch_mol_graph)
    batch_rna_graph = Batch.from_data_list(batch_rna_graph)
    batch_rna_mask = torch.tensor(np.array(get_mask(batch_rna_feats))).bool()
    batch_mol_mask = torch.tensor(np.array(get_mask(batch_mol_coors))).bool()
    batch_rna_feats = torch.tensor(np.array(pack1D(batch_rna_feats))).long()
    batch_rna_c4_coors = torch.tensor(np.array(pack2D(batch_rna_c4_coors))).float()
    batch_rna_coors = torch.tensor(np.array(pack2D(batch_rna_coors))).float()
    batch_mol_feats = torch.tensor(np.array(pack1D(batch_mol_feats))).long()
    batch_mol_coors = torch.tensor(np.array(pack2D(batch_mol_coors))).float()
    batch_mol_las = torch.tensor(np.array(pack2D(batch_mol_las))).float()

    return (
        batch_rna_repre,
        batch_seq_mask,
        batch_mol_graph,
        batch_rna_graph,
        batch_rna_feats,
        batch_rna_c4_coors,
        batch_rna_coors,
        batch_rna_mask,
        batch_mol_feats,
        batch_mol_coors,
        batch_mol_mask,
        batch_mol_las,
    )


def _move_batch_to_device(batch: Tuple[object, ...], device: torch.device) -> Tuple[object, ...]:
    return tuple(item.to(device) for item in batch)


@lru_cache(maxsize=8)
def _load_affinity_model(checkpoint_path: str, device_name: str) -> GerNA:
    net = GerNA([4, 2, 128, 128], trigonometry=True, rna_graph=True, coors=True, coors_3_bead=True, uncertainty=True)
    pretrained_dict = torch.load(checkpoint_path, map_location=device_name)
    model_dict = net.state_dict()
    filtered_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
    model_dict.update(filtered_dict)
    net.load_state_dict(model_dict)
    net.to(torch.device(device_name))
    net.eval()
    return net


@lru_cache(maxsize=8)
def _load_binding_model(checkpoint_path: str, device_name: str) -> GerNA:
    net = GerNA([4, 2, 128, 128], trigonometry=True, rna_graph=False, coors=False, coors_3_bead=False, uncertainty=True)
    pretrained_dict = torch.load(checkpoint_path, map_location=device_name)
    model_dict = net.state_dict()
    filtered_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
    model_dict.update(filtered_dict)
    net.load_state_dict(model_dict)
    net.to(torch.device(device_name))
    net.eval()
    return net


@app.get("/health")
def health() -> Dict[str, object]:
    affinity_checkpoint = ""
    binding_checkpoint = ""
    affinity_ready = False
    binding_ready = False
    affinity_detail = ""
    binding_detail = ""

    try:
        affinity_checkpoint = str(_resolve_affinity_checkpoint())
        affinity_ready = True
    except HTTPException as exc:
        affinity_detail = str(exc.detail)

    try:
        binding_checkpoint = str(_resolve_binding_checkpoint())
        binding_ready = True
    except HTTPException as exc:
        binding_detail = str(exc.detail)

    return {
        "status": "ok",
        "gernabind_root": str(GERNABIND_ROOT),
        "affinity_checkpoint_ready": affinity_ready,
        "affinity_checkpoint_path": affinity_checkpoint,
        "affinity_detail": affinity_detail,
        "binding_checkpoint_ready": binding_ready,
        "binding_checkpoint_path": binding_checkpoint,
        "binding_detail": binding_detail,
        "default_rhofold_service_url": DEFAULT_RHOFOLD_SERVICE_URL,
    }


@app.post("/score", response_model=ScoreResponse)
def score(payload: ScoreRequest) -> ScoreResponse:
    rna_sequence = _normalize_rna_sequence(payload.rna_sequence)
    checkpoint = _resolve_affinity_checkpoint(payload.checkpoint_path)
    device = _resolve_device(payload.device)

    example, preprocessing_pdb_path, used_secondary_structure = _build_single_example(
        rna_sequence=rna_sequence,
        smiles=payload.smiles.strip(),
        pdb_path=payload.pdb_path,
        secondary_structure=payload.secondary_structure,
        rhofold_service_url=payload.rhofold_service_url,
    )

    model = _load_affinity_model(str(checkpoint), str(device))
    batch = _move_batch_to_device(_custom_collate_fn([example]), device)

    with torch.no_grad():
        affinity_pred, _ = model(*batch)

    raw_alpha = affinity_pred[0].detach().cpu().numpy().tolist()
    probability_positive = float(raw_alpha[1] / max(sum(raw_alpha), 1e-8))
    predicted_label = int(np.argmax(raw_alpha))

    return ScoreResponse(
        rna_sequence=rna_sequence,
        smiles=payload.smiles.strip(),
        probability_positive=probability_positive,
        predicted_label=predicted_label,
        raw_alpha=[float(value) for value in raw_alpha],
        checkpoint_path=str(checkpoint),
        preprocessing_pdb_path=preprocessing_pdb_path,
        secondary_structure=used_secondary_structure,
        device=str(device),
    )


@app.post("/predict-binding-site", response_model=BindingSiteResponse)
def predict_binding_site(payload: BindingSiteRequest) -> BindingSiteResponse:
    rna_sequence = _normalize_rna_sequence(payload.rna_sequence)
    checkpoint = _resolve_binding_checkpoint(payload.checkpoint_path)
    device = _resolve_device(payload.device)

    example, preprocessing_pdb_path, used_secondary_structure = _build_single_example(
        rna_sequence=rna_sequence,
        smiles=payload.smiles.strip(),
        pdb_path=payload.pdb_path,
        secondary_structure=payload.secondary_structure,
        rhofold_service_url=payload.rhofold_service_url,
    )

    model = _load_binding_model(str(checkpoint), str(device))
    batch = _move_batch_to_device(_custom_collate_fn([example]), device)

    with torch.no_grad():
        _, interaction = model(*batch)

    interaction_scores = interaction[0].detach().cpu().numpy()
    per_residue_scores = np.round(np.max(interaction_scores, axis=1), 4).tolist()

    return BindingSiteResponse(
        rna_sequence=rna_sequence,
        smiles=payload.smiles.strip(),
        per_residue_scores=[float(value) for value in per_residue_scores],
        checkpoint_path=str(checkpoint),
        preprocessing_pdb_path=preprocessing_pdb_path,
        secondary_structure=used_secondary_structure,
        device=str(device),
    )
