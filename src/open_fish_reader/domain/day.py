from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(slots=True)
class Day:
    day_date: date
    relative_folder: Path
    id: int | None = None
    event_count: int = 0
    video_part_count: int = 0
