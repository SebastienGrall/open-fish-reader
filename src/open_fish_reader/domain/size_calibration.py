from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SizeCalibration:
    id: int
    calibration_uuid: str
    station_id: int
    valid_from: datetime
    valid_to: datetime | None
    near_mm_per_pixel: float
    middle_mm_per_pixel: float
    far_mm_per_pixel: float
    comment: str | None
    is_active: bool

    def ratio_for_position(self, glass_position: str) -> float:
        ratios = {
            "near": self.near_mm_per_pixel,
            "middle": self.middle_mm_per_pixel,
            "far": self.far_mm_per_pixel,
        }
        try:
            return ratios[glass_position]
        except KeyError as error:
            raise ValueError(f"Position vitre inconnue : {glass_position}") from error
