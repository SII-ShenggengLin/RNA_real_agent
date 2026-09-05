#!/usr/bin/env python3
"""One-line status snapshot for the Exp 29/30 overnight run."""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "experiments" / "results"
E29 = ROOT / "exp29_aptamer_campaign_arc"
E30 = ROOT / "exp30_production_navigation_live"


def count(p: Path) -> int:
    n = 0
    if p.parent.is_dir():
        for f in sorted(p.parent.glob("runs*.jsonl")):
            n += sum(1 for ln in f.read_text(encoding="utf-8").splitlines()
                     if ln.strip())
    return n


now = time.strftime("%H:%M")
segs = []
for seg in ("seg1_migration", "seg2_reanchor", "seg3_decisive",
            "seg4_confirmation"):
    segs.append(f"{seg.split('_')[0]}:{count(E29 / seg / 'runs_worker0.jsonl')}"
                f"+w{count(E29 / seg / 'runs.jsonl')}")
panels = "Y" if (E29 / "panels.json").is_file() else "-"
arc = "Y" if (E29 / "arc.json").is_file() else "-"
apt = count(E30 / "aptamer" / "runs.jsonl")
mrna = count(E30 / "mrna" / "runs.jsonl")
print(f"{now} | e29 {' '.join(segs)} panels={panels} arc={arc} "
      f"| e30 apt={apt} mrna={mrna}")
