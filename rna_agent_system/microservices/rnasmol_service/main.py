"""RNAsmol microservice for RNA-ligand binding scoring."""

from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rdkit import Chem
from torch_geometric.data import Data

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RNASMOL_ROOT = PROJECT_ROOT / "external_repos" / "RNAsmol"
RNASMOL_CODE_DIR = RNASMOL_ROOT / "rnasmol"
DEFAULT_CHECKPOINT_DIR = RNASMOL_ROOT / "saved_model"

if str(RNASMOL_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(RNASMOL_CODE_DIR))

from model import MCNN_GCN  # noqa: E402

app = FastAPI(
    title="RNAsmol Service",
    description="Score RNA-ligand interactions with the RNAsmol classifier.",
    version="0.1.0",
)

VOCAB_PROTEIN = {
    "A": 1,
    "C": 2,
    "G": 3,
    "T": 4,
    "U": 4,
    "a": 5,
    "c": 6,
    "g": 7,
    "t": 8,
    "u": 8,
    "D": 9,
    "d": 9,
    "B": 9,
    "b": 9,
    "F": 9,
    "f": 9,
    "I": 9,
    "i": 9,
    "H": 9,
    "h": 9,
    "K": 9,
    "k": 9,
    "M": 9,
    "m": 9,
    "L": 9,
    "l": 9,
    "O": 9,
    "o": 9,
    "N": 9,
    "n": 9,
    "Q": 9,
    "q": 9,
    "P": 9,
    "p": 9,
    "S": 9,
    "s": 9,
    "R": 9,
    "r": 9,
    "E": 9,
    "e": 9,
    "W": 9,
    "w": 9,
    "V": 9,
    "v": 9,
    "Y": 9,
    "y": 9,
    "X": 9,
    "x": 9,
    "Z": 9,
    "z": 9,
}


class ScoreRequest(BaseModel):
    rna_sequence: str = Field(
        ...,
        min_length=1,
        description="RNA sequence to score. FASTA-like text is accepted.",
    )
    smiles: str = Field(
        ...,
        min_length=1,
        description="Ligand SMILES string scored by RNAsmol.",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional checkpoint override. Defaults to service auto-discovery.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional PyTorch device string such as `cuda:0` or `cpu`.",
    )


class ScoreResponse(BaseModel):
    rna_sequence: str
    smiles: str
    probability_positive: float
    predicted_label: int
    raw_logits: List[float]
    checkpoint_path: str
    device: str
    model: str = "RNAsmol"


def _is_lfs_pointer(path: Path) -> bool:
    if not path.exists():
        return False
    prefix = path.read_bytes()[:64]
    return prefix.startswith(b"version https://git-lfs.github.com/spec/v1")


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


def _seqs2int(target: str) -> List[int]:
    return [VOCAB_PROTEIN.get(symbol, 9) for symbol in target]


def _one_of_k_encoding(x: object, allowable_set: List[object]) -> List[bool]:
    if x not in allowable_set:
        raise ValueError(f"input {x} not in allowable set {allowable_set}")
    return [x == symbol for symbol in allowable_set]


def _one_of_k_encoding_unk(x: object, allowable_set: List[object]) -> List[bool]:
    if x not in allowable_set:
        x = allowable_set[-1]
    return [x == symbol for symbol in allowable_set]


