# Change Log: `design_mrna_cds_junction_aware_with_lineardesign` v0.1.0 (2026-08-04)

> **Scope**: new additive tool + microservice endpoint. No locked interface
> modified; all changes are additions alongside the v0.2.0 LinearDesign lock
> (INTERFACE_LOCKS §7).

## What was added

- **Endpoint** `POST http://127.0.0.1:8014/generate/cds_junction_aware`
  (`microservices/lineardesign_service/main.py`, additive section at the end of
  the file): `LinearDesignJunctionAwareRequest` / `LinearDesignJunctionAwareResponse`,
  flank normalization + junction-side slicing (default 21 nt per side, multiple
  of 3, ≥ 3 → else 422), zero-flank degeneration to the legacy 4-argument call,
  `junction_window_pair_count` recomputed service-side with the same window
  coordinates as the C++ penalty, `mfe_thermo` recovery.
- **Tool** `design_mrna_cds_junction_aware_with_lineardesign`
  (`agent_core/tools.py` :: `LinearDesignCdsJunctionAwareInput` + wrapper;
  `agent_core/tool_specs.py` :: `LinearDesignCdsJunctionAwareOutput` + ToolSpec
  registration; full chain through the registry).
- **Service map**: `agent_core/services/service_manager.py` ::
  `CAPABILITY_SERVICE_MAP["design_mrna_cds_junction_aware_with_lineardesign"]`
  → port 8014 (pre-flight/auto-start works like the legacy tool).
  `agent_core/state.py` needed no change (no lineardesign-specific fields).
- **Lock entry**: INTERFACE_LOCKS §21 (v0.1.0) + lock-table row.
- **Tool doc**: `docs/tools/design_mrna_cds_junction_aware_with_lineardesign.md`.

Depends on the local LinearDesign C++ JUNCTION-PATCH — see
`docs/change_logs/2026-08-04_lineardesign_junction_patch.md`.

## Tests

- +23 unit tests (flank normalization/slicing 422s, zero-flank degeneration,
  pair-count window math, `mfe_thermo` recovery, wrapper payload/timeout,
  ToolSpec/registry wiring).
- Live curl smoke against port 8014 (30 aa + 21 nt flanks, w_jun = 1):
  `junction_window_pair_count = 33`, `mfe = −68.4`, `mfe_thermo = −101.4`,
  byte-identical to direct binary invocation; zero-flank response identical to
  the legacy `/generate/cds`.
- Full suite: pytest 587 passed, 1 skipped (baseline 564 + 23 new).

## Integration status

**Not wired into any workflow.** The P2 pre-registered acceptance (72 cells,
`experiments/junction_integrated_optimizer_eval.py`) returned **NO-GO**
(`experiments/results/junction_integrated_optimizer_summary.json`): the
global-fold window penalty does not repair fragment-fold AUG/Kozak burial
(hard repair ≤ 2/7 at all weights; mechanism = penalty/metric coordinate
mismatch). The capability stays registered for future use (e.g. a penalty
acting on the fragment-fold objective).
