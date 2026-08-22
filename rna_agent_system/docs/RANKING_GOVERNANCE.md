# Ranking Governance — Verdict-Driven Objective Assembly

> **Status**: **implemented 2026-08-21** (module
> `agent_core/calibrated/objective_assembly.py`; registered as DECISIONS (p);
> tests `tests/test_ranking_governance.py`, suite 534 passed)
> **Scope**: the cooperation between CapGate (DecisionGate / SelfModel / CalibratedRuntime) and the shared ASF ranking layer (`agent_core/workflows/multi_objective.py`)
> **Related**: [`DECISIONS.md`](DECISIONS.md) (e), (j), (k), (l), (o), (p) · [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md) §10–§15 · [`WORKFLOWS.md`](WORKFLOWS.md)
> **Governing principle**: the verdicts in (e)/(j)/(l) are *preserved unchanged* — this design changes only how the ranking layer *consumes* them.
>
> **Implementation corrections (2026-08-21)**: three facts established while
> implementing, superseding the original design draft: (1) full-length
> `utr3_stability` is backed by `gemorna_3utr_stability` (no SelfModel
> records → keep + `unprofiled` flag); RNASTOP's `overall_stability` is a
> report-only diagnostic, not an ASF dimension, so the E18 ranking failure
> demotes nothing in the current objective sets. (2) sgrNA
> `crisot_specificity_component` is aggregate compute (`ToolKind.compute`),
> outside the mechanism. (3) The degrade marker never enters
> `WorkflowResult.errors` — a non-empty errors list **is** a hard failure
> under `is_hard_failure`; the marker lives in summary / extras /
> `_state_writeback`.

---

## 1. Problem statement

CapGate and the ASF ranking layer speak different languages and are connected only by a
blunt bridge. CapGate adjudicates **evidence admissibility** at tool-call time with a
binary vocabulary (`allow` / `reject` → substitute `scoring_annotation` / `downgrade` /
`require_profiling`). The ASF aggregates **preferences** over score dimensions at ranking
time and has no channel for "this dimension's values are not trustworthy". The only
coupling today is *blocked call → metric missing → dimension dropped*, which conflates
"the oracle is invalid" with "this candidate's evaluation failed" — the same conflation
the 2026-08-20 ASF audit (DECISIONS (o)) already fought at the missing-value level.

Concretely, with the current packaged SelfModel the system exhibits three distinct
failure modes:

| Mode | What happens | Where |
|---|---|---|
| **enforce, hard** | Gated oracle calls cascade into workflow-level failures (the reason the PA driver defaults its subprocesses to advisory) | registered in (j)/(l); `run_pa_form.py:61` |
| **enforce, silent** | Gated calls surface as per-candidate missing metrics with warnings; *all* ranking dimensions drop; `apply_reference_point_ranking` returns `best = candidates[0]` — an **unlabeled generation-order "best"** | `tool_executor.py:154-176` → `multi_objective.py:440-442` (aptamer path verified: `rna_aptamer_design.py:758` ff. treats gated calls like ordinary tool failures) |
| **advisory** | The gate reviews and audits but never blocks; the ASF ranks by metrics that CapGate has *falsified* — contradicting the system's own ontology (a failed oracle's official disposition is the `scoring_annotation` substitute, `decision_gate.py:97`, not ranking evidence) | default for PA batches and all retained experiment verdicts |

Root cause: the system has claim governance (ClaimGate) and tool governance
(DecisionGate), but **no ranking governance** — the DecisionGate verdict never reaches
the ranking layer as a first-class input.

## 2. Non-goals

1. **No continuous reliability weighting.** Profile-derived ASF weights (weight ∝ ρ or
   grade×confidence) remain deferred: SelfModel coverage is too thin (only
   `gemorna_5utr_mrl` is verified-healthy for ranking), and validation requires the
   cross-family protocol that avoids circularity. This design provides the binary
   vocabulary (`keep` / `demote`) that a later continuous refinement can slot into.
2. **No new profiling campaigns, no governance flips.** Which oracles are enforce /
   pending and what their records say are inputs, not targets, of this design.
3. **No softening of (e)/(j)/(l).** Oracle verdicts, the "zeroed equally" consequence,
   and the regenerate-rather-than-soften stance all stand. What changes is the
   *presentation* of the accepted degradation (labeled degrade state instead of crash
   or silent arbitrary order).
4. **No LLM anywhere in the new path.** Assembly is a deterministic function of the
   SelfModel, the governance table, and the ontology.

## 3. Design

### 3.1 Principle

