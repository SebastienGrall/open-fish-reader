import logging
from pathlib import Path

from ..core.exceptions import (
    IgnoredJsonRecordError,
    InvalidStationFolderError,
)
from ..domain.station import Station
from .day_scanner import (
    find_day_folders,
    find_video_part_json_files,
)
from .json_parser import parse_video_part_json

LOGGER = logging.getLogger(__name__)


def slugify(name: str) -> str:
    normalized = "_".join(name.strip().split())

    return "".join(
        character for character in normalized if character.isalnum() or character in "_-"
    )


def scan_station_identity(
    station_folder: Path,
) -> Station:
    for day_folder in find_day_folders(station_folder):
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

            return Station(
                name=video_part.station_name,
                source_folder=station_folder.resolve(),
                slug=slugify(video_part.station_name),
            )

    raise InvalidStationFolderError(
        "Aucun JSON de type video_part valide n'a été trouvé dans la station."
    )
