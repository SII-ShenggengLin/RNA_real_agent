from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure():
    # Ensure `agent_core` is importable (mirrors frontend/app.py behavior).
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

