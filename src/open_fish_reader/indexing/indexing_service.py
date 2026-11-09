from pathlib import Path

from ..domain.event import Event
from .day_scanner import find_video_part_json_files
from .event_builder import build_events
from .json_parser import (
    is_video_part_json,
    parse_video_part_json,
)


def index_day(day_folder: Path) -> listvideo_parts = []

    for json_path in find_video_part_json_files(
        day_folder
    ):
        if not is_video_part_json(json_path):
            continue

        video_parts.append(
            parse_video_part_json(json_path)
        )

    return build_events(video_parts)