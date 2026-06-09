import os
import sys
import subprocess
import numpy as np
from Bio.PDB import PDBParser

PDB_IDS = [
    ("1ehz", "tRNA-Phe (yeast)"),
    ("1mme", "Hammerhead ribozyme"),
    ("1y26", "Hairpin ribozyme"),
    ("1gid", "Group I intron (Tetrahymena)"),
    ("3d2v", "SAM-I riboswitch"),
    ("1hr2", "P4-P6 domain"),
    ("1f7u", "Theophylline aptamer"),
    ("2gdi", "T-box riboswitch"),
]

MODIFIED_MAP = {
    'A': 'A', 'U': 'U', 'G': 'G', 'C': 'C',
    'RA': 'A', 'RU': 'U', 'RG': 'G', 'RC': 'C',
    'ADE': 'A', 'URA': 'U', 'URI': 'U', 'GUA': 'G', 'CYT': 'C',
    'DA': 'A', 'DT': 'T', 'DG': 'G', 'DC': 'C',
    # Modified nucleotides mapped to standard bases
    '1MA': 'A', '2MG': 'G', '5MC': 'C', '5MU': 'U', '7MG': 'G',
    'H2U': 'U', 'M2G': 'G', 'OMC': 'C', 'OMG': 'G', 'PSU': 'U',
    'YYG': 'G', '1MG': 'G', 'M2A': 'A', '6MZ': 'A', 'UR3': 'U',
    '4SU': 'U', 'A2M': 'A', 'CMG': 'G', 'T6A': 'A', 'I': 'G',
    'MA6': 'A', 'MGT': 'G', 'ATP': 'A', 'GTP': 'G', 'CTP': 'C', 'UTP': 'U',
    'GDP': 'G', 'ADP': 'A', 'UDP': 'U', 'CDP': 'C',
}

def download_pdb(pdb_id):
    path = f"{pdb_id.lower()}.pdb"
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        print(f"  {pdb_id} already exists, skipping download.")
        return path
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    print(f"  Downloading {pdb_id} from {url} ...")
    result = subprocess.run(['curl', '-sL', '-o', path, url])
    if result.returncode != 0 or os.path.getsize(path) < 1000:
        raise RuntimeError(f"Failed to download {pdb_id}")
    return path

def extract_rna_sequence(pdb_path):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure('rna', pdb_path)
    sequences = []
    for model in structure:
        for chain in model:
            seq = []
            for residue in chain:
                resname = residue.resname.strip()
                if resname in ('HOH', 'MG', 'MN', 'NA', 'CL', 'K', 'CA', 'ZN'):
                    continue  # Skip ions and water
                if resname in MODIFIED_MAP:
                    base = MODIFIED_MAP[resname]
                    if base in 'AUGC':
                        seq.append(base)
            if len(seq) >= 10:
                sequences.append((''.join(seq), chain.id))
    if not sequences:
        return None, None
    # Return longest RNA chain
    return max(sequences, key=lambda x: len(x[0]))

def predict_secondary_structure(sequence):
    result = subprocess.run(
        ['RNAfold', '--noPS'],
        input=sequence,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"RNAfold failed: {result.stderr}")
    lines = result.stdout.strip().split('\n')
    struct_line = lines[1] if len(lines) > 1 else lines[0]
    structure = struct_line.split()[0]
    return structure

def dot_bracket_to_contact_map(structure):
    L = len(structure)
    cm = np.zeros((L, L), dtype=np.float32)
    stack = []
    for i, char in enumerate(structure):
        if char == '(':
            stack.append(i)
        elif char == ')':
            if stack:
                j = stack.pop()
                cm[i, j] = 1.0
                cm[j, i] = 1.0
    return cm

def main():
    results = []
    for pdb_id, desc in PDB_IDS:
        print(f"\nProcessing {pdb_id.upper()} ({desc}) ...")
        try:
            pdb_path = download_pdb(pdb_id)
            seq, chain_id = extract_rna_sequence(pdb_path)
            if seq is None:
                print(f"  WARNING: No RNA sequence found in {pdb_id}")
                continue
            print(f"  Chain {chain_id}: {len(seq)} nt")
            print(f"  Seq: {seq[:60]}{'...' if len(seq)>60 else ''}")
            
            struct = predict_secondary_structure(seq)
            print(f"  2D:  {struct[:60]}{'...' if len(struct)>60 else ''}")
            
            cm = dot_bracket_to_contact_map(struct)
            npy_path = f"{pdb_id.lower()}_contact_map.npy"
            np.save(npy_path, cm)
            print(f"  Saved contact map -> {npy_path} (contacts: {int(cm.sum()/2)})")
            
            results.append({
                'pdb_id': pdb_id.lower(),
                'description': desc,
                'chain': chain_id,
                'length': len(seq),
                'sequence': seq,
                'pdb_path': os.path.abspath(pdb_path),
                'npy_path': os.path.abspath(npy_path),
            })
        except Exception as exc:
            print(f"  ERROR: {exc}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for r in results:
        print(f"{r['pdb_id']:6s} | {r['description']:30s} | chain={r['chain']:3s} | len={r['length']:4d}")
    print("="*60)

if __name__ == '__main__':
    main()
