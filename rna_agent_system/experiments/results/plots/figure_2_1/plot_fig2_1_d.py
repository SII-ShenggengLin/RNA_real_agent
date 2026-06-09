#!/usr/bin/env python3
"""
Figure 2.1 — Panel (d): Tool Correctness heatmap
Data source: RNA-BioBench-Platform benchmark results
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

from figure_2_1_common import (
    BASE_DIR,
    GROUP_MAP,
    MORANDI_COLORS,
    SHORT_NAMES,
    WORKFLOWS,
    load_all_records,
    setup_mpl_style,
)

setup_mpl_style(grid=False)

# 工具名称缩写映射（用于纵轴显示）
TOOL_ABBREV = {
    "compute_rna_sequence_gc_content": "GC Content Calculation",
    "predict_rna_secondary_structure": "2D Structure Prediction (RNAfold)",
    "predict_rna_tertiary_structure_with_rhofold": "3D Structure Prediction (RhoFold)",
    "design_sgrna_handle_with_crgpt": "sgRNA Design (CRGPT)",
    "compute_sirna_duplex_binding_vienna": "siRNA Binding (RNAcofold)",
    "score_sgrna_handle_with_crgpt": "sgRNA Score (CRGPT)",
    "design_mrna_cds_with_lineardesign": "mRNA CDS (LinearDesign)",
    "inverse_fold_rna_secondary_structure_vienna": "Inverse Fold (RNAinverse)",
    "predict_rna_secondary_structure_with_linearfold": "2D Structure Prediction (LinearFold)",
    "build_odesign_aptamer_input_json": "ODesign Input",
    "run_odesign_inference": "ODesign Inference",
    "extract_rna_sequence_from_cif": "Extract from CIF",
    "score_rna_protein_complex_with_egarps": "RNA-Protein Score (EGARPS)",
    "predict_rna_local_accessibility_profile_vienna": "Local Accessibility (RNAplfold)",
    "design_mrna_cds_with_rnarl": "mRNA CDS (RNARL)",
    "identify_protein_binding_hotspots": "Binding Hotspots",
    "design_rna_sequence_with_rhodesign": "RNA Design (RhoDesign)",
    "compute_aso_target_accessibility_vienna": "ASO Accessibility (RNAplfold)",
    "design_rna_inverse_fold_with_ribodiffusion": "Inverse Fold (RiboDiff)",
    "score_rna_ligand_binding_with_gernabind": "Ligand Binding (GerNA-Bind)",
    "compute_cai_for_cds_sequence": "CAI Calculation",
    "predict_mrna_stability_with_rnastop": "mRNA Stability (RNASTOP)",
    "compute_dot_bracket_unpaired_fraction": "Unpaired Fraction",
    "design_3utr_with_gemorna": "3'UTR Design (GEMORNA)",
    "design_5utr_with_gemorna": "5'UTR Design (GEMORNA)",
    "shuffle_cds_junction_codons": "CDS Junction Shuffle",
    "score_structure_alignment": "Structure Alignment",
    "analyze_rna_protein_interface": "RNA-Protein Interface Analysis",
    "predict_rna_protein_complex_with_proteinx": "RNA-Protein Complex Structure Prediction (ProteinX)",
    "score_crispr_off_target_with_crisot": "Off-target Score (CRISOT)",
    "predict_putative_ires_with_iresfinder": "IRES Prediction (IRESfinder)",
    "compute_rna_rna_interaction_vienna": "RNA-RNA Interaction (RNAup)",
    "design_mrna_cds_with_gemorna": "mRNA CDS (GEMORNA)",
    "design_sirna_with_evitar": "siRNA Design (Evitar)",
    "score_rna_ligand_binding_with_rnasmol": "Ligand Binding (RNAsmol)",
    "run_blastn_similarity_search": "BLASTn Similarity Search",
    "run_bowtie2_short_alignment":"Bowtie2 Similarity Search",
    "predict_protein_structure_with_proteinx": "Protein Structure Prediction (ProteinX)",
}


# ───────────────────────────────────────────────
# Panel (d) 绘图逻辑
# ───────────────────────────────────────────────

def compute_tool_correctness_matrix(df: pd.DataFrame, top_n_tools: int | None = None) -> pd.DataFrame:
    """
    计算 Tool Correctness heatmap 矩阵。
    行 = 所有工具（或 top_n_tools 个高频工具），列 = 11 个 workflows。
    值为 Tool Correctness ratio，NaN 表示该 workflow 不期望该 tool。
    """
    # 统计每个工具被期望的总次数
    tool_expect_counts = {}
    for _, row in df.iterrows():
        for tool in row.get("expected_tools", []):
            tool_expect_counts[tool] = tool_expect_counts.get(tool, 0) + 1

    # 选取高频工具（top_n_tools=None 时展示全部）
    top_tools = sorted(tool_expect_counts, key=tool_expect_counts.get, reverse=True)
    if top_n_tools is not None:
        top_tools = top_tools[:top_n_tools]

    # 计算每个 (workflow, tool) 的 correctness ratio
    matrix = pd.DataFrame(index=top_tools, columns=WORKFLOWS, dtype=float)

    for wf in WORKFLOWS:
        wf_df = df[df["workflow"] == wf]
        for tool in top_tools:
            # 该 workflow 中期望该 tool 的任务
            expected_mask = wf_df["expected_tools"].apply(lambda x: tool in x)
            expected_count = expected_mask.sum()

            if expected_count == 0:
                matrix.loc[tool, wf] = np.nan
            else:
                # 其中 tool_correctness=True 的任务数
                correct_count = wf_df[expected_mask & wf_df["tool_correctness"]].shape[0]
                matrix.loc[tool, wf] = correct_count / expected_count

    return matrix


def plot_panel_d(matrix: pd.DataFrame):
    """绘制 Tool Correctness heatmap。"""
    colors = ["#FAFAFA", "#E2E8EC", "#CAD4DB", "#B1BFC9", "#98AAB7",
              "#8B9DAF", "#7E90A0", "#617280", "#465F6D"]
    cmap = LinearSegmentedColormap.from_list("morandi_bluegrey", colors)

    y_labels = [TOOL_ABBREV.get(t, t) for t in matrix.index]

    x_labels = [SHORT_NAMES[wf] for wf in WORKFLOWS]

    # ── 修改1：动态增加高度，避免纵轴重叠 ──
    n_tools = len(matrix.index)
    fig_height = max(8, n_tools * 0.38)  # 每个工具约 0.38 英寸
    fig, ax = plt.subplots(figsize=(12, fig_height))

    # ── 修改2：annot=False，改为手动添加文本，实现1.00白色 ──
    sns.heatmap(
        matrix.values,
        cmap=cmap,
        vmin=0, vmax=1,
        annot=False,  # 关闭默认注释
        linewidths=0.5,
        linecolor="#E0E0E0",
        xticklabels=x_labels,
        yticklabels=y_labels,
        ax=ax,
        cbar_kws={
            "label": "Tool Correctness Ratio",
            "shrink": 0.6,
            "aspect": 20,
        },
        mask=matrix.isna().values,
    )

    # 手动添加注释：1.00 用白色，其余用深灰色
    for i in range(len(matrix.index)):
        for j in range(len(matrix.columns)):
            val = matrix.iloc[i, j]
            if not pd.isna(val):
                text_color = "#FFFFFF" if val == 1.0 else "#333333"
                ax.text(
                    j + 0.5, i + 0.5,
                    f"{val:.2f}",
                    ha="center", va="center",
                    color=text_color,
                    fontsize=8,
                    fontweight="bold" if val == 1.0 else "normal",
                )

    # NaN cell 填充浅灰色
    for i in range(len(matrix.index)):
        for j in range(len(matrix.columns)):
            if pd.isna(matrix.iloc[i, j]):
                ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=True,
                                           facecolor="#F0F0F0", edgecolor="#E0E0E0", lw=0.5))

    ax.set_xlabel("Workflow", fontsize=11, labelpad=10)
    ax.set_ylabel("Tool", fontsize=11, labelpad=10)
    ax.set_title("Tool Correctness Ratio by Workflow", fontsize=14, fontweight="bold", pad=15)

    ax.set_xticklabels(ax.get_xticklabels(), rotation=20, ha='right', fontsize=9)
    
    # ── 修改3：适当缩小 y 轴标签字号，进一步避免拥挤 ──
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=8.5)

    cbar = ax.collections[0].colorbar
    cbar.ax.set_ylabel("Tool Correctness Ratio", fontsize=10, rotation=270, labelpad=18)
    cbar.ax.tick_params(labelsize=9)

    plt.tight_layout()
    return fig

def main():
    out_dir = Path(
        "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent"
        "/rna_agent_system/experiments/results/plots/figure_2_1"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    df = load_all_records()
    print(f"Loaded {len(df)} records across {df['workflow'].nunique()} workflows")

    print("Computing tool correctness matrix...")
    matrix = compute_tool_correctness_matrix(df)
    print(f"Matrix shape: {matrix.shape}")
    print(matrix)

    print("Plotting...")
    fig = plot_panel_d(matrix)

    out_path = out_dir / "fig2_1_d.png"
    fig.savefig(
        out_path,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.1,
    )
    print(f"Saved to {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
