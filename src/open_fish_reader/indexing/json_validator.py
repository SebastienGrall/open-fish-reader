from typing import Any

from ..core.exceptions import (
    IgnoredJsonRecordError,
    InvalidVideoPartJsonError,
    UnsupportedJsonSchemaError,
)

COMMON_REQUIRED_FIELDS = {
    "schema_version",
    "record_type",
}

VIDEO_PART_REQUIRED_FIELDS = {
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
    missing_common_fields = sorted(COMMON_REQUIRED_FIELDS - data.keys())

    if missing_common_fields:
        raise InvalidVideoPartJsonError(
            "Champs JSON communs manquants : " + ", ".join(missing_common_fields)
        )

    if data["schema_version"] != 1:
        raise UnsupportedJsonSchemaError(
            f"Schéma JSON non pris en charge : {data['schema_version']}"
        )

    if data["record_type"] != "video_part":
        raise IgnoredJsonRecordError(f"JSON ignoré, record_type={data['record_type']!r}")

    missing_video_fields = sorted(VIDEO_PART_REQUIRED_FIELDS - data.keys())

    if missing_video_fields:
        raise InvalidVideoPartJsonError(
            "Champs video_part manquants : " + ", ".join(missing_video_fields)
        )

    if not isinstance(data["part_number"], int) or data["part_number"] < 1:
        raise InvalidVideoPartJsonError("part_number doit être un entier positif.")

    if not isinstance(data["frame_count"], int) or data["frame_count"] < 0:
        raise InvalidVideoPartJsonError("frame_count doit être un entier positif ou nul.")

    if data["recording_fps"] <= 0:
        raise InvalidVideoPartJsonError("recording_fps doit être strictement positif.")

    if data["frame_width"] <= 0 or data["frame_height"] <= 0:
        raise InvalidVideoPartJsonError("Les dimensions vidéo doivent être positives.")
