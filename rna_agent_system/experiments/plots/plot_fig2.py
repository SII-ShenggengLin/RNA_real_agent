#!/usr/bin/env python3
"""Fig 2 plot: biological output quality across the 11 workflows.

Data sources (all final, see RESUME_CHECKPOINT.md):
- `experiments/results/fig2_{cpu_a,cpu_b,gpu}.jsonl` — 210 platform tasks
  (latest record per task wins).
- `experiments/results/fig2_cds_nulls.jsonl` — WT / random-synonymous /
  CAI-only null arms for the 20 Fig-3 proteins.
- `experiments/results/fig2_literature_panels.jsonl` — IRES positive/negative
  panel and small-molecule binder/non-binder pairs.
- `experiments/results/fig2_summary.json` — pre-computed statistics
  (`experiments/analysis/summarize_fig2.py`); p-values / effect sizes / AUROC
  CIs are read from here, never recomputed.

Output: `experiments/plots/fig2.png` (300 dpi, 3×4 grid) plus one PDF per
panel under `experiments/plots/fig2_panels/`.

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

ARM_COLORS = {"wt": "#7f7f7f", "random_syn": "#bdbdbd", "cai_only": "#1f77b4", "designed": "#d62728"}
ARM_LABELS = {"wt": "WT", "random_syn": "random-synonymous", "cai_only": "CAI-only (λ=0)", "designed": "designed"}


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

def panel_a(ax, nulls, tasks):
    """mrna_cds_design: CAI and MFE/nt vs biological nulls (H2.1)."""
    arms = ["wt", "random_syn", "cai_only"]
    by_arm = {a: [r for r in nulls if r.get("arm") == a and r.get("success")] for a in arms}
    designed = best_scores_by_workflow(tasks, "mrna_cds_design")
    groups = [values(by_arm[a], "cai_score") for a in arms] + [values(designed, "cai_score")]
    labels = [f"WT\n(n={len(groups[0])})", f"rand-syn\n(n={len(groups[1])})",
              f"CAI-only\n(n={len(groups[2])})", f"designed\n(n={len(groups[3])})"]
    colors = [ARM_COLORS[a] for a in arms] + [ARM_COLORS["designed"]]
    box_strip(ax, groups, labels, colors, "CAI")
    ax.tick_params(axis="x", labelsize=6)
    summ = SUMMARY.get("fig2a_cds_nulls", {})
    p = ((summ.get("cai_score") or {}).get("wt_vs_random") or {}).get("mannwhitney_p")
    d = ((summ.get("cai_score") or {}).get("wt_vs_random") or {}).get("cliffs_delta")
    note = f"WT vs rand: p={p:.1e}, δ={d:.2f}" if p is not None else ""
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


def panel_d(ax, tasks):
    """sgrna_design: CRGPT neural-score of designed handles."""
    rows = best_scores_by_workflow(tasks, "sgrna_design")
    nn = values(rows, "nn_score")
    hist_panel(ax, nn, "CRGPT nn_score", "#2ca02c", bins=10)
    panel_label(ax, "d", "sgrna_design — handle quality", f"n={len(nn)}")


def panel_e(ax, tasks):
    """rna_secondary_structure_design: distance-to-target distribution."""
    rows = best_scores_by_workflow(tasks, "rna_secondary_structure_design")
    dist = values(rows, "structure_distance")
    summ = SUMMARY.get("fig2e_secondary_design", {})
    hist_panel(ax, dist, "structure distance to target", "#9467bd", bins=8)
    rate = summ.get("exact_match_rate")
    note = f"n={summ.get('n', len(dist))}, exact {summ.get('exact_match', '?')}/{summ.get('n', '?')}"
    if rate is not None:
        note += f" ({rate:.0%})"
    panel_label(ax, "e", "rna_secondary_structure_design", note, note_loc="top")


def panel_f(ax, tasks):
    """rna_tertiary_structure_design: pLDDT and sequence recovery."""
    rows = best_scores_by_workflow(tasks, "rna_tertiary_structure_design")
    plddt = values(rows, "rhofold_mean_plddt")
    rec = values(rows, "recovery_rate")
    groups = [plddt, [r * 100 for r in rec]]
    box_strip(ax, groups, [f"pLDDT\n(n={len(plddt)})", f"recovery %\n(n={len(rec)})"],
              ["#8c564b", "#e377c2"], "value")
    panel_label(ax, "f", "rna_tertiary_structure_design", f"median pLDDT comp {SUMMARY.get('fig2f_tertiary_design', {}).get('median_plddt_component', float('nan')):.2f}")


def panel_g(ax, tasks):
    """rna_aptamer_design: objective components of best candidates."""
    rows = best_scores_by_workflow(tasks, "rna_aptamer_design")
    keys = ["egarps_component", "rhofold_component", "iptm_component"]
    groups = [values(rows, k) for k in keys]
    box_strip(ax, groups, [f"EGARPS\n(n={len(groups[0])})", f"RhoFold\n(n={len(groups[1])})",
                           f"ipTM\n(n={len(groups[2])})"],
              ["#1f77b4", "#ff7f0e", "#2ca02c"], "component score")
    panel_label(ax, "g", "rna_aptamer_design — components", f"n={len(rows)}")


def panel_h(ax, panels):
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
    panel_label(ax, "h", "rna_small_molecule_interaction", note)


def panel_i(ax, tasks):
    """aso_target_screening: accessibility vs binding components."""
    rows = best_scores_by_workflow(tasks, "aso_target_screening")
    x = values(rows, "accessibility_component")
    y = values(rows, "binding_component")
    n = min(len(x), len(y))
    ax.scatter(x[:n], y[:n], s=10, color="#17becf", alpha=0.8, linewidths=0)
    ax.set_xlabel("accessibility component")
    ax.set_ylabel("binding component")
    panel_label(ax, "i", "aso_target_screening", f"n={n}")


def panel_j(ax, panels):
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
    panel_label(ax, "j", "ires_prediction — discrimination", note)


def panel_k(ax, tasks):
    """full_length_mrna_design: junction thermodynamics of assembled molecules."""
    rows = best_scores_by_workflow(tasks, "full_length_mrna_design")
    j5 = values(rows, "junction_5utr_cds_mfe")
    j3 = values(rows, "junction_cds_3utr_mfe")
    box_strip(ax, [j5, j3], [f"5'UTR–CDS\n(n={len(j5)})", f"CDS–3'UTR\n(n={len(j3)})"],
              ["#bcbd22", "#17becf"], "junction MFE (kcal/mol)")
    buried = sum(1 for r in rows if r.get("junction_5utr_cds_aug_buried"))
    panel_label(ax, "k", "full_length_mrna_design — junctions", f"AUG-burial flag: {buried}/{len(rows)}")


def panel_l(ax):
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
    panel_label(ax, "l", "platform coverage", f"total {tot.get('n_success', '?')}/{tot.get('n_tasks', '?')}", note_loc="top")


PANEL_FUNCS = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]


def draw_all(tasks, nulls, panels):
    fig, axes = plt.subplots(3, 4, figsize=(13.5, 9.5))
    for letter, ax in zip(PANEL_FUNCS, axes.flat):
        globals()[f"panel_{letter}"](ax, *args_for(letter, tasks, nulls, panels))
    fig.tight_layout()
    return fig


def args_for(letter, tasks, nulls, panels):
    if letter in ("a",):
        return (nulls, tasks)
    if letter == "b":
        return (nulls,)
    if letter in ("h", "j"):
        return (panels,)
    if letter == "l":
        return ()
    return (tasks,)


def main() -> int:
    global SUMMARY
    SUMMARY = json.loads((RESULTS / "fig2_summary.json").read_text())
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
