# paper_v5 — Nature Methods figure set (2026-08-20)

Six main figures for the RNADesignAgent manuscript, rebuilt per
`docs/REFERENCE_FIGURE_SURVEY.md` (seven Nature/Science agent papers) and
`docs/FIGURE_PLAN_V5.md`.

## Layout

- `style.py` — shared Morandi palette, Arial rcParams, arm→colour code,
  save helpers. Every panel imports this module, so fonts/colours cannot drift.
- `data.py` — loaders for every result file the panels read
  (`experiments/results/`, live audit trail).
- `schematic.py` — rounded-box/arrow helpers for the Fig 1 architecture panels.
- `assemble.py` — composite builder (PyMuPDF): vector PDF + 450-dpi PNG proof;
  draws the bold panel letters at assembly time only.
- `qa_bounds.py` — objective audit: every text/tick/title artist must sit
  inside its figure (catches clipping without a vision model).
- `figN/<letter>_<slug>.py` — ONE script per panel (user requirement);
  exports `figN/panels/<letter>.{pdf,png}`.
- `figN/assemble.py` — per-figure grid layout.

## Build

```bash
cd rna_agent_system/experiments/plots/paper_v5
python qa_bounds.py          # render all panels + bounds audit (exit 1 on OOB)
python assemble.py           # compose fig1..fig6 (.pdf + .png)
```

## Figures

| Fig | Panels | Content |
|---|---|---|
| 1 | a–f | architecture: platform spine + layers; multi-agent layer; platform at a glance; CapGate + GenNav mechanisms; gear lattice; RNADesign-210 composition |
| 2 | a–i | eleven workflows, biological validity, auditability (coverage, CAI/MFE nulls, inverse folding, IRES ROC, siRNA, RNAsmol two-sided, runtime, audit trail) |
| 3 | a–i | failure modes measurable by default (schematic; screening/ranking/docking 0-for-N; calibration inversion; ungated overreach; E7 certification; deployed-artifact fidelity; confounded-improvement dissolution) |
| 4 | a–i | CapGate eliminates false claims (schematic; E3 headline + waffle + events; E3-M; selective gating; production gate decisions; advisory governance; LLM minimalism) |
| 5 | a–i | GenNav delivers pre-registered profiles (schematic; selection-layer failure; mRNA 30:0 + delivery map + disclosed secondary; aptamer arc E8→E15; E14 decisive + map; budget + production runs) |
| 6 | a–i | negative results and boundaries (capability map; junction NO-GOs; ddG validity; memory no-pay; generator boundaries; E15 regime boundary; escape routes closed; failure taxonomy; LLM usage) |

## QA loop used

1. `python qa_bounds.py figN` until "all panels within figure bounds".
2. Vision-model check of each assembled `figN.png` (overlap, palette
   consistency, letter placement); flagged panels re-rendered from their
   scripts and re-audited.
3. Numbers cross-checked against `docs/PAPER_FACT_SHEET.md` evidence files;
   the two hard-coded exceptions (RNAsmol pre-fix AUROCs, E11 simulation
   P values) carry provenance comments in their panel scripts.
