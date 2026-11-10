from pathlib import Path

from ..domain.event import Event
from .day_scanner import find_video_part_json_files
from .event_builder import build_events
from .json_parser import parse_video_part_json


def index_day(day_folder: Path) -> list[Event]:
    video_parts = []

    for json_path in find_video_part_json_files(day_folder):
        video_part = parse_video_part_json(json_path)
        video_parts.append(video_part)

    return build_events(video_parts)