def _atom_features(atom: Chem.rdchem.Atom) -> np.ndarray:
    encoding = _one_of_k_encoding_unk(
        atom.GetSymbol(),
        [
            "C",
            "N",
            "O",
            "S",
            "F",
            "Si",
            "P",
            "Cl",
            "Br",
            "Mg",
            "Na",
            "Ca",
            "Fe",
            "As",
            "Al",
            "I",
            "B",
            "V",
            "K",
            "Tl",
            "Yb",
            "Sb",
            "Sn",
            "Ag",
            "Pd",
            "Co",
            "Se",
            "Ti",
            "Zn",
            "H",
            "Li",
            "Ge",
            "Cu",
            "Au",
            "Ni",
            "Cd",
            "In",
            "Mn",
            "Zr",
            "Cr",
            "Pt",
            "Hg",
            "Pb",
            "Unknown",
        ],
    )
    encoding += _one_of_k_encoding(atom.GetDegree(), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    encoding += _one_of_k_encoding_unk(atom.GetTotalNumHs(), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    encoding += _one_of_k_encoding_unk(atom.GetImplicitValence(), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    encoding += _one_of_k_encoding_unk(
        atom.GetHybridization(),
        [
            Chem.rdchem.HybridizationType.SP,
            Chem.rdchem.HybridizationType.SP2,
            Chem.rdchem.HybridizationType.SP3,
            Chem.rdchem.HybridizationType.SP3D,
            Chem.rdchem.HybridizationType.SP3D2,
            "other",
        ],
    )
    encoding += [atom.GetIsAromatic()]
    try:
        encoding += _one_of_k_encoding_unk(atom.GetProp("_CIPCode"), ["R", "S"])
        encoding += [atom.HasProp("_ChiralityPossible")]
    except Exception:
        encoding += [0, 0, atom.HasProp("_ChiralityPossible")]
    return np.asarray(encoding, dtype=np.float32)


def _mol_to_graph(mol: Chem.Mol) -> Tuple[np.ndarray, np.ndarray]:
    features = []
    for atom in mol.GetAtoms():
        feature = _atom_features(atom)
        features.append(feature / max(feature.sum(), 1.0))

    if not features:
        raise HTTPException(status_code=400, detail="SMILES produced an empty molecular graph.")

    num_nodes = len(features)
    adjacency = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    undirected_edges = []
    for bond in mol.GetBonds():
        begin_idx = bond.GetBeginAtomIdx()
        end_idx = bond.GetEndAtomIdx()
        undirected_edges.append((begin_idx, end_idx))
        adjacency[begin_idx, end_idx] = 1.0
        adjacency[end_idx, begin_idx] = 1.0

    if undirected_edges:
        graph = nx.Graph(undirected_edges).to_directed()
        for src, dst in graph.edges:
            adjacency[src, dst] = 1.0

    return np.asarray(features, dtype=np.float32), adjacency


def _get_ppr_matrix(adj_matrix: np.ndarray, alpha: float = 0.1) -> np.ndarray:
    num_nodes = adj_matrix.shape[0]
    a_tilde = adj_matrix + np.eye(num_nodes)
    d_tilde = np.diag(1 / np.sqrt(a_tilde.sum(axis=1)))
    h_matrix = d_tilde @ a_tilde @ d_tilde
    return alpha * np.linalg.inv(np.eye(num_nodes) - (1 - alpha) * h_matrix)


def _get_top_k_matrix(matrix: np.ndarray, k: int = 5) -> np.ndarray:
    num_nodes = matrix.shape[0]
    row_idx = np.arange(num_nodes)
    matrix = matrix.copy()
    matrix[matrix.argsort(axis=0)[: max(num_nodes - k, 0)], row_idx] = 0.0
    norm = matrix.sum(axis=0)
    norm[norm <= 0] = 1.0
    return matrix / norm


def _build_single_example(smiles: str, rna_sequence: str) -> Data:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise HTTPException(status_code=400, detail=f"Invalid SMILES: {smiles}")

    node_features, adjacency = _mol_to_graph(mol)
    ppr_matrix = _get_top_k_matrix(_get_ppr_matrix(adjacency, alpha=0.1), k=5)

    target = _seqs2int(rna_sequence)
    target_len = 500
    if len(target) < target_len:
        target = list(np.pad(target, (0, target_len - len(target))))
    else:
        target = target[:target_len]

    edges_i = []
    edges_j = []
    edge_attr = []
    for row_index, row in enumerate(ppr_matrix):
        for col_index in np.where(row > 0)[0]:
            edges_i.append(row_index)
            edges_j.append(int(col_index))
            edge_attr.append(float(ppr_matrix[row_index, col_index]))

    data = Data(
        x=torch.FloatTensor(node_features),
        edge_index=torch.LongTensor([edges_i, edges_j]),
        edge_attr=torch.FloatTensor(edge_attr),
        target=torch.LongTensor([target]),
    )
    data.batch = torch.zeros(data.x.size(0), dtype=torch.long)
    return data


def _default_device_name() -> str:
    requested = os.environ.get("RNASMOL_DEVICE", "").strip()
    if requested:
        return requested
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def _resolve_device(device_name: Optional[str]) -> torch.device:
    resolved_name = device_name or _default_device_name()
    if resolved_name:
        if resolved_name.startswith("cuda") and not torch.cuda.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"Requested device `{resolved_name}` but CUDA is not available.",
            )
        return torch.device(resolved_name)
    return torch.device("cpu")


def _resolve_checkpoint_path(checkpoint_path: Optional[str] = None) -> Path:
    candidates = []
    if checkpoint_path:
        requested = Path(checkpoint_path)
        candidates.append(requested if requested.is_absolute() else PROJECT_ROOT / checkpoint_path)

    env_checkpoint = os.environ.get("RNASMOL_CHECKPOINT_PATH")
    if env_checkpoint:
        env_path = Path(env_checkpoint)
        candidates.append(env_path if env_path.is_absolute() else PROJECT_ROOT / env_checkpoint)

    candidates.extend(sorted(DEFAULT_CHECKPOINT_DIR.glob("*.pt")))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            if _is_lfs_pointer(candidate):
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"RNAsmol checkpoint `{candidate}` is still a Git LFS pointer. "
                        "Copy the real `.pt` file to the Linux server before starting the service."
                    ),
                )
            return candidate

    raise HTTPException(
        status_code=503,
        detail=(
            "No RNAsmol checkpoint was found. Set `RNASMOL_CHECKPOINT_PATH` or place a `.pt` file under "
            "`rna_agent_system/external_repos/RNAsmol/saved_model/`."
        ),
    )


