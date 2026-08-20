# Reference-Paper Figure Survey — Seven Nature/Science Agent-System Papers

> Compiled 2026-08-20 (paper_v5 figure rebuild). Source PDFs under
> `relevant_references/`; per-paper renderings and text extracts were produced
> by four survey agents under `/tmp/survey{1..4}/` (transient).
> Method: `pdftotext -layout` caption extraction (authoritative for panel
> semantics) + page rendering + vision-model inspection for plot types and
> palette. Two low-confidence cells are flagged inline.

Papers surveyed (main figures / extended-data figures; mean panels per main figure):

| # | Paper | Venue | Main / ED figs | Panels per main fig (mean, range) |
|---|-------|-------|----------------|------------------|
| 1 | Robin — "A multi-agent system for automating scientific discovery" | Nature 2026 | 4 / 6 | 4.5 (3–6) |
| 2 | Biomni — "Autonomous biomedical research with an AI agent" | Science 2026 | 5 / 0 | 5.6 (3–8) |
| 3 | Co-Scientist — "Accelerating scientific discovery with Co-Scientist" | Nature 2026 | 4 / 6 | 4.5 (3–8) |
| 4 | CASCADE — case-based continual adaptation | Nature (submitted) | 6 / 2 | 4.0 (1–7) |
| 5 | DeepRare — rare-disease diagnosis agentic system | Nature 2026 | 5 / 3 | 3.2 (2–4) |
| 6 | ERA — expert-level empirical software | Nature 2026 | 3 / 8 | 4.0 (3–5) |
| 7 | BioMedAgent — multi-agent biomedical data analyses | Nat. Biomed. Eng. 2026 | 6 / 10 | 4.0 (2–6) |

## 1. Figure-1 anatomy (the architecture figure)

All seven papers devote Fig. 1 to the system itself, in three recurrent styles:

- **Cycle/loop schematic** (Robin 1a, Biomni 1c, Co-Scientist 1a): input (goal)
  on the left, output (candidates/hypotheses) on the right, the agent system as
  a rounded-box loop in the middle, scientist-in-the-loop drawn explicitly.
- **Layered architecture diagram** (Co-Scientist 1b, BioMedAgent 1a,
  DeepRare ED1): nested rounded boxes per module with a **colour-coded arrow
  semantics legend** (grey = data flow, red = feedback), sometimes a
  PC-analogy tier structure (host = CPU, agents = peripherals).
- **Asset/action-space map** (Biomni 1a–b, DeepRare 1b sunburst): counts of
  curated tools/databases/knowledge sources as a workflow or radial hierarchy.

Conventions: pastel flat fills, thin dark outlines, white background, no 3D or
shadows; numbered-step badges (CASCADE ①–⑥) for pipeline stages; an embedded
worked example (query → answer, prompt → code) inside the diagram (Biomni 1c,
CASCADE 6a). Robin and Co-Scientist add a third Fig-1 panel previewing the
downstream validation cases (one row per case study).

## 2. Recurrent panel types (frequency across the 33 main figures)

| Panel type | Used by (examples) | Notes |
|---|---|---|
| Grouped bars + error bars / asterisks | all seven | the workhorse; values often printed on bars (DeepRare) |
| Small-multiple line charts (metric vs steps/compute, mean ± band) | CASCADE 3a/5c, Co-Scientist 2a, BioMedAgent 3c-d | always improvement-over-baseline normalised to one y-scale |
| Performance-vs-cost scatter (accuracy vs time/GPU-memory) | Biomni 2c-e/4a, CASCADE 3c, Co-Scientist 2a | **the signature system-level panel**; ours-analogous = quality vs budget |
| Heatmap (method × task / rounds / sensitivity) | DeepRare 5a, CASCADE 3b/4d, BioMedAgent 3a/4b, ERA 3b | sequential or diverging; ERA prints cell values + gold-highlights own row |
| Box/violin + jittered points | BioMedAgent 2d-f, DeepRare 4c, Co-Scientist ED2, CASCADE 5f | judge-robustness and distribution-shift panels |
| Dumbbell / paired before→after dots with Δ labels | DeepRare 5b, ERA ED1 | baseline→agent per host/task |
| Waterfall (module contributions) | DeepRare 5c | |
| Radar (ablation across many tasks) | CASCADE 4c | |
| Mosaic / waffle / donut (composition, failure taxonomy) | DeepRare 4d, BioMedAgent 2b | |
| Styled table with best-bold / √-× matrix | CASCADE 3b/5g, ERA 2b, BioMedAgent 2a/5b | a table *is* a panel in Nature agent papers |
| Search/trajectory plot with labelled jumps ("breakthrough plot") | ERA ED2/6/8 | score vs attempts; annotations name the intervention — directly transferable to GenNav rounds |
| Agent-output artefact as a panel | Robin 2a/3a/4a (verbatim JSON), Biomni 3c/4b/5c (generated plots, prompts, code) | every results figure opens with one |
| Permutation-null histogram with observed statistic | Robin ED4 | most rigorous ablation-statistics pattern |
| Sunburst / radial hierarchy | DeepRare 1b | knowledge-source structure |
| CONSORT-style curation flow | DeepRare ED2 | cohort/asset curation |
| Text-UI mockup (case output with citations) | DeepRare 4a | traceability exhibit |

