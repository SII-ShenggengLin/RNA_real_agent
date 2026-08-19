# Batch-B full-platform re-verification — 2026-08-19

Second user-directed end-to-end verification pass ("换一批数据，再重新测一次"):
a **fresh-data batch** of process-aware regressions (PA_025–PA_036, all 11
workflows plus two GenNav `navigation=true` campaigns), run against the gated
platform on GPU 0 with `RNADA_CAPGATE=advisory` (PA-driver default). Every
input differs from the 2026-08-19 first batch (PA_006–PA_024): new viral
targets (HCV / poliovirus / a different nsp12 window), new sgRNA guides from
TTR/EPO, three aptamer targets untouched by PA_009/PA_020, new RNA–ligand
pairs, a fresh mRNA / vaccine-mRNA ASO target, authentic IRES-positive 5'UTRs
(first in the PA registry), two RNA 3D structures unused by PA_013, wild-type
CDS scoring inputs, and four proteins unused by PA_015/PA_019/PA_024.

## Verdict

- **12/12 benchmarks passed, 0 failed turns** (35 user-input turns total).
  Per-run exit codes and durations: `summary.tsv`.
- **Agent-core suite before the batch: 496 passed** (unchanged after the
  session-stamping fix below).
- **PA_035 note**: the first attempt failed turn 2 because the batch's own
  `start_sequence` was 22 nt against a 23-nt `target_structure` — an
  input-authoring error the platform correctly rejected at the input layer
  (`start_sequence_length_mismatch`, empty candidates, advisory-only quality
  abort, no crash). After fixing the fixture the rerun passed 3/3; the
  incident is retained here as evidence that the deterministic input
  validation path works on bad user data.

## CapGate (audit + gating)

- Platform audit trail grew 4,106 → 5,747 events (1,230 new `tool_call`,
  303 new `gate_decision`; `workspace/audit/platform_audit.jsonl`).
- **Session attribution added this pass**: `tool_call` records now carry
  `session_id` + `task_type` (from the context-propagated session id and the
  calling workflow's task context), making every audit line attributable to
  the run that produced it. Fix: `CalibratedRuntime.record_tool_call` stamps
  the fields; `AgentRunner.stream_form` now copies its contextvars into the
  pipeline worker thread (the CLI execution path runs the pipeline in a
  `threading.Thread`, which does not inherit contextvars — the missing copy
  is why the first two entries of this batch, run pre-fix, show 0
  session-stamped records while 1,148 later records are stamped).
- Gating behaviour on live runs: pending-governance oracles
  (`score_sgrna_handle_with_crgpt`, `score_crispr_off_target_with_crisot`)
  are reviewed and audited as `require_profiling` without blocking (28 such
  gate decisions during PA_026 alone) — the documented advisory/pending
  semantics. Enforce-mode blocking remains pinned by
  `tests/test_tool_ontology.py` + `tests/test_calibrated_runtime.py`.

## GenNav production navigation (`navigation=true`)

Two fresh-target campaigns through the form-driven CLI, both fully
successful, both with complete `_gennav_trace` in the run record and every
ODesign/LinearFold call audited (380 session-stamped records for PA_028):

| target | raw budget spent | rounds (all `guarantee`) | deliveries | D1 min dist |
|---|---|---|---|---|
| 1CA2 carbonic anhydrase II | 47/48 | 5 (L25→L40→L67→L31→L43, cycling bands) | compact 5/5, standard 5/5, extended 5/5 (no degrade) | 0.21–0.42 |
| 3CNA concanavalin A | 35/48 | 3 (L28→L43→L67), **early stop** once all profiles deliverable | compact 5/5, standard 5/5, extended 5/5 (no degrade) | 0.36–0.39 |

The pair exercises both allocation paths live: budget-capped exhaustion
(1CA2) and the pre-registered early-stop rule (3CNA). Round patterns follow
the E14 cycling guaranteed-repair semantics (one round per gapped band, in
profile order, before any band receives a second). Archived results:
`gennav_1ca2_navigation_result.json`, `gennav_3cna_navigation_result.json`.

## Fresh-data observations worth keeping

- **IRES on authentic positives**: mode-0 full-sequence scans scored EMCV
  0.808 and poliovirus 0.891 — reproducing the fig2i literature-panel values
  (0.8081 / 0.9356) from the newly extracted fixtures. The EMCV mode-2
  174-nt windowed scan returned zero windows ≥ 0.5 (honest empty result,
  workflow still completes): the windowed scan can miss an IRES the
  full-sequence mode finds.
- **CDS translation integrity**: IL-2 (153 aa → 459 nt) and IFN-α2a
  (188 aa → 564 nt) candidates are exactly 3× protein length.
- **First E. coli K-12 CAI species** appearance in a PA run (PA_034 turn 3)
  — accepted by the species registry and used end-to-end.
- **Thrombin hotspots honored**: PA_027 turn 4 (1HAO chain H, declared
  exosite hotspots) produced 15-nt candidates with the declared hotspot set
  carried through to evaluation metadata.

## Files

- `summary.tsv` — per-benchmark exit codes and durations.
- `verification_output.txt` — per-session table (results, candidates, trace
  records, session-stamped audit counts) from `verify_batch.py`.
- `gennav_{1ca2,3cna}_navigation_result.json` — archived navigation runs.
- `audit_lines_before.txt` — audit-trail line count at batch start.
- Raw per-turn logs: `workspace/sessions/pa0NN_batchB_*` (runtime artifacts,
  untracked).
