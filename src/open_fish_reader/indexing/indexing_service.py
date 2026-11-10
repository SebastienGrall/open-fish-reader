import logging
from pathlib import Path

from ..core.exceptions import IgnoredJsonRecordError
from ..domain.event import Event
from ..domain.video_part import VideoPart
from .day_scanner import find_video_part_json_files
from .event_builder import build_events
from .json_parser import parse_video_part_json

LOGGER = logging.getLogger(__name__)


def index_day(day_folder: Path) -> list[Event]:
    video_parts: list[VideoPart] = []

    for json_path in find_video_part_json_files(day_folder):
        try:
            video_part = parse_video_part_json(json_path)

        except IgnoredJsonRecordError as error:
            LOGGER.info(
                "%s : %s",
                json_path,
                error,
            )
            continue

        video_parts.append(video_part)

    return build_events(video_parts)
