from typing import Any

from ..core.exceptions import InvalidVideoPartJsonError, UnsupportedJsonSchemaError

REQUIRED_FIELDS = {
    "schema_version",
    "record_type",
    "event_id",
    "station_name",
    "video_file",
    "part_number",
    "event_start_time",
    "event_detection_time",
    "video_start_time",
    "video_end_time",
    "frame_count",
    "recording_fps",
    "frame_width",
    "frame_height",
}


def validate_video_part_data(data: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - data.keys())
    if missing:
        raise InvalidVideoPartJsonError("Champs manquants : " + ", ".join(missing))
    if data["schema_version"] != 1:
        raise UnsupportedJsonSchemaError(f"Schéma non pris en charge : {data['schema_version']}")
    if data["record_type"] != "video_part":
        raise InvalidVideoPartJsonError("record_type invalide")
    if not isinstance(data["part_number"], int) or data["part_number"] < 1:
        raise InvalidVideoPartJsonError("part_number invalide")
    if (
        data["frame_count"] < 0
        or data["recording_fps"] <= 0
        or data["frame_width"] <= 0
        or data["frame_height"] <= 0
    ):
        raise InvalidVideoPartJsonError("Métadonnées vidéo invalides")
