# GenNav production-path live verification (2026-08-19)

One real end-to-end navigation run through the form-driven CLI, GPU 0,
`RNADA_CAPGATE=advisory`, no caches:

- Target: VEGF (1vpf.pdb, chain A), auto hotspot identification, `navigation=true`.
- Command: `python cli/form_chat.py --workflow rna_aptamer_design --params-file workspace/gennav_live/params.json --session-id gennav_live_vegf_20260819`
- Outcome: success. raw_spent 41/48 (early stop honoured), pool 39,
  4 reinforcement rounds (all guarantee-kind), deliveries:
  compact 5/5 (D1 0.32), standard 5/5 (D1 0.43), extended 4/5 (D1 0.36,
  explicit degrade after budget), 7 delivered candidates ASF-ranked with the
  full metric bundle; QualityAgent advisory review passed.
- Audit: 172 tool-call records in the result artifact; every call also in
  `workspace/audit/platform_audit.jsonl` (21 ODesign requests, 39 LinearFold
  constraint folds, 21 RhoFold, 7 full EGARPS/ProteinX/interface evaluations).
- Result JSON: `vegf_1vpf_navigation_result.json` (copied from the session
  workspace; note this run predates the CLI v2.4.0 `_gennav_trace` artifact
  key — the navigation view is in its `summary`, the round-level trace was
  verified in the unit tests and lands in `_gennav_trace` for runs after
  that change).
