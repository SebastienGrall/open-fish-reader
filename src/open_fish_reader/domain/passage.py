from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Passage:
    id: int
    passage_uuid: str
    station_id: int
    video_part_id: int
    taxon_id: int
    frame_number: int
    position_ms: int
    observed_at: datetime
    individual_count: int
    direction: int
    confidence: str
    needs_review: bool
    glass_position: str
    length_mm: int | None
    length_pixels: float | None
    calibration_id: int | None
    measurement_method: str
    comment: str | None
    created_at: datetime
    updated_at: datetime
