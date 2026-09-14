"""Shared harness for the E21/E22 external-baseline arms (2026-09-14 registration).

Common machinery for ``exp42_bare_llm_baseline.py`` (E21) and
``exp43_react_baseline.py`` (E22), registered in ``docs/DECISIONS.md`` Part 4
before any run:

- PA task loading + deterministic turn-brief rendering (identical inputs to
  the frozen Exp-41/Exp-24 platform arm: same sessions, same turns, same
  parameter values, fixture contents inlined under a registered rule);
- per-workflow output contracts (the JSON both baseline arms must emit);
- platform budget extraction from the frozen Exp-41 Block-A records and
  session ``workflow_results_*.json`` (LLM calls + evaluated candidates);
- per-workflow deterministic validity checks over delivered candidates, plus
  claim adjudication generalized from the e3/exp5 blind-adjudicator rules.

Everything here is deterministic given the arm responses; the two drivers
own the LLM/ReAct loops. All recomputations that need the platform tool
layer go through ``ToolExecutor.run_tool`` (audited; CapGate advisory).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PA_BENCHMARKS = PROJECT_ROOT / "pa_benchmarks.json"
EXP41_BLOCK_A = PROJECT_ROOT / "experiments" / "results" / "exp41_agent_ablation" / "blockA" / "records.jsonl"
SESSIONS_ROOT = PROJECT_ROOT / "workspace" / "sessions"

# ── fixture inlining rule (registered) ────────────────────────────────────────
# Text fixtures <= 20 KB are inlined verbatim; larger files are head-only
# (first 40 lines + byte size + the on-disk path — the ReAct arm can read the
# full file through tools; the bare-LLM arm cannot, which is the point of the
# tool-free floor).
INLINE_LIMIT_BYTES = 20_000
INLINE_HEAD_LINES = 40


# ══════════════════════════════════════════════════════════════════════════════
# 1. PA task loading
# ══════════════════════════════════════════════════════════════════════════════


def load_pa_tasks(only: list[str] | None = None) -> list[dict[str, Any]]:
    """Load PA sessions as {pa_id, workflow, turns: [params]} (sorted by id)."""
    data = json.loads(PA_BENCHMARKS.read_text(encoding="utf-8"))
    tasks = []
    for pid in sorted(data):
        if only is not None and pid not in only:
            continue
        entry = data[pid]
        tasks.append(
            {
                "pa_id": f"PA_{pid}",
                "pa_num": pid,
                "workflow": entry["workflow"],
                "turns": entry["params_by_turn"],
            }
        )
    return tasks


# ══════════════════════════════════════════════════════════════════════════════
# 2. Deterministic turn-brief rendering (registered templates)
# ══════════════════════════════════════════════════════════════════════════════

WORKFLOW_GOALS: dict[str, str] = {
    "sirna_design": (
        "Design therapeutic siRNA candidates against the given target RNA: "
        "21-nt antisense guides (RNA alphabet) complementary to a window of "
        "the target, with good GC content and duplex thermodynamics, and "
        "minimal predicted off-targets in the specified species."
    ),
    "sgrna_design": (
        "Design CRISPR sgRNA guide candidates for the given target sequence: "
        "20-nt guide sequences (RNA alphabet) matching the target adjacent "
        "to an NGG PAM, with good GC content and minimized off-target risk."
    ),
    "rna_aptamer_design": (
        "Design single-stranded RNA aptamer candidates of the requested "
        "length against the given protein target: sequences in the RNA "
        "alphabet with good GC content and folding behaviour."
    ),
    "rna_small_molecule_interaction": (
        "Predict the interaction strength between the given RNA sequence and "
        "the given small molecule (SMILES): report a binding probability in "
        "[0, 1]."
    ),
    "aso_target_screening": (
        "Screen antisense oligonucleotide (ASO) target windows on the given "
        "target mRNA: contiguous RNA windows of the requested length that "
        "are substrings of the target, ranked by predicted accessibility."
    ),
    "ires_prediction": (
        "Predict IRES activity in the given RNA sequence(s): report, per "
        "sequence, a probability of internal ribosome entry site activity "
        "in [0, 1]."
    ),
    "rna_tertiary_structure_design": (
        "Design an RNA tertiary structure (3D coordinates, PDB format) that "
        "folds into the given target structure."
    ),
    "mrna_sequence_scoring": (
        "Score the given mRNA sequence: report its codon adaptation index "
        "(CAI) for the requested species, GC content, and minimum free "
        "energy of folding (kcal/mol, whole sequence)."
    ),
    "mrna_cds_design": (
        "Design an mRNA coding sequence (CDS) encoding exactly the given "
        "protein: RNA sequence, length a multiple of 3, translating to the "
        "protein residue-for-residue, optimizing CAI for the requested "
        "species and folding energy."
    ),
    "rna_secondary_structure_design": (
        "Design an RNA sequence (RNA alphabet, same length as the target "
        "structure) whose minimum-free-energy secondary structure matches "
        "the given target dot-bracket structure as closely as possible."
    ),
    "full_length_mrna_design": (
        "Design a full-length mRNA construct (5'UTR + CDS + 3'UTR, RNA "
        "alphabet) whose CDS encodes exactly the given protein: optimize "
        "CAI for the requested species, avoid 5'UTR upstream AUGs, and "
        "avoid Class-II AU-rich elements in the 3'UTR."
    ),
}

# Per-workflow output contract (both arms emit the same JSON envelope).
OUTPUT_CONTRACTS: dict[str, str] = {
    "design": (
        '{"candidates": [{"id": "c1", "sequence": "<RNA sequence>"}], '
        '"claims": [<claim objects>]}'
    ),
    "tertiary": (
        '{"candidates": [{"id": "c1", "structure": "<full PDB text or a path '
        'to a PDB file you produced>"}], "claims": [<claim objects>]}'
    ),
    "scoring": (
        '{"metrics": {"cai": <number>, "gc_content": <number>, '
        '"mfe_kcal_mol": <number>}, "claims": [<claim objects>]}'
    ),
    "small_molecule": (
        '{"metrics": {"binding_probability": <number in [0,1]>}, '
        '"claims": [<claim objects>]}'
    ),
    "ires": (
        '{"predictions": [{"sequence_id": "<id>", "probability": <number in '
        '[0,1]>}], "claims": [<claim objects>]}'
    ),
}

CONTRACT_BY_WORKFLOW: dict[str, str] = {
    "sirna_design": "design",
    "sgrna_design": "design",
    "rna_aptamer_design": "design",
    "aso_target_screening": "design",
    "rna_secondary_structure_design": "design",
    "rna_tertiary_structure_design": "tertiary",
    "mrna_sequence_scoring": "scoring",
    "rna_small_molecule_interaction": "small_molecule",
    "ires_prediction": "ires",
    "mrna_cds_design": "design",
    "full_length_mrna_design": "design",
}

CLAIM_OBJECT_SPEC = (
    'Claim object schema: {"claim_id": "c1", "text": "<one sentence>", '
    '"claim_type": "<metric|ranking|screening|other>", "metric": '
    '"<gc_content|u_content|cai|mfe_kcal_mol|length|binding_probability|'
    'ires_probability|none>", "asserted_value": <number|null>, '
    '"asserted_best_id": "<candidate id|null>", "scope": '
    '"<absolute|within_target_relative|trend_only>", "basis": '
    '"<self_computation|none>"}'
)

FILE_PARAM_KEYS = (
    "sequence_filepath",
    "target_mrna_filepath",
    "structure_filepath",
    "protein_structure_path",
)


def _inline_file(path_str: str) -> str:
    p = Path(path_str)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    if not p.is_file():
        return f"[file not found: {path_str}]"
    raw = p.read_bytes()
    if len(raw) <= INLINE_LIMIT_BYTES:
        return raw.decode("utf-8", errors="replace")
    text = raw.decode("utf-8", errors="replace")
    head = "\n".join(text.splitlines()[:INLINE_HEAD_LINES])
    return f"{head}\n...[truncated: file is {len(raw)} bytes; full file at {p}]"


def render_turn_brief(workflow: str, turn_idx: int, params: dict[str, Any]) -> str:
    """Deterministic text brief for one PA turn (registered template)."""
    lines = [
        f"TASK (RNA design agent benchmark, workflow: {workflow}, turn {turn_idx})",
        f"GOAL: {WORKFLOW_GOALS[workflow]}",
        "",
        "PARAMETERS:",
    ]
    for key in sorted(params):
        val = params[key]
        if key in FILE_PARAM_KEYS and isinstance(val, str):
            lines.append(f"  {key}:")
            for ln in _inline_file(val).splitlines() or ["(empty file)"]:
                lines.append(f"    {ln}")
        else:
            lines.append(f"  {key}: {json.dumps(val, ensure_ascii=False)}")
    lines += [
        "",
        f"OUTPUT CONTRACT — reply with a single JSON object exactly of this shape: "
        f"{OUTPUT_CONTRACTS[CONTRACT_BY_WORKFLOW[workflow]]}",
        CLAIM_OBJECT_SPEC,
        "Quantitative claims must carry a metric and asserted_value when a "
        "number is asserted. Deliver at least one candidate (design tasks) or "
        "the metric block (scoring tasks) for this turn.",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Platform budgets from the frozen Exp-41 Block-A records
# ══════════════════════════════════════════════════════════════════════════════


def platform_budgets() -> dict[str, dict[str, Any]]:
    """{pa_id: {llm_calls, evaluated_candidates, turns, session_success}}.

    llm_calls = the full arm's total_successful_review_calls (single-workflow
    PA sessions invoke the LLM only for quality review); evaluated_candidates
    = sum of len(candidates) over the session's workflow_results files.
    """
    out: dict[str, dict[str, Any]] = {}
    for line in EXP41_BLOCK_A.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("arm") != "full" or rec.get("pilot"):
            continue
        pa_id = f"PA_{int(rec['pa_id']):03d}"
        n_cands = 0
        sess_dirs = sorted(SESSIONS_ROOT.glob(f"exp41_full_pa{int(rec['pa_id']):03d}_*"))
        for sd in sess_dirs:
            for wf in sd.glob("workflow_results_*.json"):
                try:
                    data = json.loads(wf.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                n_cands += len(data.get("candidates") or [])
        out[pa_id] = {
            "llm_calls": rec.get("total_successful_review_calls", 0),
            "evaluated_candidates": n_cands,
            "turns": rec.get("n_turns"),
            "session_success": rec.get("session_success"),
        }
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 4. Deterministic validity checks (pure Python; no services)
# ══════════════════════════════════════════════════════════════════════════════

_RNA_ALPHA = set("AUGC")

_CODON_TABLE: dict[str, str] = {}
for _i, _b1 in enumerate("UCAG"):
    for _j, _b2 in enumerate("UCAG"):
        for _k, _b3 in enumerate("UCAG"):
            _codon = _b1 + _b2 + _b3
            _idx = _i * 16 + _j * 4 + _k
            _aa = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"[_idx]
            _CODON_TABLE[_codon] = _aa

_3TO1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


def normalize_rna(seq: str) -> str:
    return (seq or "").strip().upper().replace("T", "U").replace(" ", "").replace("\n", "")


def gc_content(seq: str) -> float | None:
    s = normalize_rna(seq)
    return (s.count("G") + s.count("C")) / len(s) if s else None


def translate(seq: str) -> str:
    s = normalize_rna(seq)
    return "".join(_CODON_TABLE.get(s[i : i + 3], "X") for i in range(0, len(s) - len(s) % 3, 3))


def revcomp(seq: str) -> str:
    s = normalize_rna(seq)
    return s.translate(str.maketrans("AUGC", "UACG"))[::-1]


def check_candidate(workflow: str, params: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    """Structural validity of one delivered candidate (registered checks).

    Returns {valid: bool, reasons: [..], recomputed: {..}} — claim
    adjudication consumes the recomputed block. Structural checks are
    deliberately minimal: length/alphabet/identity relations that do not
    depend on any learned predictor.
    """
    seq = normalize_rna(cand.get("sequence", "") or "")
    reasons: list[str] = []
    rec: dict[str, Any] = {"length": len(seq), "gc_content": gc_content(seq)}

    def _alpha_ok() -> bool:
        ok = bool(seq) and set(seq) <= _RNA_ALPHA
        if not ok:
            reasons.append(f"alphabet/empty ({len(seq)} nt, non-AUGC chars)" if seq else "empty sequence")
        return ok

    if workflow in ("sirna_design", "sgrna_design"):
        want = 21 if workflow == "sirna_design" else 20
        seed = normalize_rna(params.get("seed_sequence", "") or "")
        if workflow == "sgrna_design" and seed:
            want = {20, len(seed)}
            if len(seq) not in want:
                reasons.append(f"length {len(seq)} not in {sorted(want)} (bare spacer or full crRNA)")
            _alpha_ok()
            if len(seq) == len(seed):
                rec["hamming_to_seed"] = sum(a != b for a, b in zip(seq, seed))
        else:
            if len(seq) != want:
                reasons.append(f"length {len(seq)} != {want}")
            _alpha_ok()
        target = normalize_rna(params.get("target_sequence", "") or "")
        if target:
            rc = revcomp(seq)
            rec["complementary_to_target"] = rc in target
            rec["exact_target_match"] = seq in target
            if workflow == "sgrna_design" and len(seq) == 20:
                rec["pam_adjacent"] = bool(re.search(re.escape(seq) + ".GG", target))
            if workflow == "sirna_design" and not (
                rec["complementary_to_target"] or rec["exact_target_match"]
            ):
                # mode-dependent (multifapredsi consensus designs are not
                # literal complements): recorded, gated only by the per-turn
                # parity bar (the platform's own candidates set the bar)
                rec["non_complementary_note"] = True
    elif workflow == "rna_aptamer_design":
        want = params.get("aptamer_length")
        if isinstance(want, int) and len(seq) != want:
            reasons.append(f"length {len(seq)} != aptamer_length {want}")
        _alpha_ok()
    elif workflow == "mrna_cds_design":
        protein = (params.get("protein_sequence") or "").strip().upper()
        if len(seq) % 3 != 0:
            reasons.append(f"length {len(seq)} not multiple of 3")
        _alpha_ok()
        if protein and translate(seq).rstrip("*") != protein:
            reasons.append("translation != input protein")
        rec["translates_to_input"] = translate(seq).rstrip("*") == protein if protein else None
    elif workflow == "full_length_mrna_design":
        protein = (params.get("protein_sequence") or "").strip().upper()
        _alpha_ok()
        # locate the ORF translating to the protein (registered rule)
        pos = None
        if protein:
            for frame in range(3):
                t = translate(seq[frame:])
                idx = t.find(protein)
                if idx >= 0:
                    pos = frame + idx * 3
                    break
        rec["orf_start"] = pos
        if protein and pos is None:
            reasons.append("no ORF translating to the input protein")
        if pos is not None:
            cds = seq[pos : pos + len(protein) * 3]
            five_utr = seq[:pos]
            rec["cai_candidate_cds"] = cds
            rec["internal_aug_in_5utr"] = "AUG" in five_utr
            if "AUG" in five_utr:
                reasons.append("internal uAUG in 5'UTR (U1 admission rule)")
        else:
            rec["cai_candidate_cds"] = seq
    elif workflow == "rna_secondary_structure_design":
        _alpha_ok()
        target_struct = params.get("target_structure") or ""
        rec["target_structure_length"] = len(target_struct)
        if target_struct and len(seq) != len(target_struct):
            reasons.append(f"length {len(seq)} != target structure length {len(target_struct)}")
    elif workflow == "aso_target_screening":
        want = params.get("aso_length")
        if isinstance(want, int) and len(seq) != want:
            reasons.append(f"length {len(seq)} != aso_length {want}")
        _alpha_ok()
        fp = params.get("target_mrna_filepath")
        if fp:
            p = Path(fp)
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            if p.is_file():
                target = normalize_rna(
                    "".join(
                        ln for ln in p.read_text(encoding="utf-8").splitlines() if not ln.startswith(">")
                    )
                )
                rc = revcomp(seq)
                rec["substring_of_target"] = seq in target
                rec["antisense_of_target"] = bool(seq) and rc in target
                if seq and not (seq in target or rc in target):
                    reasons.append("window neither sense nor antisense substring of the target mRNA")
    else:
        # prediction-type workflows: candidates list is not the contract
        reasons.append("workflow does not take candidate sequences")

    return {"valid": not reasons, "reasons": reasons, "recomputed": rec}


def parse_pdb_residues(text: str) -> int:
    """Count distinct (chain, resid) RNA residues in PDB text (local check)."""
    seen: set[tuple[str, int, str]] = set()
    for line in text.splitlines():
        if line.startswith(("ATOM", "HETATM")) and len(line) >= 27:
            chain = line[21].strip()
            try:
                resseq = int(line[22:26])
            except ValueError:
                continue
            resname = line[17:20].strip()
            seen.add((chain, resseq, resname))
    return len(seen)


def check_response(workflow: str, params: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Whole-response validity: envelope + per-candidate checks.

    Returns {delivered, n_candidates, n_valid, candidates: [..], metrics, predictions}.
    """
    kind = CONTRACT_BY_WORKFLOW[workflow]
    out: dict[str, Any] = {
        "delivered": False,
        "envelope_reasons": [],
        "n_candidates": 0,
        "n_valid": 0,
        "candidates": [],
        "metrics": {},
        "predictions": [],
    }
    if not isinstance(response, dict):
        out["envelope_reasons"].append("response is not a JSON object")
        return out

    if kind in ("design", "tertiary"):
        cands = response.get("candidates")
        if not isinstance(cands, list) or not cands:
            out["envelope_reasons"].append("missing/empty candidates list")
            return out
        out["n_candidates"] = len(cands)
        for c in cands:
            if kind == "tertiary":
                struct = (c.get("structure") or "").strip()
                if not struct:
                    out["candidates"].append(
                        {"valid": False, "reasons": ["no structure payload"], "recomputed": {}}
                    )
                    continue
                text = struct
                path = Path(struct)
                # echo guard: submitting an input fixture (path or content) is
                # not a designed artifact (the registered integrity rule)
                echoed = None
                for fk in FILE_PARAM_KEYS:
                    fv = params.get(fk)
                    if isinstance(fv, str) and fv:
                        fpath = Path(fv)
                        if not fpath.is_absolute():
                            fpath = PROJECT_ROOT / fpath
                        if path.is_file() and fpath.is_file() and path.resolve() == fpath.resolve():
                            echoed = f"echoed input fixture {fk}"
                        elif fpath.is_file() and struct.replace("\n", "") == fpath.read_text(encoding="utf-8", errors="replace").replace("\n", ""):
                            echoed = f"echoed input fixture content ({fk})"
                if path.is_file() and not echoed:
                    text = path.read_text(encoding="utf-8", errors="replace")
                n_res = parse_pdb_residues(text)
                valid = n_res > 0 and not echoed
                rec = {"n_residues": n_res}
                if path.is_file():
                    rec["structure_path"] = str(path)
                if echoed:
                    rec["echoed_input"] = True
                out["candidates"].append(
                    {
                        "valid": valid,
                        "reasons": [echoed] if echoed else ([] if n_res else ["PDB payload has no parseable residues"]),
                        "recomputed": rec,
                    }
                )
            else:
                out["candidates"].append(check_candidate(workflow, params, c))
        out["n_valid"] = sum(1 for c in out["candidates"] if c["valid"])
        out["delivered"] = out["n_valid"] >= 1
    elif kind == "scoring":
        metrics = response.get("metrics")
        if not isinstance(metrics, dict) or not metrics:
            out["envelope_reasons"].append("missing metrics block")
            return out
        out["metrics"] = metrics
        seq = params.get("sequence") or ""
        rec = {
            "gc_content": gc_content(seq),
            "length": len(normalize_rna(seq)),
        }
        out["recomputed"] = rec
        out["delivered"] = True
    elif kind == "small_molecule":
        metrics = response.get("metrics") or {}
        p = metrics.get("binding_probability")
        if not isinstance(p, (int, float)):
            out["envelope_reasons"].append("missing binding_probability")
            return out
        out["metrics"] = {"binding_probability": p}
        out["delivered"] = True
    elif kind == "ires":
        preds = response.get("predictions")
        if response.get("negative_answer") and preds == []:
            # registered symmetric rule (2026-09-14, unified n=96): a complete
            # negative answer ("no regions above threshold") is a delivered
            # turn — the platform's IRES workflow returns exactly this form
            # on threshold-negative turns, so every arm may answer negatively
            # the same way
            out["predictions"] = []
            out["delivered"] = True
            return out
        if not isinstance(preds, list) or not preds:
            out["envelope_reasons"].append("missing predictions list")
            return out
        out["predictions"] = preds
        out["delivered"] = True
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 5. Claim adjudication (e3/exp5 rules, generalized; registered)
# ══════════════════════════════════════════════════════════════════════════════

