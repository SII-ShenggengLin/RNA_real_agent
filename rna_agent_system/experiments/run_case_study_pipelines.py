#!/usr/bin/env python3
"""Fig 7 driver: real-world end-to-end case studies (MANUSCRIPT §9).

Three chained cases. Chaining is done driver-side per the §1.2 implementation
checkpoint: node 1 runs through the CLI, its session `workflow_results_*.json`
is parsed, node-2 params are written from the extracted fields, then node 2
runs. (`--pipeline-file` is intentionally NOT used: `pipeline_results` comes
from `PipelineResult.model_dump()`, which drops the ad-hoc `_state_writeback`
details the case summaries need.)

- Case A — SARS-CoV-2 Spike mRNA vaccine candidate
    node1  full_length_mrna_design (stability-first reference point per §5.2,
           bmc_max_rounds=2)
    node2  ires_prediction on the designed 5'UTR (safety screen)
    anchor overlay: BNT162b2 / mRNA-1273 metrics from fig3_anchors.json
- Case B — Anti-VEGF aptamer discovery
    node1  rna_aptamer_design on 1VPF (bmc_max_rounds=2)
    node2  interface re-render of the top candidate (extraction only, no run)
    anchor: pegaptanib scored through the same RhoFold→ProteinX→EGARPS chain
- Case C — SARS-CoV-2 NSP12 siRNA therapy
    node1  sirna_design with the PA_016 turn-1 params verbatim. NOTE: PA_016
           uses mode="antiviral"; MANUSCRIPT §9 says "generic mode". The
           curated benchmark input is used as-is (it already includes the
           Bowtie2 off-target screen Case C needs) and the discrepancy is
           recorded in the summary's `notes`.
    node2  safety-ranked candidate table + published design-rule thresholds
           (GC 30–60 % per §9; duplex MFE is reported descriptively — the
           manual names no numeric ΔG window, so none is invented here).

Output per case: `experiments/results/fig7_cases/<case>/nodes.jsonl`
(one record per node run) + `case_summary.json`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_case_study_pipelines.py \
        [--case A|B|C] [--resume] [--timeout SEC] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT, run_task_dict  # noqa: E402
from run_bmc_type2_ablation import find_structure  # noqa: E402
from run_reference_point_steering import (  # noqa: E402
    DEFAULT_POOL_JSONL,
    build_pools,
    build_reference_point,
    format_ref,
    reference_point_to_params,
)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "fig7_cases"
TARGETS_MRNA = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
FIG3_ANCHORS = PROJECT_ROOT / "experiments" / "results" / "fig3_anchors.json"
PA_BENCHMARKS = PROJECT_ROOT / "pa_benchmarks.json"

# Published siRNA design-rule thresholds (MANUSCRIPT §9 Case C anchor).
# GC window from the manual; duplex MFE has no pinned window in the manual or
# in a single canonical source, so it is reported descriptively only.
SIRNA_GC_WINDOW = (0.30, 0.60)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def case_dir(case: str) -> Path:
    d = RESULTS_DIR / case
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_done_nodes(nodes_jsonl: Path) -> set[str]:
    done = set()
    if nodes_jsonl.exists():
        for line in nodes_jsonl.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                done.add(r["node_id"])
    return done


def latest_node_record(nodes_jsonl: Path, node_id: str) -> dict | None:
    """Latest record for one node_id in a nodes.jsonl (None if absent).

    NOTE (2026-07-30, lossless-resume fix): resume-triggered summary rebuilds
    previously blanked node metadata — resumed-skip returned bare stubs, so
    `elapsed_seconds` became None (timeline_seconds collapsed to 0) and the
    Case-B pegaptanib_anchor scoring outputs were lost when the sweep rewrote
    case_summary.json. Restoring the prior record's fields from nodes.jsonl
    keeps rebuilds lossless; the anchor node now also persists `outputs` into
    nodes.jsonl at write time (see run_case_b).
    """
    latest: dict | None = None
    if nodes_jsonl.exists():
        for line in nodes_jsonl.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("node_id") == node_id:
                latest = r
    return latest


def append_node_record(nodes_jsonl: Path, record: dict) -> None:
    with nodes_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def run_node(
    case: str,
    node_id: str,
    workflow: str,
    params: dict,
    *,
    timeout: int,
    env: dict,
    resume_done: set[str],
    extract=None,
) -> dict:
    """Run one case node (or skip on --resume) and return a result dict.

    ``extract`` maps the session's latest workflow_results dict to node-specific
    outputs; it also runs on resumed nodes so summaries can be rebuilt.
    """
    if node_id in resume_done:
        print(f"    [{node_id}] resumed-skip", flush=True)
        session_id = f"fig7{case}_fig7{case}_{node_id}"
        results = latest_workflow_results(session_id)
        out = {"node_id": node_id, "success": True, "session_id": session_id, "resumed": True}
        # Lossless-resume fix (2026-07-30): restore the prior record's fields
        # so summary rebuilds keep elapsed_seconds/outputs (see NOTE above).
        prior = latest_node_record(case_dir(case) / "nodes.jsonl", node_id) or {}
        for k in ("elapsed_seconds", "timestamp", "error"):
            if prior.get(k) is not None:
                out[k] = prior[k]
        if prior.get("outputs") is not None:
            out["outputs"] = prior["outputs"]
        elif extract is not None and results is not None:
            out["outputs"] = extract(results)
        return out

    task = {
        "task_id": f"fig7{case}_{node_id}",
        "workflow": workflow,
        "category": f"fig7_case_{case}",
        "description": f"fig7 case {case} node {node_id}",
        "input": params,
        "evaluation_rubric": None,
    }
    print(f"    [{node_id}] {workflow} ...", flush=True)
    rec = run_task_dict(task, timeout=timeout, env=env, session_prefix=f"fig7{case}")
    record = {
        "case": case,
        "node_id": node_id,
        "workflow": workflow,
        "params": params,
        "session_id": rec.get("session_id"),
        "success": rec["success"],
        "error": rec.get("error"),
        "elapsed_seconds": rec.get("elapsed_seconds"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    append_node_record(case_dir(case) / "nodes.jsonl", record)
    if not rec["success"]:
        return {"node_id": node_id, "success": False, "error": rec.get("error"),
                "elapsed_seconds": rec.get("elapsed_seconds")}
    result = {"node_id": node_id, "success": True,
              "elapsed_seconds": rec.get("elapsed_seconds"),
              "session_id": rec.get("session_id")}
    if extract is not None:
        result["outputs"] = extract(latest_workflow_results(rec.get("session_id")) or {})
    return result


def latest_workflow_results(session_id: str) -> dict | None:
    """Load the newest workflow_results_*.json of a session (None if missing)."""
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    files = sorted(session_dir.glob("workflow_results_*.json")) if session_dir.is_dir() else []
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def results_of(node_result: dict) -> dict | None:
    """Load the session results dict of a finished node."""
    return latest_workflow_results(node_result.get("session_id") or "")


# ---------------------------------------------------------------------------
# Case A — Spike mRNA vaccine candidate
# ---------------------------------------------------------------------------

def spike_stability_first_params(pool_jsonl: list[Path], pool_json: Path | None) -> dict:
    """Build node-1 params for Case A (stability-first reference point, §5.2)."""
    meta = json.loads((TARGETS_MRNA / "SARS-CoV-2_Spike_WT.json").read_text())
    pools, missing = build_pools(["SARS-CoV-2_Spike_WT"], pool_jsonl, pool_json)
    if missing:
        raise RuntimeError(
            f"Case A reference-point pool missing for {missing} — wait for the "
            f"fig3 Serial (rounds=0) shard records or pass --pool-json."
        )
    ref = build_reference_point("stability-first", pools["SARS-CoV-2_Spike_WT"])
    params = {
        "protein_sequence": meta["protein_sequence"].upper(),
        "design_tool": "all",
        "lambda_value": 2.0,
        "cai_species": meta.get("species_for_codon_optimization") or "human",
        "utr_mode": "all",
        "bmc_max_rounds": 2,
        "bmc_improvement_threshold": 0.05,
    }
    params.update(reference_point_to_params(ref))
    return params


def extract_designed_mrna_metrics(results: dict) -> dict:
    """Anchor-comparable metrics of the designed best candidate (Case A overlay)."""
    best = (results.get("best_candidate") or {})
    s = best.get("scores") or {}
    m = best.get("metadata") or {}
    return {
        "candidate_id": best.get("id"),
        "cds_cai": s.get("cds_cai"),
        "cds_mfe": s.get("cds_mfe"),
        "cds_mfe_per_nt": (s.get("cds_mfe") / s.get("cds_length"))
        if isinstance(s.get("cds_mfe"), (int, float)) and s.get("cds_length") else None,
        "utr5_mrl": s.get("utr5_predicted_mrl", s.get("utr5_mrl")),
        "utr3_stability": s.get("utr3_predicted_stability", s.get("utr3_stability")),
        "full_mfe_per_nt": s.get("full_mfe_per_nt"),
        "junction_5utr_cds_mfe": s.get("junction_5utr_cds_mfe"),
        "junction_cds_3utr_mfe": s.get("junction_cds_3utr_mfe"),
        "junction_5utr_cds_aug_buried": s.get("junction_5utr_cds_aug_buried"),
        "junction_5utr_cds_kozak_buried": s.get("junction_5utr_cds_kozak_buried"),
        "utr5_preset": m.get("utr5_preset"),
        "utr3_preset": m.get("utr3_preset"),
        "total_length": best.get("total_length"),
    }


def build_anchor_overlay(designed: dict, anchors: dict) -> list[dict]:
    """Side-by-side metric table: designed candidate vs vaccine anchors."""
    rows = []
    for name, a in anchors.items():
        if not isinstance(a, dict):
            continue
        rows.append({
            "molecule": name,
            "cds_cai": (a.get("cds") or {}).get("cai_score"),
            "cds_mfe_per_nt": (a.get("cds") or {}).get("mfe_per_nt"),
            "utr5_mrl": (a.get("utr5") or {}).get("predicted_mrl"),
            "utr3_stability": (a.get("utr3") or {}).get("predicted_stability"),
            "full_mfe_per_nt": (a.get("full_length") or {}).get("mfe_per_nt"),
            "junction_5utr_cds_mfe": (a.get("junction_5utr_cds") or {}).get("mfe_kcal"),
            "junction_cds_3utr_mfe": (a.get("junction_cds_3utr") or {}).get("mfe_kcal"),
            "junction_5utr_cds_aug_buried": (a.get("junction_5utr_cds") or {}).get("aug_buried"),
            "junction_5utr_cds_kozak_buried": (a.get("junction_5utr_cds") or {}).get("kozak_buried"),
        })
    rows.insert(0, {"molecule": "designed_case_a", **{k: designed.get(k) for k in [
        "cds_cai", "cds_mfe_per_nt", "utr5_mrl", "utr3_stability", "full_mfe_per_nt",
        "junction_5utr_cds_mfe", "junction_cds_3utr_mfe",
        "junction_5utr_cds_aug_buried", "junction_5utr_cds_kozak_buried"]}})
    return rows


def run_case_a(env: dict, timeout: int, resume_done: set[str], dry_run: bool,
               pool_jsonl: list[Path], pool_json: Path | None) -> dict:
    try:
        params1 = spike_stability_first_params(pool_jsonl, pool_json)
    except RuntimeError as exc:
        if dry_run:
            print(f"    [design] pool unavailable (dry-run continues): {exc}")
            params1 = {"_note": "stability-first params could not be built yet"}
        else:
            raise
    if dry_run:
        print(f"    [design] full_length_mrna_design params: {json.dumps({k: (str(v)[:60]) for k, v in params1.items()})}")
        print("    [ires_scan] ires_prediction on designed 5'UTR (sequence_filepath from node1 best)")
        return {"case": "A", "dry_run": True}

    n1 = run_node("A", "design", "full_length_mrna_design", params1,
                  timeout=timeout, env=env, resume_done=resume_done)
    if not n1.get("success"):
        return {"case": "A", "nodes": [n1], "success": False}
    res1 = results_of(n1) or {}
    designed = extract_designed_mrna_metrics(res1)
    utr5_seq = (((res1.get("best_candidate") or {}).get("metadata") or {}).get("utr5_sequence"))

    nodes = [dict(n1, _rec=None)]
    if not utr5_seq:
        nodes.append({"node_id": "ires_scan", "success": False,
                      "error": "no utr5_sequence in node1 best candidate metadata"})
    else:
        fa = case_dir("A") / "designed_utr5.fa"
        fa.write_text(f">designed_utr5_case_a\n{utr5_seq}\n", encoding="utf-8")
        params2 = {
            "sequence_filepath": str(fa),
            "iresfinder_mode": 0,
            "probability_threshold": 0.5,
            "top_n_candidates": 5,
            "run_structural_validation": False,
        }
        n2 = run_node("A", "ires_scan", "ires_prediction", params2,
                      timeout=timeout, env=env, resume_done=resume_done,
                      extract=extract_ires_outputs)
        nodes.append(dict(n2, _rec=None))

    anchors = json.loads(FIG3_ANCHORS.read_text()) if FIG3_ANCHORS.exists() else {}
    summary = {
        "case": "A",
        "title": "SARS-CoV-2 Spike mRNA vaccine candidate",
        "success": all(n.get("success") for n in nodes),
        "nodes": [{k: v for k, v in n.items() if not k.startswith("_")} for n in nodes],
        "designed_best": designed,
        "anchor_overlay": build_anchor_overlay(designed, anchors),
        "timeline_seconds": sum(n.get("elapsed_seconds") or 0 for n in nodes),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    return summary


def extract_ires_outputs(results: dict) -> dict:
    """Key fields of the ires_prediction safety screen."""
    cands = results.get("candidates") or []
    best = results.get("best_candidate") or {}
    return {
        "candidate_count": results.get("candidate_count"),
        "best_scores": best.get("scores") or {},
        "top_probabilities": [
            (c.get("scores") or {}).get("ires_probability") for c in cands[:5]
        ],
    }


# ---------------------------------------------------------------------------
# Case B — Anti-VEGF aptamer discovery
# ---------------------------------------------------------------------------

def extract_interface_outputs(results: dict) -> dict:
    """Re-render data for the top candidate complex (Case B node 2, no run)."""
    best = (results.get("best_candidate") or {})
    s = best.get("scores") or {}
    m = best.get("metadata") or {}
    ranked = sorted(
        (results.get("candidates") or []),
        key=lambda c: (c.get("total_score") if c.get("total_score") is not None else float("-inf")),
        reverse=True,
    )
    return {
        "top_candidate": {
            "id": best.get("id"),
            "sequence": best.get("sequence"),
            "total_score": best.get("total_score"),
            "egarps_component": s.get("egarps_component"),
            "rhofold_component": s.get("rhofold_component"),
            "iptm_component": s.get("iptm_component"),
            "egarps_native_probability": s.get("egarps_native_probability"),
            "rhofold_mean_plddt": s.get("rhofold_mean_plddt"),
            "proteinx_ipTM": s.get("proteinx_ipTM"),
            "interface_contacts": s.get("interface_contacts"),
            "buried_sasa": s.get("buried_sasa"),
            "hydrogen_bonds": s.get("hydrogen_bonds"),
            "salt_bridges": s.get("salt_bridges"),
            "hotspot_residues": m.get("hotspot_residues"),
            "proteinx_pdb_path": s.get("proteinx_pdb_path"),
        },
        "candidate_count": results.get("candidate_count"),
        "top5_total_scores": [c.get("total_score") for c in ranked[:5]],
    }


def run_case_b(env: dict, timeout: int, resume_done: set[str], dry_run: bool) -> dict:
    from run_known_aptamer_validation import (  # lazy: pulls run_task_dict chain only
        load_pegaptanib,
        load_target_meta,
        score_aptamer_through_chain,
    )

    meta = load_target_meta("VEGF")
    struct = find_structure(meta["pdb_id"])
    chain = meta.get("pdb_chain") or "A"
    if struct is None:
        raise RuntimeError(f"Case B: no structure file for {meta['pdb_id']}")
    params1 = {
        "protein_structure_path": str(struct.relative_to(PROJECT_ROOT)),
        "chain_id": chain,
        "aptamer_length": 30,
        "n_odesign_samples": 8,
        "odesign_seeds": [42, 123],
        "bmc_max_rounds": 2,
        "bmc_improvement_threshold": 0.05,
    }
    peg = load_pegaptanib()
    peg_seq = (peg.get("sequence") or "").upper().replace("T", "U")
    if dry_run:
        print(f"    [design] rna_aptamer_design params: {json.dumps(params1)}")
        print(f"    [interface] extraction-only re-render from node1 session (no run)")
        print(f"    [anchor] pegaptanib ({len(peg_seq)} nt) via score_aptamer_through_chain on {struct.name} chain {chain}")
        return {"case": "B", "dry_run": True}

    n1 = run_node("B", "design", "rna_aptamer_design", params1,
                  timeout=timeout, env=env, resume_done=resume_done)
    if not n1.get("success"):
        return {"case": "B", "nodes": [n1], "success": False}
    interface = extract_interface_outputs(results_of(n1) or {})
    nodes = [dict(n1, _rec=None)]

    # Node 2: interface re-render is extraction-only (already computed above).
    nodes.append({"node_id": "interface", "success": True, "elapsed_seconds": 0,
                  "note": "extraction-only re-render of the node1 top candidate"})

    # Anchor: pegaptanib through the same scoring chain (direct capability calls).
    # NOTE (2026-07-30): this direct chain does NOT auto-start microservices
    # (there is no workflow pre-flight here). If RhoFold (8005) / ProteinX
    # (8022) / EGARPS (8023) are down — e.g. right after a machine restart —
    # the anchor scoring fails with connection-refused. Ensure them first via
    # agent_core.services.service_manager.ensure_services_ready (capability
    # keys: predict_rna_tertiary_structure_with_rhofold,
    # predict_rna_protein_complex_with_proteinx,
    # score_rna_protein_complex_with_egarps).
    anchor_record = {"node_id": "pegaptanib_anchor", "success": None}
    if "pegaptanib_anchor" not in resume_done:
        print("    [pegaptanib_anchor] scoring pegaptanib through RhoFold→ProteinX→EGARPS ...", flush=True)
        anchor = score_aptamer_through_chain("fig7b_pegaptanib", peg_seq, struct, chain, timeout=timeout)
        anchor_success = not any(
            str(v).startswith("failed") for v in (anchor.get("steps") or {}).values()
        )
        anchor_record = {
            "case": "B", "node_id": "pegaptanib_anchor", "workflow": "direct_capability_chain",
            "params": {"sequence": peg_seq, "structure": str(struct), "chain_id": chain},
            "success": anchor_success,
            "elapsed_seconds": anchor.get("elapsed_seconds"),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        # Persist outputs so later --resume rebuilds stay lossless (NOTE above).
        anchor_record["outputs"] = anchor
        append_node_record(case_dir("B") / "nodes.jsonl", anchor_record)
    else:
        print("    [pegaptanib_anchor] resumed-skip", flush=True)
        prior = latest_node_record(case_dir("B") / "nodes.jsonl", "pegaptanib_anchor") or {}
        anchor_record = {"node_id": "pegaptanib_anchor", "success": True, "resumed": True,
                         "note": "resumed; outputs restored from nodes.jsonl"}
        for k in ("elapsed_seconds", "timestamp", "outputs"):
            if prior.get(k) is not None:
                anchor_record[k] = prior[k]
    nodes.append(anchor_record)

    summary = {
        "case": "B",
        "title": "Anti-VEGF aptamer discovery",
        "success": all(n.get("success") for n in nodes),
        "nodes": [{k: v for k, v in n.items() if not k.startswith("_")} for n in nodes],
        "interface": interface,
        "pegaptanib_anchor": {
            "sequence": peg_seq,
            "kd": peg.get("kd"),
            "note": "unmodified parent sequence; 2'-F/2'-OMe/PEG of the drug product "
                    "cannot be represented (see pegaptanib.json notes)",
            "binding_site_residues": peg.get("binding_site_residues"),
            "data_gaps": ["pegaptanib binding_site_residues is null in the anchor file"
                          if not peg.get("binding_site_residues") else None],
        },
        "timeline_seconds": sum(n.get("elapsed_seconds") or 0 for n in nodes),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    summary["pegaptanib_anchor"]["data_gaps"] = [
        g for g in summary["pegaptanib_anchor"]["data_gaps"] if g
    ]
    return summary


# ---------------------------------------------------------------------------
# Case C — NSP12 siRNA therapy
# ---------------------------------------------------------------------------

def pa016_turn1_params() -> dict:
    pa = json.loads(PA_BENCHMARKS.read_text())
    entry = pa.get("016") or pa.get("PA_016")
    if not entry:
        raise RuntimeError("PA_016 not found in pa_benchmarks.json")
    return dict(entry["params_by_turn"][0])


def check_sirna_rules(candidate_scores: dict) -> dict:
    """Published design-rule thresholds for one siRNA candidate (§9 Case C)."""
    gc = candidate_scores.get("gc_content")
    gc_pass = None if gc is None else (SIRNA_GC_WINDOW[0] <= gc <= SIRNA_GC_WINDOW[1])
    return {
        "gc_content": gc,
        "gc_in_30_60_pct": gc_pass,
        "duplex_mfe": candidate_scores.get("duplex_mfe"),
        "duplex_mfe_note": "reported descriptively; no numeric ΔG window pinned in §9",
        "off_target_count": candidate_scores.get("off_target_count"),
        "specificity_score": candidate_scores.get("specificity_score"),
    }


def extract_sirna_safety_table(results: dict) -> list[dict]:
    """Safety-ranked candidate table (Case C node 2)."""
    rows = []
    for c in (results.get("candidates") or []):
        s = c.get("scores") or {}
        row = {
            "rank": c.get("rank"),
            "sequence": c.get("sequence"),
            "total_rank": s.get("total_rank"),
            "rank_mfe": s.get("rank_mfe"),
            "rank_offtarget": s.get("rank_offtarget"),
            "window_start": (c.get("metadata") or {}).get("window_start"),
        }
        row.update(check_sirna_rules(s))
        rows.append(row)
    rows.sort(key=lambda r: (r.get("total_rank") if r.get("total_rank") is not None else float("inf")))
    return rows


def run_case_c(env: dict, timeout: int, resume_done: set[str], dry_run: bool) -> dict:
    params1 = pa016_turn1_params()
    if dry_run:
        print(f"    [design] sirna_design params (PA_016 turn 1 verbatim): {json.dumps({k: (str(v)[:60]) for k, v in params1.items()})}")
        print("    [safety_table] extraction from node1 session + threshold check (no run)")
        return {"case": "C", "dry_run": True}

    n1 = run_node("C", "design", "sirna_design", params1,
                  timeout=timeout, env=env, resume_done=resume_done)
    if not n1.get("success"):
        return {"case": "C", "nodes": [n1], "success": False}
    table = extract_sirna_safety_table(results_of(n1) or {})
    nodes = [dict(n1, _rec=None),
             {"node_id": "safety_table", "success": True, "elapsed_seconds": 0,
              "note": "extraction-only safety ranking from node1 outputs"}]
    summary = {
        "case": "C",
        "title": "SARS-CoV-2 NSP12 siRNA therapy",
        "success": all(n.get("success") for n in nodes),
        "nodes": [{k: v for k, v in n.items() if not k.startswith("_")} for n in nodes],
        "safety_table": table,
        "rule_thresholds": {"gc_window": SIRNA_GC_WINDOW,
                            "source": "MANUSCRIPT §9 (published design rules); duplex ΔG reported descriptively"},
        "notes": ["PA_016 input uses mode='antiviral' although §9 says 'generic mode'; "
                  "the curated benchmark input is used verbatim."],
        "timeline_seconds": sum(n.get("elapsed_seconds") or 0 for n in nodes),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    return summary


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", choices=["A", "B", "C"], default=None, help="single case (default: all)")
    parser.add_argument("--resume", action="store_true", help="skip nodes with a successful record")
    parser.add_argument("--timeout", type=int, default=5400)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pool-jsonl", type=Path, nargs="*", default=DEFAULT_POOL_JSONL,
                        help="fig3 shard JSONLs for the Case-A stability-first pool")
    parser.add_argument("--pool-json", type=Path, default=None,
                        help="manual pool JSON overriding --pool-jsonl (see run_reference_point_steering)")
    args = parser.parse_args()

    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"

    case_ids = [args.case] if args.case else ["A", "B", "C"]
    summaries = []
    for cid in case_ids:
        print(f"[Case {cid}]", flush=True)
        nodes_jsonl = case_dir(cid) / "nodes.jsonl"
        resume_done = load_done_nodes(nodes_jsonl) if args.resume else set()
        if cid == "A":
            summary = run_case_a(env, args.timeout, resume_done, args.dry_run,
                                 args.pool_jsonl, args.pool_json)
        elif cid == "B":
            summary = run_case_b(env, args.timeout, resume_done, args.dry_run)
        else:
            summary = run_case_c(env, args.timeout, resume_done, args.dry_run)
        if not args.dry_run:
            (case_dir(cid) / "case_summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            print(f"  -> {'OK' if summary.get('success') else 'FAILED'} "
                  f"({summary.get('timeline_seconds', 0):.0f}s) -> {case_dir(cid) / 'case_summary.json'}", flush=True)
        summaries.append(summary)

    n_ok = sum(1 for s in summaries if s.get("success") or s.get("dry_run"))
    print(f"\nDone: {n_ok}/{len(summaries)} cases ok -> {RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