@lru_cache(maxsize=8)
def _load_model(checkpoint_path: str, device_name: str) -> MCNN_GCN:
    model = MCNN_GCN(3, 25 + 1, embedding_size=96, filter_num=32, out_dim=2, ban_heads=2)
    state_dict = torch.load(checkpoint_path, map_location=device_name)
    model.load_state_dict(state_dict, strict=False)
    model.to(torch.device(device_name))
    model.eval()
    return model


@app.get("/health")
def health() -> Dict[str, object]:
    checkpoint_ready = False
    checkpoint_path = ""
    detail = ""
    try:
        checkpoint = _resolve_checkpoint_path()
        checkpoint_ready = True
        checkpoint_path = str(checkpoint)
    except HTTPException as exc:
        detail = str(exc.detail)

    return {
        "status": "ok",
        "checkpoint_ready": checkpoint_ready,
        "checkpoint_path": checkpoint_path,
        "rnasmol_root": str(RNASMOL_ROOT),
        "default_device": _default_device_name(),
        "detail": detail,
    }


@app.post("/score", response_model=ScoreResponse)
def score(payload: ScoreRequest) -> ScoreResponse:
    checkpoint = _resolve_checkpoint_path(payload.checkpoint_path)
    device = _resolve_device(payload.device)
    rna_sequence = _normalize_rna_sequence(payload.rna_sequence)
    data = _build_single_example(payload.smiles.strip(), rna_sequence).to(device)

    model = _load_model(str(checkpoint), str(device))
    with torch.no_grad():
        _, _, _, logits = model(data, mode="eval")
        probabilities = torch.softmax(logits, dim=-1)[0].detach().cpu().tolist()
        predicted_label = int(torch.argmax(logits, dim=-1).item())

    return ScoreResponse(
        rna_sequence=rna_sequence,
        smiles=payload.smiles.strip(),
        probability_positive=float(probabilities[1]),
        predicted_label=predicted_label,
        raw_logits=[float(value) for value in logits[0].detach().cpu().tolist()],
        checkpoint_path=str(checkpoint),
        device=str(device),
    )