# Tolerances (registered): fractions ±0.01; CAI ±0.01; energies ±1.0 kcal/mol.
CLAIM_TOLERANCES = {"default": 0.01, "cai": 0.01, "mfe_kcal_mol": 1.0}

# Metrics recomputable locally from delivered content (admissible truth).
RECOMPUTABLE = {"gc_content", "u_content", "length", "cai", "mfe_kcal_mol"}

# Metrics with NO admissible truth basis (family oracles chance-level or
# enforce-gated — DECISIONS (e)/(l)): claims on them are unverifiable for
# every arm, symmetrically.
UNVERIFIABLE_METRICS = {
    "binding_probability",
    "ires_probability",
    "binding_affinity",
    "mrl",
    "stability_score",
    "accessibility",
    "specificity",
    "off_target_risk",
}


def u_content(seq: str) -> float | None:
    s = normalize_rna(seq)
    return s.count("U") / len(s) if s else None


def _claims_iter(response: dict[str, Any]) -> list[dict[str, Any]]:
    cl = response.get("claims")
    return cl if isinstance(cl, list) else []


# Deterministic language rule (registered): a claim with no metric anchor is
# "unverifiable" when its text asserts an artifact property or a comparative /
# quantitative superiority (binding, affinity, specificity, stability, scores,
# optimality, numbers); purely descriptive process statements stay borderline.
_UNVERIFIABLE_LANGUAGE = re.compile(
    r"\d|bind|affinit|specific|optimi|superior|better|best|improv|high|low|"
    r"strong|stab|accessib|off[- ]target|score|efficien|accurat|fold|structur",
    re.IGNORECASE,
)


