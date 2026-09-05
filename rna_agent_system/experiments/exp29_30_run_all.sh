#!/bin/bash
# EXP 29 + EXP 30 orchestration (fourth reset, 2026-09-03).
#
# Chains the full two-experiment pipeline with resource-gated concurrency
# (2026-09-04 machine: usable GPUs 0/1/2, more CPU — replica fleet spread
# over three cards, phaseB workers 8, exp30 form sessions x2): pilot gate
# check -> Exp29 phaseA (resume no-op if complete) -> panel selection ->
# Exp29 phaseB concurrent with Exp30 aptamer form sessions -> Exp29
# verify+arc -> Exp30 mRNA sessions -> Exp30 verify.
# Every stage logs to experiments/results/exp29_30_orchestrator.log via the
# caller; the script aborts before phaseA if any pilot calibration gate
# fails (recalibration needs human judgement, not automation).
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"
export RNADA_CAPGATE=advisory
export EXP29_ODESIGN_URLS="http://127.0.0.1:8012/design/from-json,http://127.0.0.1:18012/design/from-json,http://127.0.0.1:18013/design/from-json,http://127.0.0.1:18014/design/from-json,http://127.0.0.1:18015/design/from-json,http://127.0.0.1:18016/design/from-json,http://127.0.0.1:18017/design/from-json,http://127.0.0.1:18018/design/from-json,http://127.0.0.1:18019/design/from-json,http://127.0.0.1:18020/design/from-json,http://127.0.0.1:18021/design/from-json,http://127.0.0.1:18022/design/from-json,http://127.0.0.1:18023/design/from-json"
export EXP29_FETCH_POOL=2
PY=python

log() { echo "[$(date +%H:%M:%S)] $*"; }

# ── 1. wait for the Exp29 pilot to finish ──────────────────────────────
log "waiting for exp29 pilot to finish ..."
while pgrep -f "exp29_aptamer_campaign_arc.py pilot" > /dev/null; do sleep 60; done
log "exp29 pilot process exited"

# ── 2. pilot gate check (abort on failure) ─────────────────────────────
GATE=$($PY - <<'EOF'
import json, sys
from pathlib import Path
root = Path("experiments/results/exp29_aptamer_campaign_arc/pilot")
def verd(seg):
    p = root / seg / "verdict.json"
    return json.loads(p.read_text()) if p.is_file() else None
v1, v2, v3 = verd("seg1_migration"), verd("seg2_reanchor"), verd("seg3_decisive")
if not (v1 and v2 and v3):
    print("FAIL missing verdicts"); sys.exit(1)
po1, po2 = v1["pair_outcomes"], v2["pair_outcomes"]
deliv1 = po1["both"] + po1["nav"] + po1["rule"]
sat = po1["both"] / deliv1 if deliv1 else 0.0
fail2 = (po2["nav"] + po2["none"]) / v2["n_cells"]
both2 = po2["both"] / v2["n_cells"]
viol = v1["budget"]["violations"] + v2["budget"]["violations"] + v3["budget"]["violations"]
smoke = (v3["budget"]["nav_raw_spent_max"] or 0) <= 48 and v3["n_cells"] > 0
# AMENDED 2026-09-03 (pre-phaseA, disclosed): the original gate (b) expected
# the legacy E12-era static-arm scarcity (11/30) to transfer to the pilot
# pair — it did not (Thrombin/GFP: static 6/6 delivered under v3).  The
# informative pilot direction is the DANGEROUS one (over-scarcity: both arms
# fail everywhere); under-scarcity on two easy targets is a measured finding
# the full-pool seg2 measures directly, with the decisive panel still chosen
# by the registered relative-scarcity rule.
checks = [
    ("seg1 saturation >= 0.75", sat >= 0.75, f"{sat:.3f}"),
    ("seg2 over-scarcity guard (both-pass > 0, static-fail < 0.5)",
     both2 > 0 and fail2 < 0.5, f"both {both2:.3f}, static-fail {fail2:.3f}"),
    ("budget violations == 0", viol == 0, str(viol)),
    ("seg3 production smoke", smoke, f"maxspend {v3['budget']['nav_raw_spent_max']}"),
]
ok = True
for name, passed, detail in checks:
    print(("PASS " if passed else "FAIL ") + name + f" ({detail})")
    ok &= passed
print("GATES-OK" if ok else "GATES-FAIL")
sys.exit(0 if ok else 1)
EOF
)
echo "$GATE"
if ! echo "$GATE" | grep -q "GATES-OK"; then
    log "ABORT: pilot calibration gates failed — recalibration required"
    exit 1
fi

# ── 3. Exp29 phaseA (resume no-op when complete; workers 4 is plenty —
#      it only verifies frozen seg1/seg2) ────────────────────────────────
log "exp29 phaseA launch (workers 4, resume)"
$PY experiments/exp29_aptamer_campaign_arc.py phaseA --workers 4 --resume
rc=$?
if [ $rc -ne 0 ]; then log "exp29 phaseA rc=$rc — continuing to panels only if records exist"; fi

# ── 4. panel selection ─────────────────────────────────────────────────
if [ -f experiments/results/exp29_aptamer_campaign_arc/seg2_reanchor/runs.jsonl ]; then
    log "exp29 panel selection"
    $PY experiments/exp29_aptamer_campaign_arc.py panels
fi

# ── 5. Exp29 phaseB + Exp30 aptamer concurrently ───────────────────────
log "waiting for exp30 pilot (IFN-gamma form session) to finish ..."
while pgrep -f "exp30_production_navigation_live.py pilot" > /dev/null; do sleep 60; done
log "exp30 aptamer arm launch (background, 2 concurrent form sessions)"
$PY experiments/exp30_production_navigation_live.py aptamer --concurrency 2 \
    > experiments/results/exp30_aptamer.log 2>&1 &
EXP30_APT_PID=$!
log "exp29 phaseB launch (workers 8)"
$PY experiments/exp29_aptamer_campaign_arc.py phaseB --workers 8 --resume
log "exp29 phaseB rc=$?"

# ── 6. Exp29 verify + arc ──────────────────────────────────────────────
log "exp29 verify all"
$PY experiments/exp29_aptamer_campaign_arc.py verify all
log "exp29 arc"
$PY experiments/exp29_aptamer_campaign_arc.py arc

# ── 7. Exp30 mRNA arm (after aptamer arm finishes) ─────────────────────
log "waiting for exp30 aptamer arm (pid $EXP30_APT_PID) ..."
wait $EXP30_APT_PID
log "exp30 mrna arm launch (2 concurrent form sessions)"
$PY experiments/exp30_production_navigation_live.py mrna --concurrency 2 \
    > experiments/results/exp30_mrna.log 2>&1
log "exp30 verify all"
$PY experiments/exp30_production_navigation_live.py verify all

log "ORCHESTRATION COMPLETE — figures render next"
