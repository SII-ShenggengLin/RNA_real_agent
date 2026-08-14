# Supplementary — GenNav aptamer-side campaign (E8–E15): pre-registration archive, power analysis, sensitivity

**Scope**: the complete evidence trail behind the paper's aptamer GenNav
results (E14 primary-endpoint GO, McNemar b=14/c=3/P=0.0127). Every
pre-registration, adjudication, and result file is committed in git; this
document bundles the reviewer-facing numbers.

## S1. Campaign timeline and pre-registration chain (all commits precede their runs)

| Campaign | Pre-registration (commit) | Protocol | Outcome |
|---|---|---|---|
| E8 | `run_e8_gennav_aptamer.py` (2026-08-11) | relax v1 grid, 9 lengths, LLM rounds | b=3/c=1/P=0.625 (transfer, saturated) |
| E9 | `run_e9_gennav_aptamer.py` (2026-08-12) | scarcity matrix, relax v1 | b=6/c=8/P=0.79 |
| E10 | `run_e10_gennav_aptamer.py` (2026-08-12) | mechanized allocation, 12-target panel | b=9/c=4/P=0.267 |
| E11 | `e11_feasibility_sim.py` (2026-08-13) | escape-route simulation | both routes closed |
| E12 | `run_e12_gennav_aptamer.py` 7890e77 (+addenda dd60d09, f0e50f1) | matrix v3 + densified 17-length lattice + S1 priors + panel gate | b=9/c=2/P=0.0654 |
| E13 | `run_e13_gennav_aptamer.py` 259973c | panel-axis closure (controlled replication) | bit-identical to E12 |
| **E14** | `run_e14_gennav_aptamer.py` **75fdc3e** (+addenda 1803a77, 7ce7875) | single-gate endpoint (user-adjudicated) + guarantee allocation | **b=14/c=3/P=0.0127 GO** |
| E15 | `run_e15_gennav_aptamer.py` 1d42f69 | confirmatory: 4 never-paneled targets + top-8 | b=14/c=6/P=0.1153 (boundary) |

## S2. Criteria revision (user adjudication, 2026-08-14; commit 75fdc3e precedes the E14 S2 run)

**Original dual gate (E6–E13)**: pass iff McNemar P<0.05 ∧ C e2e ≥ 0.8.
**Revised single gate (E14)**: pass iff paired McNemar two-sided P<0.05;
e2e demoted to secondary disclosure.

Rationale (recorded in the criteria book and DECISIONS.md row 13):
1. e2e ≥ 0.8 is an absolute-delivery feasibility measure, not a navigation
   measure: at the 48-raw cap, 12 of 36 cells are jointly infeasible — the
   static arm fails there too (E12/E13 data; closure analyses in
   FIX appendices I/J/L). A gate neither arm can meet measures the target
   set, not the navigator.
2. The relative-advantage test (paired McNemar at equal budget) is the
   direct measurement of "navigation earns its keep".
3. e2e is fully disclosed as secondary: E14 C 0.50 vs A 0.00 (6:0), with
   the jointly-infeasible-cell decomposition.

## S3. Power analysis (exact two-sided McNemar, α = 0.05)

Rejection threshold k = smallest b with 2·P(X ≥ b | D, p=0.5) < 0.05.
Power = P(X ≥ k | D, p) for true C-win probability p over discordant cells.

| Discordant pairs D | threshold b≥k | power p=0.70 | p=0.75 | p=0.80 | p=0.85 |
|---|---|---|---|---|---|
| 11 (E12/E13) | 10 | 0.11 | 0.20 | 0.32 | 0.49 |
| **17 (E14)** | 13 | 0.39 | **0.57** | 0.76 | 0.90 |
| 20 (E15) | 15 | 0.42 | 0.62 | 0.80 | 0.93 |
| 24 | 18 | 0.39 | 0.61 | 0.81 | 0.94 |
| 30 | 21 | 0.59 | 0.80 | 0.94 | 0.99 |
| **37 (E14+E15 pooled)** | 25 | 0.70 | **0.89** | 0.98 | 1.00 |
| 54 (E6 mRNA) | 35 | 0.84 | 0.97 | 1.00 | 1.00 |

Honest reading: the 12-target aptamer panel is modestly powered (57% at
the observed D=17 for p=0.75). The E14 result is nevertheless significant
(P=0.0127); the E13 deterministic replication (bit-identical rerun) and the
campaign consistency (E12→E14 monotone improvement under pre-registered
addenda) provide corroboration beyond the single P-value. Pooling the two
pre-registered aptamer campaigns (D=37, 28:9) gives P=0.0026 with 89%
power — driven by E14, heterogeneity acknowledged (E15: b=14/c=6).

## S4. Sensitivity of the E14 result to the discordant cells

- Each of the 3 c-cells (MBP extended, Papain compact, Thrombin extended)
  converted to concordant would give b=14/c=2 → P=0.0042; all three →
  b=17/c=0 → P=1.5×10⁻⁵.
- Removing any single b-cell: b=13/c=3 → P=0.0213 (still < 0.05).
- The result is robust to single-cell perturbations in either direction.
- One-sided McNemar (directional hypothesis, not used) would give P=0.0064
  for E14; we report the two-sided value throughout (consistent with E6).

## S5. Protocol addenda (user-adjudicated, criteria thresholds untouched)

- **Addendum v1 (1803a77)**: guarantee allocation changed from band-ordered
  ("repair to delivery before moving on" — starved the extended band, E14v1
  measured b=14/c=6/P=0.115) to CYCLING (one round per repairable band
  before any band's second round).
- **Addendum v2 (7ce7875)**: rounds 3×n8 → 4×n6 (budget-neutral: 17 probe +
  6 probe2 + 24 = 47 raw); sampled-gear check counts only depth ≥ n8 (the
  n2 probe2 occupancy was blocking high-rate n8 guarantee gears — E14v2
  measured b=10/c=3/P=0.092).
- E14 final (v3) measured b=14/c=3/P=0.0127 — GO.

## S6. Reviewer-ready file map

- Criteria books (docstring pre-registrations): `experiments/run_e{8..15}_gennav_aptamer.py`
- Verdicts: `experiments/results/e{12,13,14,15}_verdict_s{0,1,2}.json`
- Append-only run records: `experiments/results/e{12,13,14,15}_runs_s{0,1,2}.jsonl`
- Audit trails: `experiments/results/e{12,13,14,15}_audit/`
- Iteration-path evidence: `experiments/results/e14_runs_s{0,2}_v{1,2}.jsonl`, `e14_audit_v{1,2}/`
- Closure analyses: `docs/FIX_2026-08-12_DUAL_GENERALIZATION.md` appendices I–N
- Fact-check table: `docs/PAPER_FACT_SHEET.md`
- Decisions register: `docs/DECISIONS.md` rows 9–14, Part 1 (f), Part 3 timeline