**The ASF objective set is assembled at ranking time from CapGate verdicts.** A dimension
backed by an oracle without verified (or transferred-verified) ranking power is demoted
to `scoring_annotation` — excluded from the ASF for the whole pool equally — instead of
being steered by an enforced block or left ranking in advisory. Assembly is
**mode-independent**: it never reads `RNADA_CAPGATE`, so advisory and enforce produce
the *same ranking* whenever SelfModel records exist; the modes differ only in whether
annotation values were actually computed (enforce blocks the call → annotation shows
`gated`).

### 3.2 Assembly rules

Queried per `(oracle_id, workflow task_type, target_family="default")` against the
SelfModel — deliberately using the **conservative default-family transfer** semantics
(worst grade across profiled families), because letting a workflow cherry-pick a
favorable family would violate the SelfModel's own anti-cherry-pick rule
(`self_model.py::_transfer_conservative`).

| SelfModel cell grade (ranking capability) | Governance | ASF action |
|---|---|---|
| `verified` | any | **keep** as ranking dimension |
| `transferred` from `verified` | any | **keep** + `transferred` flag (decayed confidence recorded) |
| `failed` (direct or transferred-worst) | any | **demote** to `scoring_annotation`: excluded from ASF dims pool-wide equally; value (or `gated`) still reported |
| `unprofiled`, governance=`pending` (registered campaign, not yet run: CRISOT-Score, CRGPT) | pending | **keep** + `pending` flag (matches "reviewed, audited, never blocked") |
| `unprofiled`, governance=`enforce` (no records under this task key — e.g. RhoFold under `rna_tertiary_structure_design` per (k)) | enforce | **keep** + `unprofiled` flag in v1 (no verdict exists; punishing without a verdict would violate the evidence-driven spirit of (j)). Known divergence: enforce-mode tool-call blocking still drops the dimension at measurement time — see open item §8.2 |
| not an oracle (deterministic compute: MFE, CAI, GC, RMSD, TM-score, duplex NN asymmetry, BLAST/Bowtie2 off-target) | never gated per (j) | **keep** — outside the mechanism entirely |

### 3.3 New module: `agent_core/calibrated/objective_assembly.py`

Pure functions, deterministic, no LLM. Sketch:

```python
@dataclass(frozen=True)
class ObjectiveRef:
    dim: str                 # ASF dimension key, e.g. "utr3_stability"
    tool_name: str           # backing tool, e.g. "predict_3utr_stability_with_rnastop"
    oracle_id: str           # SelfModel key, e.g. "rnastop_stability"

@dataclass
class AssembledObjectives:
    ranking_dims: list[str]              # dims entering apply_reference_point_ranking
    kept_flags: dict[str, str]           # dim -> "transferred" | "pending" | "unprofiled"
    demoted: dict[str, str]              # dim -> human-readable verdict summary
    degrade_reason: str | None           # set iff ranking_dims is empty

def assemble_ranking_objectives(
    refs: list[ObjectiveRef],
    self_model: SelfModel,
    task_type: str,
    target_family: str = "default",
) -> AssembledObjectives: ...
```

Implementation note: prefer reusing `CalibratedRuntime.review_tool_call` /
`DecisionGate._review_one` semantics over re-implementing grade mapping, so assembly and
tool-call gating can never disagree about what a record means.

### 3.4 Consumption at the five ASF call sites

Each workflow declares its `ObjectiveRef` table next to its existing `_OBJECTIVES`
tuple and filters before calling `apply_reference_point_ranking`:

- `full_length_mrna_design.py:695` — refs for `utr5_mrl`, `utr3_stability`
- `rna_aptamer_design.py:1108` — refs for all three components
- `sirna_design.py:543` — no oracle-backed dims (all compute); empty ref list, zero behavior change
- `aso_target_screening.py` (v1.1.0, 2026-08-22) — same shape as siRNA: accessibility/binding are deterministic Vienna computes; empty ref list, zero demotions
- `sgrna_design.py:489` — refs pending-governance; kept + flagged
- `rna_tertiary_structure_design.py:697` — `rhofold_component` ref; unprofiled under this task key, kept + flagged

The shared layer's own `dropped_dims` (measurement-driven) continues to apply to kept
dims. The two mechanisms are distinct and both surface in state:
**`demoted_dims` is verdict-driven; `dropped_dims` is measurement-driven.**

`apply_reference_point_ranking`'s signature is **unchanged** — assembly pre-filters the
`objectives` list. Weight renormalization (sgRNA/tertiary `weight_*` inputs) proceeds
over kept dims only, exactly as the existing code already renormalizes over ranking dims.

