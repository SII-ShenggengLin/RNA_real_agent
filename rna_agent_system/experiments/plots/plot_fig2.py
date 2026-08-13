#!/usr/bin/env python3
"""Fig 2 plot: biological output quality across the 11 workflows.

Paper v2 (2026-08-11) refresh:
- 210/210 tasks (the legacy advisory-abort siRNA task completes under the
  2026-08-10 governance; `quality_abort_cases` is now empty).
- Panel a arms: WT (n=20) / random-synonymous (n=200) / designed (n=20).
  The designed arm is the `cai_only` records in `fig2_cds_nulls.jsonl`
  (OTC/PDGFB replaced the two oversized targets; PAPER_FACT_SHEET §2 maps
  designed = cai_only, median CAI 0.7454).
- NEW panel d: RNAsmol two-sided boundary (`rnasmol_boundary_panel.json`) —
  in-distribution test power exactly reproduced after the v0.3.0
  preprocessing-fidelity fix vs no demonstrated power on OOD short aptamers
  (95% CIs span chance). Subsequent panels shift one letter (a..m, 13 panels,
  4x4 grid with the last three cells hidden).

Data sources (all final, see RESUME_CHECKPOINT.md):
- `experiments/results/fig2_{cpu_a,cpu_b,gpu}.jsonl` — 210 platform tasks
  (latest record per task wins).
- `experiments/results/fig2_cds_nulls.jsonl` — WT / random-synonymous /
  designed arms for the 20 Fig-2a proteins.
- `experiments/results/fig2_literature_panels.jsonl` — IRES positive/negative
  panel and small-molecule binder/non-binder pairs.
- `experiments/results/fig2_summary.json` — pre-computed statistics
  (`experiments/analysis/summarize_fig2.py`); p-values / effect sizes / AUROC
  CIs are read from here, never recomputed.
- `experiments/results/rnasmol_boundary_panel.json` — RNAsmol in-/out-of-
  distribution boundary panel (2026-08-11).

Output: `experiments/plots/fig2.png` (300 dpi, 4×4 grid, 13 panels) plus one
PDF per panel under `experiments/plots/fig2_panels/`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/plots/plot_fig2.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = PROJECT_ROOT / "experiments" / "results"
PLOTS = PROJECT_ROOT / "experiments" / "plots"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
})

ARM_COLORS = {"wt": "#7f7f7f", "random_syn": "#bdbdbd", "cai_only": "#d62728", "designed": "#d62728"}
ARM_LABELS = {"wt": "WT", "random_syn": "random-synonymous", "cai_only": "designed", "designed": "designed"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def load_platform() -> dict[str, dict]:
    """Latest platform record per task_id across the three shards."""
    latest: dict[str, dict] = {}
    for shard in ("fig2_cpu_a", "fig2_cpu_b", "fig2_gpu"):
        for rec in load_jsonl(RESULTS / f"{shard}.jsonl"):
            tid = rec.get("task_id")
            if tid:
                latest[tid] = rec  # later shards/lines win (retry-after-fail)
    return latest


def best_scores_by_workflow(tasks: dict[str, dict], workflow: str) -> list[dict]:
    """scores dicts of best candidates of successful tasks of one workflow."""
    out = []
    for rec in tasks.values():
        if rec.get("workflow") == workflow and rec.get("success"):
            s = (rec.get("best_candidate") or {}).get("scores")
            if s:
                out.append(s)
    return out


def values(rows: list[dict], key: str) -> list[float]:
    return [float(r[key]) for r in rows if isinstance(r.get(key), (int, float))]


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def box_strip(ax: plt.Axes, groups: list[list[float]], labels: list[str],
              colors: list[str], ylabel: str) -> None:
    """Boxplot + jittered strip for a few small groups."""
    positions = list(range(1, len(groups) + 1))
    bp = ax.boxplot([g if g else [np.nan] for g in groups], positions=positions,
                    widths=0.55, showfliers=False, patch_artist=True,
                    medianprops={"color": "black", "linewidth": 1.2})
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
    rng = np.random.default_rng(0)
    for pos, group, color in zip(positions, groups, colors):
        if not group:
            continue
        jitter = rng.uniform(-0.12, 0.12, size=len(group))
        ax.scatter(np.full(len(group), pos) + jitter, group, s=6, color=color,
                   alpha=0.75, linewidths=0, zorder=3)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)


def panel_label(ax: plt.Axes, letter: str, title: str, note: str = "",
                note_loc: str = "bottom") -> None:
    ax.set_title(f"{letter}  {title}", loc="left", fontweight="bold")
    if note:
        y, va = (0.02, "bottom") if note_loc == "bottom" else (0.98, "top")
        ax.text(0.98, y, note, transform=ax.transAxes, ha="right", va=va,
                fontsize=6.5, color="#444444")


def hist_panel(ax: plt.Axes, vals: list[float], xlabel: str, color: str,
               bins: int = 10, vlines: list[tuple[float, str]] | None = None) -> None:
    if vals:
        ax.hist(vals, bins=min(bins, max(3, len(vals) // 2)), color=color, alpha=0.75,
                edgecolor="white", linewidth=0.5)
    for x, lab in (vlines or []):
        ax.axvline(x, color="#d62728", linestyle="--", linewidth=1)
        ax.text(x, ax.get_ylim()[1], f" {lab}", rotation=90, va="top", fontsize=6.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("count")


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax, nulls):
    """mrna_cds_design: designed-arm CAI vs biological nulls (H2.1).

    v2: the designed arm is the `cai_only` records (n=20, median 0.7454 —
    OTC/PDGFB replaced the two oversized targets; PAPER_FACT_SHEET §2).
    """
    arms = ["wt", "random_syn", "cai_only"]
    by_arm = {a: [r for r in nulls if r.get("arm") == a and r.get("success")] for a in arms}
    groups = [values(by_arm[a], "cai_score") for a in arms]
    labels = [f"WT\n(n={len(groups[0])})", f"rand-syn\n(n={len(groups[1])})",
              f"designed\n(n={len(groups[2])})"]
    colors = [ARM_COLORS[a] for a in arms]
    box_strip(ax, groups, labels, colors, "CAI")
    ax.tick_params(axis="x", labelsize=6)
    summ = SUMMARY.get("fig2a_cds_nulls", {})
    p = ((summ.get("cai_score") or {}).get("wt_vs_random") or {}).get("mannwhitney_p")
    d = ((summ.get("cai_score") or {}).get("wt_vs_random") or {}).get("cliffs_delta")
    med = ((summ.get("cai_score") or {}).get("cai_only") or {}).get("median")
    note = f"WT vs rand: p={p:.1e}, δ={d:.2f}" if p is not None else ""
    if med is not None:
        note += f"\ndesigned median {med:.3f}"
    panel_label(ax, "a", "mrna_cds_design — codon optimality", note)


def panel_b(ax, nulls):
    """mrna_sequence_scoring: total_score ordering across the null arms."""
    arms = ["wt", "random_syn", "cai_only"]
    groups = [values([r for r in nulls if r.get("arm") == a and r.get("success")], "total_score")
              for a in arms]
    box_strip(ax, groups, [f"{ARM_LABELS[a]}\n(n={len(g)})" for a, g in zip(arms, groups)],
              [ARM_COLORS[a] for a in arms], "sequence total score")
    ax.tick_params(axis="x", labelsize=6)
    panel_label(ax, "b", "mrna_sequence_scoring — arm ordering")


def panel_c(ax, tasks):
    """sirna_design: off-target burden + duplex MFE."""
    rows = best_scores_by_workflow(tasks, "sirna_design")
    off = values(rows, "off_target_count")
    summ = SUMMARY.get("fig2c_sirna", {})
    hist_panel(ax, off, "off-target count (Bowtie2)", "#1f77b4", bins=8)
    note = f"n={len(rows)}, zero off-target {summ.get('zero_off_target', '?')}"
    aborts = summ.get("quality_abort_cases") or []
    if aborts:
        note += f"\nQualityAgent abort: {len(aborts)} (governance case)"
    panel_label(ax, "c", "sirna_design — specificity", note, note_loc="top")


def panel_d(ax):
    """RNAsmol oracle: two-sided boundary (in-distribution vs OOD aptamers)."""
    bp = BOUNDARY
    rows = [
        (f"ROBIN test\n(n={bp['robin_test']['n']:,})",
         bp["robin_test"]["auroc"], bp["robin_test"]["auroc_ci95"], "#2ca02c"),
        (f"PDB test\n(n={bp['pdb_test']['n']:,})",
         bp["pdb_test"]["auroc"], bp["pdb_test"]["auroc_ci95"], "#2ca02c"),
        ("OOD aptamers\nvs random-chem",
         bp["ood_aptamer"]["auroc_vs_random_chem"],
         bp["ood_aptamer"]["auroc_vs_random_chem_ci95"], "#d62728"),
        ("OOD aptamers\nvs near-cognate",
         bp["ood_aptamer"]["auroc_vs_near_cognate"],
         bp["ood_aptamer"]["auroc_vs_near_cognate_ci95"], "#d62728"),
    ]
    for x, (lab, au, ci, col) in enumerate(rows):
        lo, hi = ci
        ax.bar(x, au, width=0.58, color=col, alpha=0.8, zorder=3)
        ax.errorbar(x, au, yerr=[[max(au - lo, 0.0)], [max(hi - au, 0.0)]],
                    fmt="none", ecolor="black", elinewidth=0.9, capsize=2.5,
                    zorder=4)
        ax.text(x, min(hi + 0.035, 1.24), f"{au:.2f}", ha="center",
                fontsize=6.2, color=col, fontweight="bold")
    ax.axhline(0.5, color="#7f7f7f", lw=0.9, ls=":", zorder=2)
    ax.text(-0.45, 0.515, "chance", fontsize=5.8, color="#7f7f7f", va="bottom")
    ax.axhline(0.8, color="#1f77b4", lw=0.9, ls="--", zorder=2)
    ax.text(-0.45, 0.815, "power gate > 0.8", fontsize=5.8, color="#1f77b4",
            va="bottom")
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([r[0] for r in rows], fontsize=5.6)
    ax.set_ylim(0, 1.30)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_ylabel("AUROC (95% CI)")
    fmn, mal = bp["FMN_ribocil_decoy"], bp["MALAT1_furamidine_decoy"]
    note = (f"decoy true-ligand ranks: {fmn['true_binder_rank']}/{fmn['n']:,} "
            f"(FMN), {mal['true_binder_rank']}/{mal['n']:,} (MALAT1)\n"
            "OOD short-aptamer CIs span chance — no demonstrated power")
    panel_label(ax, "d", "RNAsmol oracle — two-sided boundary", note,
                note_loc="top")


def panel_e(ax, tasks):
    """sgrna_design: CRGPT neural-score of designed handles."""
    rows = best_scores_by_workflow(tasks, "sgrna_design")
    nn = values(rows, "nn_score")
    hist_panel(ax, nn, "CRGPT nn_score", "#2ca02c", bins=10)
    panel_label(ax, "e", "sgrna_design — handle quality", f"n={len(nn)}")


def panel_f(ax, tasks):
    """rna_secondary_structure_design: distance-to-target distribution."""
    rows = best_scores_by_workflow(tasks, "rna_secondary_structure_design")
    dist = values(rows, "structure_distance")
    summ = SUMMARY.get("fig2e_secondary_design", {})
    hist_panel(ax, dist, "structure distance to target", "#9467bd", bins=8)
    rate = summ.get("exact_match_rate")
    note = f"n={summ.get('n', len(dist))}, exact {summ.get('exact_match', '?')}/{summ.get('n', '?')}"
    if rate is not None:
        note += f" ({rate:.0%})"
    panel_label(ax, "f", "rna_secondary_structure_design", note, note_loc="top")


def panel_g(ax, tasks):
    """rna_tertiary_structure_design: pLDDT and sequence recovery."""
    rows = best_scores_by_workflow(tasks, "rna_tertiary_structure_design")
    plddt = values(rows, "rhofold_mean_plddt")
    rec = values(rows, "recovery_rate")
    groups = [plddt, [r * 100 for r in rec]]
    box_strip(ax, groups, [f"pLDDT\n(n={len(plddt)})", f"recovery %\n(n={len(rec)})"],
              ["#8c564b", "#e377c2"], "value")
    panel_label(ax, "g", "rna_tertiary_structure_design", f"median pLDDT comp {SUMMARY.get('fig2f_tertiary_design', {}).get('median_plddt_component', float('nan')):.2f}")


def panel_h(ax, tasks):
    """rna_aptamer_design: objective components of best candidates."""
    rows = best_scores_by_workflow(tasks, "rna_aptamer_design")
    keys = ["egarps_component", "rhofold_component", "iptm_component"]
    groups = [values(rows, k) for k in keys]
    box_strip(ax, groups, [f"EGARPS\n(n={len(groups[0])})", f"RhoFold\n(n={len(groups[1])})",
                           f"ipTM\n(n={len(groups[2])})"],
              ["#1f77b4", "#ff7f0e", "#2ca02c"], "component score")
    panel_label(ax, "h", "rna_aptamer_design — components", f"n={len(rows)}")


def panel_i(ax, panels):
    """rna_small_molecule_interaction: binder vs non-binder scores (AUROC)."""
    recs = [r for r in panels if r.get("panel") == "small_mol" and r.get("success")
            and isinstance(r.get("total_score"), (int, float))]
    binders = [r["total_score"] for r in recs if r.get("expected") == "binder"]
    near = [r["total_score"] for r in recs if r.get("negative_class") == "near_cognate"]
    rand = [r["total_score"] for r in recs if r.get("negative_class") == "random_chem"]
    groups = [binders, near, rand]
    box_strip(ax, groups, [f"binder\n(n={len(binders)})", f"near-cognate\n(n={len(near)})",
                           f"random chem\n(n={len(rand)})"],
              ["#d62728", "#ff7f0e", "#7f7f7f"], "total score")
    ax.tick_params(axis="x", labelsize=6)
    summ = SUMMARY.get("fig2h_small_molecule", {})
    a1, a2 = summ.get("auroc_vs_random_chem"), summ.get("auroc_vs_near_cognate")
    note = f"AUROC {a1:.2f} / {a2:.2f} (tool boundary)" if a1 is not None else ""
    panel_label(ax, "i", "rna_small_molecule_interaction", note)


def panel_j(ax, tasks):
    """aso_target_screening: accessibility vs binding components."""
    rows = best_scores_by_workflow(tasks, "aso_target_screening")
    x = values(rows, "accessibility_component")
    y = values(rows, "binding_component")
    n = min(len(x), len(y))
    ax.scatter(x[:n], y[:n], s=10, color="#17becf", alpha=0.8, linewidths=0)
    ax.set_xlabel("accessibility component")
    ax.set_ylabel("binding component")
    panel_label(ax, "j", "aso_target_screening", f"n={n}")


def panel_k(ax, panels):
    """ires_prediction: validated IRES vs random UTRs (AUROC)."""
    recs = [r for r in panels if r.get("panel") == "ires" and r.get("success")]
    pos = [r["best_ires_probability"] for r in recs
           if r.get("label") == "positive" and isinstance(r.get("best_ires_probability"), (int, float))]
    neg = [r["best_ires_probability"] for r in recs
           if r.get("label") == "negative" and isinstance(r.get("best_ires_probability"), (int, float))]
    box_strip(ax, [neg, pos], [f"random UTR\n(n={len(neg)})", f"known IRES\n(n={len(pos)})"],
              ["#7f7f7f", "#d62728"], "IRES probability")
    summ = SUMMARY.get("fig2i_ires", {})
    au, ci = summ.get("auroc"), summ.get("auroc_ci95") or [None, None]
    note = f"AUROC {au:.2f} [{ci[0]:.2f}, {ci[1]:.2f}]" if au is not None else ""
    panel_label(ax, "k", "ires_prediction — discrimination", note)


def panel_l(ax, tasks):
    """full_length_mrna_design: junction thermodynamics of assembled molecules."""
    rows = best_scores_by_workflow(tasks, "full_length_mrna_design")
    j5 = values(rows, "junction_5utr_cds_mfe")
    j3 = values(rows, "junction_cds_3utr_mfe")
    box_strip(ax, [j5, j3], [f"5'UTR–CDS\n(n={len(j5)})", f"CDS–3'UTR\n(n={len(j3)})"],
              ["#bcbd22", "#17becf"], "junction MFE (kcal/mol)")
    buried = sum(1 for r in rows if r.get("junction_5utr_cds_aug_buried"))
    panel_label(ax, "l", "full_length_mrna_design — junctions", f"AUG-burial flag: {buried}/{len(rows)}")


def panel_m(ax):
    """Coverage: per-workflow task success and median runtime."""
    cov = SUMMARY.get("coverage", {})
    workflows = sorted(cov.keys())
    frac = [cov[w]["n_success"] / max(cov[w]["n_tasks"], 1) for w in workflows]
    short = [w.replace("_design", "").replace("_prediction", "").replace("_screening", "")
             .replace("_interaction", "") for w in workflows]
    colors = ["#2ca02c" if f >= 0.95 else "#ff7f0e" if f >= 0.8 else "#d62728" for f in frac]
    ax.barh(range(len(workflows)), frac, color=colors, alpha=0.8, height=0.65)
    for i, (w, f) in enumerate(zip(workflows, frac)):
        ax.text(min(f + 0.02, 1.02), i, f"{cov[w]['n_success']}/{cov[w]['n_tasks']}",
                va="center", fontsize=6.5)
    ax.set_yticks(range(len(workflows)))
    ax.set_yticklabels(short, fontsize=6.5)
    ax.set_xlim(0, 1.15)
    ax.set_xlabel("task success fraction")
    tot = SUMMARY.get("total", {})
    panel_label(ax, "m", "platform coverage", f"total {tot.get('n_success', '?')}/{tot.get('n_tasks', '?')}", note_loc="top")


PANEL_FUNCS = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m"]


def draw_all(tasks, nulls, panels):
    fig, axes = plt.subplots(4, 4, figsize=(13.5, 12.6))
    for letter, ax in zip(PANEL_FUNCS, axes.flat):
        globals()[f"panel_{letter}"](ax, *args_for(letter, tasks, nulls, panels))
    for ax in axes.flat[len(PANEL_FUNCS):]:
        ax.axis("off")
    fig.tight_layout()
    return fig


def args_for(letter, tasks, nulls, panels):
    if letter in ("a", "b"):
        return (nulls,)
    if letter in ("i", "k"):
        return (panels,)
    if letter in ("d", "m"):
        return ()
    return (tasks,)


def main() -> int:
    global SUMMARY, BOUNDARY
    SUMMARY = json.loads((RESULTS / "fig2_summary.json").read_text())
    BOUNDARY = json.loads((RESULTS / "rnasmol_boundary_panel.json").read_text())
    tasks = load_platform()
    nulls = load_jsonl(RESULTS / "fig2_cds_nulls.jsonl")
    panels = load_jsonl(RESULTS / "fig2_literature_panels.jsonl")

    PLOTS.mkdir(parents=True, exist_ok=True)
    (PLOTS / "fig2_panels").mkdir(parents=True, exist_ok=True)

    fig = draw_all(tasks, nulls, panels)
    fig.savefig(PLOTS / "fig2.png", dpi=300)
    print(f"wrote {PLOTS / 'fig2.png'}")

    for letter in PANEL_FUNCS:
        f, ax = plt.subplots(figsize=(3.4, 3.0))
        globals()[f"panel_{letter}"](ax, *args_for(letter, tasks, nulls, panels))
        f.tight_layout()
        f.savefig(PLOTS / "fig2_panels" / f"panel_{letter}.pdf")
        plt.close(f)
    print(f"wrote {len(PANEL_FUNCS)} panel PDFs -> {PLOTS / 'fig2_panels'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
