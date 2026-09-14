# E21/E22 three-arm comparison (Exp 41 platform / Exp 42 bare-LLM / Exp 43 ReAct)

Per-turn delivered validity by workflow (delivered/turns):

| workflow | platform | bare zero | bare few | ReAct matched | ReAct 3x | ReAct 10x |
|---|---|---|---|---|---|---|
| aso_target_screening | 9/9 | 9/9 | 7/9 | 0/9 | 1/9 | 3/9 |
| full_length_mrna_design | 9/9 | 5/9 | 5/9 | 0/9 | 2/9 | 9/9 |
| ires_prediction | 9/9 | 9/9 | 9/9 | 3/9 | 9/9 | 9/9 |
| mrna_cds_design | 6/6 | 5/6 | 4/6 | 0/6 | 4/6 | 6/6 |
| mrna_sequence_scoring | 6/6 | 6/6 | 6/6 | 0/6 | 4/6 | 6/6 |
| rna_aptamer_design | 13/13 | 13/13 | 13/13 | 0/13 | 2/13 | 11/13 |
| rna_secondary_structure_design | 6/6 | 5/6 | 6/6 | 0/6 | 0/6 | 2/6 |
| rna_small_molecule_interaction | 9/9 | 9/9 | 9/9 | 0/9 | 9/9 | 9/9 |
| rna_tertiary_structure_design | 6/6 | 0/6 | 0/6 | 0/6 | 3/6 | 4/6 |
| sgrna_design | 13/13 | 0/13 | 0/13 | 0/13 | 4/13 | 3/13 |
| sirna_design | 10/10 | 10/10 | 10/10 | 4/10 | 6/10 | 9/10 |

Design-workflow turns only (prediction-type turns excluded):

| arm | delivered/turns |
|---|---|
| platform | 72/72 |
| bare_zeroshot | 47/72 |
| bare_fewshot | 45/72 |
| react_matched | 4/72 |
| react_3x | 22/72 |
| react_10x | 47/72 |

Non-delivery decomposition:

| arm | budget-exhausted | no parseable answer | below platform quality parity | structurally invalid |
|---|---|---|---|---|
| bare_zeroshot | 0 | 0 | 14 | 11 |
| bare_fewshot | 0 | 0 | 13 | 14 |
| react_matched | 86 | 0 | 3 | 0 |
| react_3x | 42 | 0 | 10 | 0 |
| react_10x | 9 | 0 | 16 | 0 |

Paired vs platform (exact McNemar on per-turn delivery):

- bare_zeroshot: platform-only 25, baseline-only 0, n = 96, p = 0.0
- bare_fewshot: platform-only 27, baseline-only 0, n = 96, p = 0.0
- react_matched: platform-only 89, baseline-only 0, n = 96, p = 0.0
- react_3x: platform-only 52, baseline-only 0, n = 96, p = 0.0
- react_10x: platform-only 25, baseline-only 0, n = 96, p = 0.0
- react_10x_vs_bare_zeroshot: bare-only 12, react-only 12, n = 96, p = 1.0