For `full_length_mrna_design`: the locked user-facing `reference_point` keys
(`utr5_mrl`, `utr3_stability`, `full_mfe_score`) remain accepted input. If
`utr3_stability` is demoted, a reference point containing it no longer silently
restricts the ranking — the `asf_ranking_note` must state *why*
(`utr3_stability demoted by ranking governance: E18 ranking ρ=0.579 < 0.6`), preserving
the loud-restriction semantics of (o).

### 3.5 Gated annotations are expected outcomes, not errors

`ToolResult.error.type == "GatedActionError"` (set at `tool_executor.py:164-175`) is
recognized by the evaluation paths as *expected missing* for demoted dims: no warning
spam, no retry, no hard-failure contribution; the annotation slot records
`{"gated": true, "verdict_reason": ...}`. Ordinary tool failures on **kept** dims
retain today's semantics (pool-worst imputation per (o)).

Secondary consumption point flagged for implementation: the aptamer two-stage evaluation
uses RhoFold pLDDT ≥ 65 + GC as a *screening filter* for top-k selection — a stronger
consumption of a failed oracle than ranking. When its screening capability is failed,
the filter must degrade to pass-through with a flag rather than arbitrate selection.
Verify current enforce behavior during implementation (the blocked call already leaves
pLDDT `None`); decide and register the exact degrade there.

### 3.6 Degradation state: `ranking_evidence_unavailable`

When *all* oracle-backed and compute dims of a workflow are demoted — with the current
SelfModel, only `rna_aptamer_design` (all three components failed on all six E1
families) — the workflow returns:

- `success=True` — candidates were generated and evaluated; what is unavailable is
  *evidence-based ordering*, and retrying cannot fix falsified oracles (contrast
  `navigation_delivery_empty`, which is `success=False` because *no candidates* were
  delivered at all, `rna_aptamer_design.py` degrade path);
- `summary` explicitly states the ranking has no evidence basis and the order is
  generation order;
- candidates delivered with annotation components intact; `asf_distance` absent
  (`None`) rather than fabricated;
- the marker lives in `summary`, the `ranking_evidence_unavailable` extras field,
  and `_state_writeback["_ranking_governance"]` — **never in `errors`**, because a
  non-empty `errors` list is a hard failure under
  `WorkflowResult.is_hard_failure` and would trigger pointless retries;
- `_state_writeback["_ranking_governance"]` carries the full assembly record (§3.7).

This is the machine-readable, honest form of the (j)/(l) accepted consequence — the
verdict is not softened; the workflow's *claim scope* shrinks to what its evidence
supports, which is exactly what DecisionGate's `scoring_annotation` substitute prescribes.

### 3.7 Audit and state writeback

- One `AuditTrail` event per assembly: `ranking_objective_assembly`
  `{task_type, family, kept, flags, demoted, degrade_reason}` — attributable via the
  existing session/task stamping. (The event type was registered in
  `AuditEvent.event_type` on 2026-08-22 — audit files written before that date
  legitimately contain no `ranking_objective_assembly` lines because every event
  was rejected by the Literal and silently swallowed; see DECISIONS (s).)
- `_state_writeback["_ranking_governance"]` (additive field):
  `{"ranking_dims": [...], "kept_flags": {...}, "demoted": {...}, "degrade_reason": ...}`.
- The `asf_ranking_note` convention extends to name demoted dims.

## 4. Per-workflow effect under the current packaged SelfModel

| Workflow | Ranking dims today (both modes nominally) | After v1 | Behavior delta |
|---|---|---|---|
| `full_length_mrna_design` | cds, utr5_mrl, utr3_stability, full_mfe | same four dims — `utr5_mrl` kept with `transferred` flag (E7-verified on all families), `utr3_stability` kept with `unprofiled` flag (source `gemorna_3utr_stability` has no records); cds/full_mfe are compute | state fields + flags only; no dim demotion (RNASTOP's E18 ranking failure maps to its diagnostic `overall_stability`, not an ASF dim) |
| `rna_aptamer_design` | egarps, rhofold, iptm | none — **`ranking_evidence_unavailable` degrade** | replaces both the enforce hard-failure risk and the silent generation-order "best"; advisory no longer ranks by falsified metrics; light-stage pLDDT top-k filter degrades to deterministic pool order |
| `sirna_design` | efficiency, specificity, asymmetry (all compute) | unchanged | none — regression anchor |
| `sgrna_design` | nn, crisot (pending oracles), crisot_specificity (compute) | unchanged + `pending` flags on nn/crisot | none (state fields only) |
| `rna_tertiary_structure_design` | rhofold (unprofiled under task key), rmsd, tm | unchanged + `unprofiled` flag | none (state fields only) |

Self-healing property: assembly is recomputed from live SelfModel records on every run.
If a future campaign verifies an oracle's ranking power (e.g. an RNASTOP re-profile
clearing ρ ≥ 0.6 on a broader anchor set), the dimension re-enters the ranking
automatically — no code change. Conversely, a newly failed record auto-demotes.

