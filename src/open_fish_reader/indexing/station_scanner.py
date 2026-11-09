from pathlib import Path

from ..core.exceptions import InvalidStationFolderError
from ..domain.station import Station
from .day_scanner import (
    find_day_folders,
    find_video_part_json_files,
)
from .json_parser import (
    is_video_part_json,
    parse_video_part_json,
)


def slugify_station_name(name: str) -> str:
    normalized_name = "_".join(name.strip().split())

    return "".join(
        character
        for character in normalized_name
        if character.isalnum() or character in "_-"
    )


def scan_station_identity(
    station_folder: Path,
) -> Station:
    day_folders = find_day_folders(station_folder)

    if not day_folders:
        raise InvalidStationFolderError(
            "Aucune journée contenant un dossier videos "
            "n'a été trouvée."
        )

    for day_folder in day_folders:
        json_paths = find_video_part_json_files(
            day_folder
        )

        for json_path in json_paths:
            if not is_video_part_json(json_path):
                continue

            video_part = parse_video_part_json(
                json_path
            )

            return Station(
                name=video_part.station_name,
                source_folder=station_folder.resolve(),
                slug=slugify_station_name(
                    video_part.station_name
                ),
            )

    raise InvalidStationFolderError(
        "Aucun JSON de type video_part n'a été trouvé "
        "dans les dossiers videos de cette station."
    )