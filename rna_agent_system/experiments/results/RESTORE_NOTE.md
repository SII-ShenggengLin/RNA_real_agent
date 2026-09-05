# RESTORE NOTE v2 — Exp 29 expanded-pool campaign mid-run save (2026-09-05 ~02:45)

> Second mid-run shutdown (user-directed). All experiment processes stopped
> cleanly; caches fully merged (root: odesign 1085 / folds 3763 / hotspots 46
> incl 7 ProteinX structure folds). Resume from here.

## Completed & FROZEN (byte-verified or verdict-written — do not re-run)

### 20-target pool (v4 production navigator = least-served band rotation)
- **Four-segment arc** (`exp29_aptamer_campaign_arc/{seg1,seg2,seg3,seg4}*/verdict.json`):
  seg1 1:1 (nav −32% same-delivery cost, spend 32.7/48); seg2 10:9;
  **seg3 10:3 p=0.092 (delivered C24:A17, e2e 4:0 nav-only)**; seg4 1:8 P=0.039.
  Pre-repair registers archived: `seg3_decisive_prerepair{,_v2,_v3b}`.
- **Budget sweep 20-pool**: cap24 **9:3** (C9:A3); cap32 5:5 (8:8);
  `sweep_curve.json` written (fig5h data for the 20-pool points).
- fig5e/f/g/h rendered + raster QA green — **BUT rendered from v3b-era data**;
  re-render on the v4 numbers before any use (scripts unchanged, they read
  the live verdict files — just re-run the four plot scripts).

### Expanded pool (39 targets = 20 + 19 new; v4 navigator)
- Dataset: `data/benchmarks/RNA-BioBench-Aptamer-Expanded/` (12 docking-anchor
  complex targets, protein chains retained; 7 anchor-fasta targets, ProteinX
  folded once and cached under `proteinx::<tid>` keys in the caches).
- **cap16: b:c = 10:2, p = 0.039 — SIGNIFICANT navigation win (C10 vs A2)**.
- cap20: 9:4, p=0.267 (C9:A4). cap24: 10:10 (C15:A15).
- **cap32: 9:23, p = 0.020 — static significantly wins (C15 vs A29)** (the
  mid-budget regime; nav's per-band ~8.7 samples vs static's 10).
- cap48: interrupted with 0 completed records (in-flight work lost by design;
  caches hold the completed requests — resume is cheap). This is the ONLY
  remaining run: `sweep-expanded --workers 7 --resume` finishes cap48 then
  auto-writes `expanded_summary.json` (per-cap full-pool McNemar + e2e sign
  test over base+expanded records).

## Resume procedure (after reboot, GPUs 0/1/2)

```bash
cd rna_agent_system
bash experiments/exp1_bring_up_services.sh          # platform services
# six resident ODesign services (2 per GPU; the throughput fix — model
# weights stay on GPU, ~22 s/request vs ~90 s subprocess path, outputs
# verified byte-identical):
for spec in "0 18112" "0 18113" "1 18114" "1 18115" "2 18116" "2 18117"; do
  set -- $spec; CUDA_VISIBLE_DEVICES=$1 nohup microservices/odesign_service/start_resident.sh $2 > /tmp/odesign_resident_$2.log 2>&1 &
  sleep 8
done
# wait for 6/6 health, then the final leg:
cat > /tmp/exp29_env.sh <<'EOF'
export EXP29_ODESIGN_URLS="http://127.0.0.1:18112/design/from-json,http://127.0.0.1:18113/design/from-json,http://127.0.0.1:18114/design/from-json,http://127.0.0.1:18115/design/from-json,http://127.0.0.1:18116/design/from-json,http://127.0.0.1:18117/design/from-json"
export EXP29_FETCH_POOL=1
export RNADA_CAPGATE=advisory
EOF
source /tmp/exp29_env.sh
PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp29_aptamer_campaign_arc.py sweep-expanded --workers 7 --resume
```

## After cap48 completes (the remaining work)

1. Read `expanded_summary.json` — per-cap delivered/b:c/p + e2e pairing.
2. Re-render fig5e/f/g (v4 numbers) and rebuild fig5h as the FULL cap curve
   (16/20/24/32/48, expanded pool + 20-pool points; the current fig5h script
   reads sweep_curve.json — extend it to the expanded summary).
3. Docs re-base with the final curve: the honest shape is a regime story —
   starvation budgets: navigation significantly better (cap16 10:2, p=0.039);
   mid budgets: static significantly better (cap32 9:23) — disclose both;
   registered 48: parity (20-pool 8:9, e2e 4:0 nav-only); easy regime: −32%
   cost at identical delivery. §2.5/legend/FACT_SHEET/CHANGELOG/AGENTS
   currently carry v3b-era numbers in places — full re-base pending.
4. `navigation_raw_budget` is a production knob (tested); v4 navigator code
   + tests are final (650+ passed before the expanded run).

## Known issues / notes

- The cap32 static-side win is REAL (p=0.02), not a bug: mid-budget band
  depth 10 vs ~8.7 favours the static equal split. Any narrative must carry
  both directions.
- One cap16 target record failed (38/39; boundary) — verdicts note it.
- Watch for pkill/pgrep SELF-MATCH when killing by pattern (it killed our
  own compound commands twice): use bracket patterns `[-]` or exact PIDs.
- The milestone watcher + heartbeat scripts are in /tmp (gone after reboot)
  — optional to recreate.
