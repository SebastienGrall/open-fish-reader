from dataclasses import dataclass, field
from datetime import datetime
from .video_part import VideoPart
@dataclass(slots=True)
class Event:
    source_event_id:str; station_name:str; event_start_time:datetime; event_detection_time:datetime; parts:list[VideoPart]=field(default_factory=list)
    @property
    def total_frame_count(self)->int: return sum(p.frame_count for p in self.parts)
