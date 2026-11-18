from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.size_calibration_repository import SizeCalibrationRepository
from ..domain.size_calibration import SizeCalibration
from ..ui.dialogs.size_calibration_editor_dialog import SizeCalibrationValue


class SizeCalibrationService:
    def list_for_station(self, database_path: Path, station_id: int) -> list[SizeCalibration]:
        connection = open_database(database_path)
        try:
            return SizeCalibrationRepository(connection).list_for_station(station_id)
        finally:
            connection.close()

    def create(self, database_path: Path, station_id: int, value: SizeCalibrationValue) -> int:
        connection = open_database(database_path)
        try:
            with connection:
                return SizeCalibrationRepository(connection).create(
                    station_id=station_id,
                    valid_from=value.valid_from,
                    near_mm_per_pixel=value.near_mm_per_pixel,
                    middle_mm_per_pixel=value.middle_mm_per_pixel,
                    far_mm_per_pixel=value.far_mm_per_pixel,
                    comment=value.comment,
                    now=datetime.now().astimezone(),
                )
        finally:
            connection.close()

    def update_comment(
        self,
        database_path: Path,
        calibration_id: int,
        comment: str | None,
    ) -> None:
        connection = open_database(database_path)
        try:
            with connection:
                SizeCalibrationRepository(connection).update_comment(
                    calibration_id, comment, datetime.now().astimezone()
                )
        finally:
            connection.close()
