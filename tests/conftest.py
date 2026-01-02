from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


def _running_inside_binary_ninja() -> bool:
    try:
        return importlib.util.find_spec("binaryninjaui") is not None
    except (ValueError, ImportError):
        return False


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if not _running_inside_binary_ninja():
    os.environ.setdefault("FORCE_BINJA_MOCK", "1")
    from binja_test_mocks import binja_api  # noqa: F401
