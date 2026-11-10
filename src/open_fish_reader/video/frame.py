from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtGui import QImage


@dataclass(slots=True)
class DecodedFrame:
    image: QImage
    frame_number: int
    pts: int | None
    position_ms: int
    absolute_timestamp: datetime
