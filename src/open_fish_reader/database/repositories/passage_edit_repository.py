from __future__ import annotations

import sqlite3
from datetime import datetime


class PassageEditRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_for_edit(self, passage_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT
                passages.id,
                passages.passage_uuid,
                passages.taxon_id,
                passages.observed_at,
                passages.video_part_id,
                passages.frame_number,
                passages.individual_count,
                passages.direction,
                passages.confidence,
                passages.needs_review,
                passages.glass_position,
                passages.length_mm,
                passages.length_pixels,
                passages.calibration_id,
                passages.measurement_method,
                passages.comment,
                video_parts.video_file_name,
                COUNT(passage_measurement_points.id) AS measurement_point_count
            FROM passages
            JOIN video_parts ON video_parts.id = passages.video_part_id
            LEFT JOIN passage_measurement_points
                ON passage_measurement_points.passage_id = passages.id
            WHERE passages.id = ?
            GROUP BY passages.id
            """,
            (passage_id,),
        ).fetchone()

    def update(
        self,
        *,
        passage_id: int,
        taxon_id: int,
        individual_count: int,
        direction: int,
        confidence: str,
        needs_review: bool,
        glass_position: str,
        comment: str | None,
        now: datetime,
    ) -> None:
        cursor = self.connection.execute(
            """
            UPDATE passages
            SET taxon_id = ?,
                individual_count = ?,
                direction = ?,
                confidence = ?,
                needs_review = ?,
                glass_position = ?,
                comment = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                taxon_id,
                individual_count,
                direction,
                confidence,
                int(needs_review),
                glass_position,
                comment,
                now.isoformat(timespec="milliseconds"),
                passage_id,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("Le passage à modifier est introuvable.")