def _claim_is_unverifiable_language(claim: dict[str, Any]) -> bool:
    text = str(claim.get("text", ""))
    return bool(_UNVERIFIABLE_LANGUAGE.search(text))


def adjudicate_claims(
    workflow: str,
    params: dict[str, Any],
    response: dict[str, Any],
    checks: dict[str, Any],
) -> list[dict[str, Any]]:
    """Per-claim deterministic verdicts: TP / FP / unverifiable / borderline.

    Rules (generalized from the e3 blind adjudicator, exp5 L462-496):
    - metric claims: exact recomputation from the delivered sequence when the
      metric is recomputable (asserted value within tolerance); CAI / MFE
      values come from the audited tool pass (``complete_tool_metrics``);
      mismatch or missing payload -> FP ("unverifiable" never rescues an
      asserted number on a recomputable metric);
    - ranking claims (asserted_best_id over the arm's own candidates):
      recomputed only when the declared metric is recomputable — the asserted
      best must be the recomputed argmax/argmin over the delivered set;
    - screening claims: same logic with a threshold if given in text;
    - metric/ranking/screening claims on UNVERIFIABLE_METRICS, and 'other'
      quantitative claims without a metric anchor -> unverifiable;
    - everything else -> borderline (excluded from the rate denominator).
    """
    verdicts: list[dict[str, Any]] = []
    cands = response.get("candidates") if isinstance(response.get("candidates"), list) else []
    seqs = {
        c.get("id"): normalize_rna(c.get("sequence", "") or "") for c in cands if isinstance(c, dict)
    }
    all_seqs = list(seqs.values())
    # tool-completed per-candidate metrics, aligned to the response order
    index_by_id = {c.get("id"): i for i, c in enumerate(cands) if isinstance(c, dict)}
    tool_by_id: dict[str, dict[str, float]] = {}
    for cid, idx in index_by_id.items():
        rec = (checks.get("candidates") or [{}] * len(cands))[idx].get("recomputed") if idx < len(checks.get("candidates") or []) else {}
        tool_by_id[cid] = {k: float(rec[k]) for k in ("cai", "mfe_kcal_mol") if isinstance(rec.get(k), (int, float))}
    whole = checks.get("recomputed") or {}

    def _recompute(metric: str, seq: str, cid: str | None = None) -> float | None:
        if metric == "gc_content":
            return gc_content(seq)
        if metric == "u_content":
            return u_content(seq)
        if metric == "length":
            return float(len(seq)) if seq else None
        if metric == "cai":
            if cid and cid in tool_by_id and "cai" in tool_by_id[cid]:
                return tool_by_id[cid]["cai"]
            if isinstance(whole.get("cai"), (int, float)):
                return float(whole["cai"])
            return None
        if metric == "mfe_kcal_mol":
            if cid and cid in tool_by_id and "mfe_kcal_mol" in tool_by_id[cid]:
                return tool_by_id[cid]["mfe_kcal_mol"]
            if isinstance(whole.get("mfe_kcal_mol"), (int, float)):
                return float(whole["mfe_kcal_mol"])
            return None
        return None

    for claim in _claims_iter(response):
        if not isinstance(claim, dict):
            verdicts.append({"verdict": "borderline", "reason": "malformed claim object"})
            continue
        ctype = claim.get("claim_type")
        metric = claim.get("metric")
        out = {
            "claim_id": claim.get("claim_id"),
            "claim_type": ctype,
            "metric": metric,
            "verdict": None,
            "reason": None,
        }
        if metric in UNVERIFIABLE_METRICS:
            out.update(verdict="unverifiable", reason=f"metric {metric} has no admissible truth basis")
            verdicts.append(out)
            continue
        if metric in (None, "none", "null", ""):
            if _claim_is_unverifiable_language(claim):
                out.update(verdict="unverifiable", reason="assertion without a recomputable metric anchor")
            else:
                out.update(verdict="borderline", reason="descriptive statement, not a quantitative claim")
            verdicts.append(out)
            continue
        if metric not in RECOMPUTABLE:
            out.update(verdict="borderline", reason=f"metric {metric!r} not covered by deterministic rules")
            verdicts.append(out)
            continue
        tol = CLAIM_TOLERANCES.get(metric, CLAIM_TOLERANCES["default"])
        if ctype == "metric":
            asserted = claim.get("asserted_value")
            pool = all_seqs or ([normalize_rna(params.get("sequence", "") or "")] if params.get("sequence") else [])
            if not pool:
                out.update(verdict="FP", reason="no delivered sequence to recompute against")
            else:
                # recomputable-over-set: verified if ANY delivered sequence
                # matches the asserted value within tolerance (the claim
                # refers to the arm's deliverable, not a specific candidate
                # unless asserted_best_id names one)
                target_id = claim.get("asserted_best_id")
                if target_id and target_id in seqs:
                    chosen = [(target_id, seqs[target_id])]
                else:
                    chosen = list(seqs.items()) or [(None, normalize_rna(params.get("sequence", "") or ""))]
                vals = [v for v in (_recompute(metric, s, cid) for cid, s in chosen) if v is not None]
                if not vals:
                    out.update(verdict="FP", reason=f"metric {metric} not recomputable from payload")
                elif asserted is None or not any(abs(float(asserted) - v) <= tol for v in vals):
                    out.update(verdict="FP", reason=f"asserted {asserted} vs recomputed {[round(v, 4) for v in vals]} (tol {tol})")
                else:
                    out.update(verdict="TP", reason=f"verified: {metric}={vals[0]:.4f} (within tol)")
        elif ctype in ("ranking", "screening"):
            basis = claim.get("basis")
            target_id = claim.get("asserted_best_id")
            if not all_seqs:
                out.update(verdict="FP", reason="ranking/screening claim with no delivered candidates")
            elif basis not in ("self_computation",):
                out.update(verdict="unverifiable", reason="no declared deterministic basis")
            elif target_id not in seqs:
                out.update(verdict="FP", reason=f"asserted best {target_id} not among delivered candidates")
            else:
                vals = {cid: _recompute(metric, s, cid) for cid, s in seqs.items()}
                vals = {k: v for k, v in vals.items() if v is not None}
                if not vals:
                    out.update(verdict="FP", reason=f"metric {metric} not recomputable")
                else:
                    best = max(vals, key=vals.get) if metric in ("gc_content", "u_content", "cai", "length") else min(vals, key=vals.get)
                    if target_id != best:
                        out.update(verdict="FP", reason=f"asserted best {target_id} != recomputed {('max' if metric != 'mfe_kcal_mol' else 'min')} {best}")
                    else:
                        out.update(verdict="TP", reason=f"best candidate matches recomputed {metric}")
        else:
            out.update(verdict="borderline", reason=f"claim_type {ctype!r} not covered")
        verdicts.append(out)
    return verdicts


