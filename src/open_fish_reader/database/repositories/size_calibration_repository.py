from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import uuid4

from ...domain.size_calibration import SizeCalibration


class SizeCalibrationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        station_id: int,
        valid_from: datetime,
        near_mm_per_pixel: float,
        middle_mm_per_pixel: float,
        far_mm_per_pixel: float,
        comment: str | None,
        now: datetime,
    ) -> int:
        for value in (near_mm_per_pixel, middle_mm_per_pixel, far_mm_per_pixel):
            if value <= 0:
                raise ValueError("Les ratios millimètres/pixel doivent être positifs.")

        valid_from_iso = valid_from.isoformat(timespec="milliseconds")
        timestamp = now.isoformat(timespec="milliseconds")
        active = self.find_for_timestamp(station_id, valid_from)
        if active is not None and active.valid_from == valid_from:
            raise ValueError("Une calibration existe déjà à cette date pour la station.")

        self.connection.execute(
            """
            UPDATE size_calibrations
            SET valid_to = ?, is_active = 0, updated_at = ?
            WHERE station_id = ? AND valid_to IS NULL
            """,
            (valid_from_iso, timestamp, station_id),
        )
        cursor = self.connection.execute(
            """
            INSERT INTO size_calibrations (
                calibration_uuid, station_id, valid_from, valid_to,
                near_mm_per_pixel, middle_mm_per_pixel, far_mm_per_pixel,
                comment, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                str(uuid4()),
                station_id,
                valid_from_iso,
                near_mm_per_pixel,
                middle_mm_per_pixel,
                far_mm_per_pixel,
                comment,
                timestamp,
                timestamp,
            ),
        )
        return int(cursor.lastrowid)

    def find_for_timestamp(
        self,
        station_id: int,
        observed_at: datetime,
    ) -> SizeCalibration | None:
        row = self.connection.execute(
            """
            SELECT * FROM size_calibrations
            WHERE station_id = ?
              AND valid_from <= ?
              AND (valid_to IS NULL OR valid_to > ?)
            ORDER BY valid_from DESC
            LIMIT 1
            """,
            (
                station_id,
                observed_at.isoformat(timespec="milliseconds"),
                observed_at.isoformat(timespec="milliseconds"),
            ),
        ).fetchone()
        return self._from_row(row) if row is not None else None

    @staticmethod
    def _from_row(row: sqlite3.Row) -> SizeCalibration:
        return SizeCalibration(
            id=int(row["id"]),
            calibration_uuid=str(row["calibration_uuid"]),
            station_id=int(row["station_id"]),
            valid_from=datetime.fromisoformat(row["valid_from"]),
            valid_to=(datetime.fromisoformat(row["valid_to"]) if row["valid_to"] else None),
            near_mm_per_pixel=float(row["near_mm_per_pixel"]),
            middle_mm_per_pixel=float(row["middle_mm_per_pixel"]),
            far_mm_per_pixel=float(row["far_mm_per_pixel"]),
            comment=(str(row["comment"]) if row["comment"] is not None else None),
            is_active=bool(row["is_active"]),
        )