## 5. Interface-lock impact and migration checklist (completed 2026-08-21)

`apply_reference_point_ranking` itself is untouched. Lock updates applied
(additive state fields + ranking-dim documentation; `INTERFACE_LOCKS.md` and
the source lock headers updated in the same change):

1. **`FullLengthMrnaDesignWorkflow` §14 (v3.0.0 → v3.1.0)** — objectives
   assembled from verdicts; reference-point interaction documented (§3.4).
2. **`RnaAptamerDesignWorkflow` §15 (v2.1.0 → v2.2.0)** —
   `ranking_evidence_unavailable` degrade state + light-stage filter degrade
   + gated-call recognition.
3. **`SirnaDesignWorkflow` §10 / `SgRnaDesignWorkflow` §11 / `RnaTertiaryStructureDesignWorkflow` §12**
   — additive `_ranking_governance` state field only.
4. **PA driver expectations** — pending the planned full experimental re-run
   (the user's registered plan): full-length batches gain flags in
   `asf_ranking_note`; aptamer PA runs return the degrade summary. Retained
   batch A/B evidence stays untouched as historical audit trail.
5. **`WORKFLOWS.md`** — ranking-governance block added to the shared ASF
   policy section.
6. **`tests/test_ranking_governance.py`** — new pinned expectations (§7).

## 6. DECISIONS registration

Registered verbatim as [`DECISIONS.md`](DECISIONS.md) **(p)** "Ranking
governance: ASF objectives are assembled from CapGate verdicts (2026-08-21)"
— including the deferred continuous-weighting item and the accepted
unprofiled-enforce divergence (§8.2).

## 7. Test plan (implemented: `tests/test_ranking_governance.py`, 15 tests)

1. **Assembly pinning** — per workflow, `assemble_ranking_objectives` against the
   packaged `default_self_model.json` reproduces the §4 table exactly; the
   workflow modules' `_ORACLE_BACKED_OBJECTIVES` tables are pinned to the same
   sets.
2. **Mode-independence** — identical `ranking_dims` / `demoted` /
   `degrade_reason` under `advisory` and `enforce` (aptamer: demoted under
   both).
3. **Degrade path** — aptamer `rank_and_format` returns success=True with
   `ranking_evidence_unavailable`, empty `errors`, `is_hard_failure` False,
   no `asf_distance` values, generation-order delivery; the governance-off
   counterpart still ranks (utopian ASF 0 for the all-dims champion).
4. **Gated-annotation recognition** — `is_gated_error` semantics (True only
   for `GatedActionError`); the degrade result carries no errors.
5. **No-op regression** — sirna / sgrna / tertiary / full-length: assembly
   keeps every dim and the ASF map over the assembled dims equals the map
   over the full objective list.
6. **Full suite** — 534 passed, 0 failed (baseline 496 + this work).

## 8. Open items — resolutions (2026-08-21)

1. **Aptamer light-stage screening filter** — **resolved**: when RhoFold's
   `screening_evaluation` verdict is a rejection, top-k selection degrades to
   deterministic pool order (`_rhofold_screening_demoted` cached per run;
   state `_screening_governance`); pLDDT no longer arbitrates selection in
   either mode. Gated ProteinX calls no longer raise — they mark the
   annotation and continue.
2. **Unprofiled-enforce divergence** — **accepted and registered** ((p)):
   advisory keeps these dims (gemorna_3utr in full-length, RhoFold under the
   tertiary task key) while enforce blocks the calls and the dims drop at
   measurement time. Registering profiling campaigns requires real anchor
   sets ((l) forbids improvised ones); the divergence closes automatically
   once records exist.
3. **Default-family semantics** — assembly queries `target_family="default"`
   (conservative worst-grade transfer); if workflows ever gain family-aware
   inputs, assembly must follow the same anti-cherry-pick rule.
4. **PA driver default** — unchanged (`advisory`) until the planned full
   experimental re-run validates enforce end-to-end with this mechanism.

## 9. Sequencing note

The user plan is to re-run all experiments after the current adjustment round. Landing
this design **before** that re-run means RNADesign-210 / fig2 regeneration against the
gated platform (the registered next step of (l)) happens exactly once, against a system
whose governance and ranking are already reconciled — instead of regenerating now for
gating and again after this fix.
