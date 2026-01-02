from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = ROOT / "cli" / "src"

if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))
