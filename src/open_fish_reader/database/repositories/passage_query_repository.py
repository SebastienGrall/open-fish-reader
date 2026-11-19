from __future__ import annotations

import sqlite3
from datetime import datetime


class PassageQueryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_for_period(
        self,
        station_id: int,
        start_at: datetime,
        end_at: datetime,
    ) -> list[dict[str, object]]:
        rows = self.connection.execute(
            """
            SELECT
                passages.id,
                passages.passage_uuid,
                passages.video_part_id,
                passages.frame_number,
                passages.position_ms,
                passages.observed_at,
                passages.individual_count,
                passages.direction,
                passages.confidence,
                passages.needs_review,
                passages.glass_position,
                passages.length_mm,
                passages.comment,
                taxa.tax_code,
                taxa.common_name,
                video_parts.video_file_name
            FROM passages
            JOIN taxa ON taxa.id = passages.taxon_id
            JOIN video_parts ON video_parts.id = passages.video_part_id
            WHERE passages.station_id = ?
              AND passages.observed_at >= ?
              AND passages.observed_at < ?
            ORDER BY passages.observed_at, passages.id
            """,
            (
                station_id,
                start_at.isoformat(timespec="milliseconds"),
                end_at.isoformat(timespec="milliseconds"),
            ),
        ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, passage_id: int) -> int | None:
        row = self.connection.execute(
            "SELECT video_part_id FROM passages WHERE id = ?", (passage_id,)
        ).fetchone()
        if row is None:
            return None
        video_part_id = int(row["video_part_id"])
        self.connection.execute("DELETE FROM passages WHERE id = ?", (passage_id,))
        self.connection.execute(
            """
            UPDATE video_parts
            SET observation_count = MAX(observation_count - 1, 0),
                review_status = CASE
                    WHEN observation_count - 1 <= 0 THEN 'read'
                    ELSE 'observed'
                END
            WHERE id = ?
            """,
            (video_part_id,),
        )
        return video_part_id

    def delete_many(
        self,
        passage_ids: list[int],
    ) -> list[int]:
        if not passage_ids:
            return []

        placeholders = ", ".join("?" for _passage_id in passage_ids)

        rows = self.connection.execute(
            f"""
            SELECT DISTINCT video_part_id
            FROM passages
            WHERE id IN ({placeholders})
            """,
            tuple(passage_ids),
        ).fetchall()

        existing_count = self.connection.execute(
            f"""
                SELECT COUNT(*)
                FROM passages
                WHERE id IN ({placeholders})
                """,
            tuple(passage_ids),
        ).fetchone()[0]

        if existing_count != len(set(passage_ids)):
            raise ValueError("Un ou plusieurs passages sélectionnés sont introuvables.")

        video_part_ids = [int(row["video_part_id"]) for row in rows]

        self.connection.execute(
            f"""
            DELETE FROM passages
            WHERE id IN ({placeholders})
            """,
            tuple(passage_ids),
        )

        for video_part_id in video_part_ids:
            actual_count = self.connection.execute(
                """
                    SELECT COUNT(*)
                    FROM passages
                    WHERE video_part_id = ?
                    """,
                (video_part_id,),
            ).fetchone()[0]

            self.connection.execute(
                """
                UPDATE video_parts
                SET
                    observation_count = ?,
                    review_status = CASE
                        WHEN ? > 0
                        THEN 'observed'

                        WHEN completed_at IS NOT NULL
                        THEN 'read'

                        ELSE review_status
                    END
                WHERE id = ?
                """,
                (
                    actual_count,
                    actual_count,
                    video_part_id,
                ),
            )

        return video_part_ids