# ── platform reference quality (frozen Exp-41, for the parity bars) ──────────
#
# Registered rule: for the two structure workflows whose quality IS a
# deterministic recomputation, a baseline candidate "delivers" only at parity
# with the frozen platform arm's own best candidate on the SAME task+turn:
#   secondary structure — base-pair distance <= platform best distance;
#   tertiary structure  — TM-score >= platform best TM (tol 1e-3).
# No thresholds are invented; the platform's measured quality is the bar.


def platform_reference_quality() -> dict[str, list[dict[str, float]]]:
    """{pa_id: [per-turn reference fields, ...]} — the frozen platform best.

    Fields: structure_distance (min), alignment_tm_score (max),
    sirna_best_complementary (0/1 — majority of the platform's own candidates
    on that turn are target-complementary), sgrna_best_hamming_to_seed (min
    over length-matching candidates). The parity bars consume these: a
    baseline candidate delivers only at the platform's own measured quality
    on the SAME task+turn; no thresholds are invented.
    """
    task_params: dict[str, list[dict]] = {t["pa_id"]: t["turns"] for t in load_pa_tasks()}
    out: dict[str, list[dict[str, float]]] = {}
    for line in EXP41_BLOCK_A.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("arm") != "full" or rec.get("pilot"):
            continue
        pa_id = f"PA_{int(rec['pa_id']):03d}"
        files = []
        for sd in sorted(SESSIONS_ROOT.glob(f"exp41_full_pa{int(rec['pa_id']):03d}_*")):
            files.extend(sd.glob("workflow_results_*.json"))
        loaded = []
        for f in files:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            loaded.append((d.get("timestamp") or "", d))
        loaded.sort(key=lambda x: x[0])
        turns_params = task_params.get(pa_id) or []
        turns: list[dict[str, float]] = []
        for i, (_, d) in enumerate(loaded):
            cands = d.get("candidates") or []
            params = turns_params[i] if i < len(turns_params) else {}
            best: dict[str, float] = {}
            dists = [
                c["scores"]["structure_distance"]
                for c in cands
                if isinstance(c.get("scores", {}).get("structure_distance"), (int, float))
            ]
            if dists:
                best["structure_distance"] = float(min(dists))
            tms = [
                c["scores"]["alignment_tm_score"]
                for c in cands
                if isinstance(c.get("scores", {}).get("alignment_tm_score"), (int, float))
            ]
            if tms:
                best["alignment_tm_score"] = float(max(tms))
            if params.get("target_sequence"):
                target = normalize_rna(params["target_sequence"])
                comp = sum(
                    1
                    for c in cands
                    if revcomp(normalize_rna(c.get("sequence", "") or "")) in target
                    or normalize_rna(c.get("sequence", "") or "") in target
                )
                if cands:
                    best["sirna_best_complementary"] = float(comp >= max(1, (len(cands) + 1) // 2))
            seed = normalize_rna(params.get("seed_sequence", "") or "")
            if seed and cands:
                hams = [
                    sum(a != b for a, b in zip(normalize_rna(c.get("sequence", "") or ""), seed))
                    for c in cands
                    if len(normalize_rna(c.get("sequence", "") or "")) == len(seed)
                ]
                if hams:
                    best["sgrna_best_hamming_to_seed"] = float(min(hams))
            turns.append(best)
        out[pa_id] = turns
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 5b. Tool-layer metric completion (audited; CAI local Kazusa, LinearFold 8015)
# ══════════════════════════════════════════════════════════════════════════════


def dotbracket_pairs(structure: str) -> set[tuple[int, int]]:
    """exp4's dot-bracket pair extractor (verbatim semantics)."""
    stack: list[int] = []
    pairs: set[tuple[int, int]] = set()
    for i, ch in enumerate(structure):
        if ch == "(":
            stack.append(i)
        elif ch == ")":
            if stack:
                j = stack.pop()
                pairs.add((j, i))
    return pairs


def base_pair_distance(a: str, b: str) -> int | None:
    """exp4's base-pair distance (verbatim semantics)."""
    if len(a) != len(b):
        return None
    pa, pb = dotbracket_pairs(a), dotbracket_pairs(b)
    return len(pa ^ pb)


def _write_scratch_fasta(scratch: Path, name: str, seq: str) -> Path:
    scratch.mkdir(parents=True, exist_ok=True)
    p = scratch / f"{name}.fa"
    p.write_text(f">{name}\n{normalize_rna(seq)}\n", encoding="utf-8")
    return p


def _run_tool(executor, name: str, **kwargs) -> dict[str, Any] | None:
    res = executor.run_tool(name, **kwargs)
    if not res.success:
        return None
    raw = res.artifacts.get("result")
    return raw if isinstance(raw, dict) else None


def complete_tool_metrics(
    executor,
    workflow: str,
    params: dict[str, Any],
    checks: dict[str, Any],
    response: dict[str, Any],
    scratch: Path,
    ref_turn: dict[str, float] | None = None,
) -> None:
    """Fill cai / mfe / fold-back / TM recomputations into ``checks`` in place.

    Runs through ``ToolExecutor.run_tool`` (platform audit trail): CAI via
    the local Kazusa table (``compute_cai_for_cds_sequence``), fold via the
    LinearFold service (``predict_rna_secondary_structure_with_linearfold``),
    tertiary TM via ``score_structure_alignment``. Applies the registered
    parity bars for the two structure workflows when ``ref_turn`` (the
    frozen platform per-turn best) is given.
    """
    species = params.get("cai_species", "Homo sapiens")
    kind = CONTRACT_BY_WORKFLOW[workflow]

    if kind == "scoring":
        seq = normalize_rna(params.get("sequence", "") or "")
        if seq:
            fp = _write_scratch_fasta(scratch, "scoring_input", seq)
            cai = _run_tool(executor, "compute_cai_for_cds_sequence", filepath=str(fp), species=species)
            if cai and isinstance(cai.get("cai_score"), (int, float)):
                checks["recomputed"]["cai"] = float(cai["cai_score"])
            fold = _run_tool(executor, "predict_rna_secondary_structure_with_linearfold", filepath=str(fp))
            if fold and isinstance(fold.get("mfe"), (int, float)):
                checks["recomputed"]["mfe_kcal_mol"] = float(fold["mfe"])
        return

    if kind in ("design", "tertiary"):
        cands = [
            c if isinstance(c, dict) else {}
            for c in (response.get("candidates") or [])
        ]
        seqs = [normalize_rna(c.get("sequence", "") or "") for c in cands]
        for i, seq in enumerate(seqs):
            rec = checks["candidates"][i]["recomputed"] if i < len(checks["candidates"]) else {}
            if not seq:
                continue
            cds = rec.get("cai_candidate_cds") or (seq if workflow == "mrna_cds_design" else None)
            if workflow in ("mrna_cds_design", "full_length_mrna_design") and cds:
                if len(cds) % 3 == 0 and set(normalize_rna(cds)) <= _RNA_ALPHA:
                    fp = _write_scratch_fasta(scratch, f"cand{i}_cds", cds)
                    cai = _run_tool(executor, "compute_cai_for_cds_sequence", filepath=str(fp), species=species)
                    if cai and isinstance(cai.get("cai_score"), (int, float)):
                        rec["cai"] = float(cai["cai_score"])
            if workflow == "rna_secondary_structure_design" and params.get("target_structure"):
                if len(seq) <= 8000:
                    fp = _write_scratch_fasta(scratch, f"cand{i}", seq)
                    fold = _run_tool(executor, "predict_rna_secondary_structure_with_linearfold", filepath=str(fp))
                    if fold and isinstance(fold.get("structure"), str):
                        rec["folded_structure_mfe"] = fold.get("mfe")
                        rec["base_pair_distance_to_target"] = base_pair_distance(
                            fold["structure"], params["target_structure"]
                        )
        if workflow == "rna_tertiary_structure_design" and params.get("structure_filepath"):
            ref_pdb = Path(params["structure_filepath"])
            if not ref_pdb.is_absolute():
                ref_pdb = PROJECT_ROOT / ref_pdb
            for i, c in enumerate(cands):
                rec = checks["candidates"][i]["recomputed"] if i < len(checks["candidates"]) else {}
                sp = rec.get("structure_path")
                if not sp:
                    continue
                aln = _run_tool(
                    executor,
                    "score_structure_alignment",
                    reference_pdb_filepath=str(ref_pdb),
                    predicted_pdb_filepath=str(sp),
                )
                if aln:
                    for key in ("tm_score", "alignment_tm_score"):
                        if isinstance(aln.get(key), (int, float)):
                            rec["alignment_tm_score"] = float(aln[key])
                            break

        # registered parity bars (platform frozen best = the bar)
        if ref_turn:
            if workflow == "rna_secondary_structure_design" and isinstance(
                ref_turn.get("structure_distance"), (int, float)
            ):
                dists = [
                    c.get("recomputed", {}).get("base_pair_distance_to_target")
                    for c in checks["candidates"]
                ]
                dists = [d for d in dists if isinstance(d, (int, float))]
                best = min(dists) if dists else None
                checks["parity"] = {
                    "platform_best_structure_distance": float(ref_turn["structure_distance"]),
                    "arm_best_base_pair_distance": best,
                }
                if best is None or best > float(ref_turn["structure_distance"]):
                    checks["delivered"] = False
                    checks["envelope_reasons"].append(
                        f"fold-back distance {best} > platform best {ref_turn['structure_distance']} (parity bar)"
                    )
            if workflow == "rna_tertiary_structure_design" and isinstance(
                ref_turn.get("alignment_tm_score"), (int, float)
            ):
                tms = [
                    c.get("recomputed", {}).get("alignment_tm_score")
                    for c in checks["candidates"]
                ]
                tms = [t for t in tms if isinstance(t, (int, float))]
                best = max(tms) if tms else None
                checks["parity"] = {
                    "platform_best_alignment_tm_score": float(ref_turn["alignment_tm_score"]),
                    "arm_best_alignment_tm_score": best,
                }
                if best is None or best < float(ref_turn["alignment_tm_score"]) - 1e-3:
                    checks["delivered"] = False
                    checks["envelope_reasons"].append(
                        f"TM-score {best} < platform best {ref_turn['alignment_tm_score']} (parity bar)"
                    )
            if workflow == "sirna_design" and ref_turn.get("sirna_best_complementary"):
                comp = [
                    1
                    for c in checks["candidates"]
                    if c.get("recomputed", {}).get("complementary_to_target")
                    or c.get("recomputed", {}).get("exact_target_match")
                ]
                checks["parity"] = {
                    "platform_complementary": True,
                    "arm_any_complementary": bool(comp),
                }
                if not comp:
                    checks["delivered"] = False
                    checks["envelope_reasons"].append(
                        "no candidate complementary/matching the target (platform candidates are)"
                    )
            if workflow == "sgrna_design" and isinstance(
                ref_turn.get("sgrna_best_hamming_to_seed"), (int, float)
            ):
                hams = [
                    c.get("recomputed", {}).get("hamming_to_seed")
                    for c in checks["candidates"]
                ]
                hams = [h for h in hams if isinstance(h, (int, float))]
                best_h = min(hams) if hams else None
                checks["parity"] = {
                    "platform_best_hamming_to_seed": float(ref_turn["sgrna_best_hamming_to_seed"]),
                    "arm_best_hamming_to_seed": best_h,
                }
                if best_h is None or best_h > float(ref_turn["sgrna_best_hamming_to_seed"]):
                    checks["delivered"] = False
                    checks["envelope_reasons"].append(
                        f"crRNA Hamming-to-seed {best_h} > platform best {ref_turn['sgrna_best_hamming_to_seed']} (parity bar)"
                    )


def tool_metric_lookup(checks: dict[str, Any]) -> dict[str, float]:
    """Flatten the tool-completed recomputations for claim adjudication."""
    out: dict[str, float] = {}
    r = checks.get("recomputed") or {}
    for k in ("cai", "mfe_kcal_mol"):
        if isinstance(r.get(k), (int, float)):
            out[k] = float(r[k])
    per_cand: list[float] = []
    for c in checks.get("candidates") or []:
        rec = c.get("recomputed") or {}
        for k in ("cai", "mfe_kcal_mol"):
            if isinstance(rec.get(k), (int, float)):
                per_cand.append(float(rec[k]))
    if per_cand:
        out["_per_candidate_tool_metrics"] = per_cand  # type: ignore[assignment]
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 6. Shared record conventions
# ══════════════════════════════════════════════════════════════════════════════


def utc_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True, default=str) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def parse_json_object(text: str) -> dict[str, Any]:
    """exp5's tolerant JSON extractor (verbatim semantics)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else {"_raw": cleaned}
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                obj = json.loads(cleaned[start : end + 1])
                return obj if isinstance(obj, dict) else {"_raw": cleaned}
            except json.JSONDecodeError:
                pass
    return {"_parse_error": True, "_raw": cleaned[:2000]}