## 3. Palette statistics

- **Background**: pure white in all seven (only native microscopy panels are dark).
- **Saturation**: muted-to-moderate everywhere; no neon primaries. Robin is the
  most Morandi-like (low saturation pastels); BioMedAgent and Co-Scientist are
  steel-blue-dominant; DeepRare allows one saturated identity accent.
- **Dominant hues**: blue family (all seven papers), followed by orange/terracotta
  and green; violet/lavender and gold appear as 4th/5th categoricals; grey always
  = baseline/null/carrier.
- **Semantic colour discipline** (the strongest shared trait):
  - one accent for "ours" (DeepRare red; CASCADE orange; ERA teal; Co-Scientist navy)
    against muted baselines, held **constant across every figure**;
  - grey = null/baseline/carrier control;
  - diverging red↔blue only for signed effects (ERA leaderboards, Co-Scientist synergy);
  - traffic-light verdicts (green/blue/red = beats both/one/neither) for
    hybrid/recombination grids (ERA);
  - discrete grade scales reused identically across figures (BioMedAgent Win-score).
- **Heatmaps**: sequential (viridis-like, blue-intensity, white→hue) or
  diverging red↔blue; ERA prints numeric values inside cells.

## 4. Statistics & ablation presentation

- Asterisk convention NS/\*/\*\*/\*\*\*/\*\*\*\* with the exact test named in
  the caption; exact P values frequently quoted on-panel (Co-Scientist,
  BioMedAgent, Robin).
- Error encodings: shaded 95% CI bands, SEM/SD bars, probable-error whiskers;
  n and seeds always stated; replicate dots overlaid on bars (ERA, Biomni).
- Ablations: module on/off two-condition comparisons (BioMedAgent), baseline→agent
  dumbbells (DeepRare), radar across variants (CASCADE), waterfall (DeepRare),
  permutation-null histograms (Robin ED4).
- Negative results: shown as annotated NS panels with the test statistic inline
  (Robin ED3), "no test survives correction" statements, and boundary/regime
  maps — never dropped.
- Expert/human comparisons: physicians or human references as one more bar
  group (DeepRare 3c), in-chart human-level reference lines (ERA 1b), or
  structured expert-audit tables (ERA ED Table 1).

## 5. Narrative architecture (how many figures, what role)

All seven: Fig. 1 = system + assets; then one figure per results subsection
(3–6 main figures). Two structural templates:

- **Discovery-narrative** (Robin, Biomni, Co-Scientist): figs 2+ are the
  validation arc; system-level evaluation lives in one flagship benchmark
  figure (Biomni 2: 8 panels) or in ED (Robin).
- **Capability-narrative** (CASCADE, DeepRare, ERA, BioMedAgent): headline
  benchmark figure → mechanism/component figures (one per contribution) →
  generality/robustness figure → real-world case-study figure.

Our paper follows the capability-narrative template: Fig 1 architecture;
Figs 2–6 = five results subsections (platform validity → failure modes →
CapGate → GenNav → boundaries), 9 panels each.

## 6. Design decisions adopted for paper_v5

1. **One script per panel**, shared `style.py` (Morandi palette, Arial 5.5–7 pt,
   white background) — fonts and colours cannot drift between panels.
2. **Strict arm→colour code held across all six figures** (survey's strongest
   shared trait): mist blue = navigation/gated/designed; terracotta =
   rule/ungated/failure; sage = wild-type/certified; grey = random/null/baseline.
3. **Fig 1** = cycle + layered architecture + CapGate/GenNav mechanism panels +
   asset map + benchmark composition (schematic, pastel fills, numbered stages,
   colour-coded arrow legend).
4. **Signature panels**: quality-vs-budget scatter (GenNav), capability-grade
   heatmaps with printed values (E1 profiling), paired discordance mosaic
   (McNemar), audit-trail telemetry, agent-output artefacts (audit lines,
   navigation traces).
5. **Ablation statistics**: dots over bars, asterisks with exact P inline,
   permutation-flavoured null lines where applicable; negative results kept
   as first-class annotated panels.
6. **9 panels per results figure** (user requirement; matches Biomni's
   full-page 8-panel flagship style plus one), with maximally diverse types.
7. Panel letters drawn only at assembly time (bold Arial, 10 pt) — cannot
   collide with panel content.
