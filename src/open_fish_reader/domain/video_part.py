from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class VideoPart:
    schema_version: int
    record_type: str
    source_event_id: str
    station_name: str
    video_file: str
    part_number: int
    event_start_time: datetime
    event_detection_time: datetime
    video_start_time: datetime
    video_end_time: datetime
    frame_count: int
    recording_fps: float
    frame_width: int
    frame_height: int
    json_path: Path
    video_path: Path

    @property
    def duration_seconds(self) -> float:
        return (self.video_end_time - self.video_start_time).total_seconds()
