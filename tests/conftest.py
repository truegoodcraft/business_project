from __future__ import annotations

import sys
from pathlib import Path

# Ensure local stub packages (e.g., httpx) are importable during tests
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
