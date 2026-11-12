from __future__ import annotations

import sqlite3
from datetime import datetime


class VideoPartStatusRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def mark_opened(
        self,
        video_part_id: int,
        now: datetime,
    ) -> None:
        timestamp = now.isoformat(timespec="milliseconds")
        self.connection.execute(
            """
            UPDATE video_parts
            SET review_status = CASE
                    WHEN review_status = 'unread' THEN 'in_progress'
                    ELSE review_status
                END,
                first_opened_at = COALESCE(first_opened_at, ?),
                last_opened_at = ?,
                error_message = NULL
            WHERE id = ?
            """,
            (timestamp, timestamp, video_part_id),
        )

    def update_position(
        self,
        video_part_id: int,
        frame_index: int,
        now: datetime,
    ) -> None:
        self.connection.execute(
            """
            UPDATE video_parts
            SET last_viewed_frame = ?, last_opened_at = ?
            WHERE id = ?
            """,
            (
                max(0, frame_index),
                now.isoformat(timespec="milliseconds"),
                video_part_id,
            ),
        )

    def mark_completed(
        self,
        video_part_id: int,
        final_frame_index: int,
        now: datetime,
    ) -> None:
        timestamp = now.isoformat(timespec="milliseconds")
        self.connection.execute(
            """
            UPDATE video_parts
            SET review_status = CASE
                    WHEN observation_count > 0 THEN 'observed'
                    ELSE 'read'
                END,
                last_viewed_frame = ?,
                last_opened_at = ?,
                completed_at = COALESCE(completed_at, ?),
                error_message = NULL
            WHERE id = ?
            """,
            (max(0, final_frame_index), timestamp, timestamp, video_part_id),
        )

    def mark_error(
        self,
        video_part_id: int,
        message: str,
        now: datetime,
    ) -> None:
        self.connection.execute(
            """
            UPDATE video_parts
            SET review_status = 'error', error_message = ?, last_opened_at = ?
            WHERE id = ?
            """,
            (
                message,
                now.isoformat(timespec="milliseconds"),
                video_part_id,
            ),
        )

    def set_observation_count(
        self,
        video_part_id: int,
        observation_count: int,
        now: datetime,
    ) -> None:
        count = max(0, observation_count)
        self.connection.execute(
            """
            UPDATE video_parts
            SET observation_count = ?,
                review_status = CASE
                    WHEN ? > 0 THEN 'observed'
                    WHEN completed_at IS NOT NULL THEN 'read'
                    ELSE 'in_progress'
                END,
                last_opened_at = ?
            WHERE id = ?
            """,
            (
                count,
                count,
                now.isoformat(timespec="milliseconds"),
                video_part_id,
            ),
        )
