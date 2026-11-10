from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class IndexedVideoPart:
    id: int
    event_id: int
    source_event_id: str
    part_number: int
    video_path: Path
    video_start_time: datetime
    video_end_time: datetime
    frame_count: int
    recording_fps: float
    frame_width: int
    frame_height: int
