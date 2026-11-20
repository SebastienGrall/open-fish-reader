from __future__ import annotations

import sys
from pathlib import Path


def resource_path(
    relative_path: str,
) -> Path:
    if hasattr(sys, "_MEIPASS"):
        root = Path(sys._MEIPASS)
    else:
        root = Path(__file__).resolve().parent.parent

    return root / "resources" / relative_path
