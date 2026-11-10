import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.exceptions import InvalidVideoPartJsonError
from ..domain.video_part import VideoPart
from .json_validator import validate_video_part_data


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidVideoPartJsonError(f"JSON illisible : {path.name}") from error

    if not isinstance(data, dict):
        raise InvalidVideoPartJsonError(f"Le JSON doit contenir un objet : {path.name}")

    return data


def is_video_part_json(path: Path) -> bool:
    """
    Indique si le fichier est une métadonnée de partie vidéo.

    Les autres JSON éventuellement présents dans le dossier videos
    sont ignorés par l'indexeur.
    """
    try:
        data = load_json_file(path)
    except InvalidVideoPartJsonError:
        return False

    return data.get("record_type") == "video_part"


def parse_iso_datetime(value: str) -> datetime:
    try:
        parsed_value = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise InvalidVideoPartJsonError(f"Horodatage ISO 8601 invalide : {value}") from error

    if parsed_value.tzinfo is None:
        raise InvalidVideoPartJsonError(f"L'horodatage ne contient pas de fuseau horaire : {value}")

    return parsed_value


def parse_video_part_json(path: Path) -> VideoPart:
    data = load_json_file(path)
    validate_video_part_data(data)

    video_start_time = parse_iso_datetime(data["video_start_time"])
    video_end_time = parse_iso_datetime(data["video_end_time"])

    if video_end_time < video_start_time:
        raise InvalidVideoPartJsonError(
            f"video_end_time est antérieur à video_start_time dans {path.name}"
        )

    return VideoPart(
        schema_version=data["schema_version"],
        record_type=data["record_type"],
        source_event_id=data["event_id"],
        station_name=data["station_name"],
        video_file=data["video_file"],
        part_number=data["part_number"],
        event_start_time=parse_iso_datetime(data["event_start_time"]),
        event_detection_time=parse_iso_datetime(data["event_detection_time"]),
        video_start_time=video_start_time,
        video_end_time=video_end_time,
        frame_count=data["frame_count"],
        recording_fps=float(data["recording_fps"]),
        frame_width=data["frame_width"],
        frame_height=data["frame_height"],
        json_path=path,
        video_path=path.parent / data["video_file"],
    )
