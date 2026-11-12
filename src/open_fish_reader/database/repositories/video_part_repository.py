from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from ...domain.indexed_video_part import IndexedVideoPart


class VideoPartRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_for_day(self, day_date: str, station_folder: Path) -> list[IndexedVideoPart]:
        rows = self.connection.execute(
            """
            SELECT
                video_parts.id,
                video_parts.event_id,
                events.source_event_id,
                video_parts.part_number,
                video_parts.video_relative_path,
                video_parts.video_start_time,
                video_parts.video_end_time,
                video_parts.declared_frame_count,
                video_parts.declared_fps,
                video_parts.frame_width,
                video_parts.frame_height,
                video_parts.review_status,
                video_parts.observation_count,
                video_parts.error_message,
                video_parts.last_viewed_frame
            FROM video_parts
            JOIN events ON events.id = video_parts.event_id
            JOIN days ON days.id = events.day_id
            WHERE days.day_date = ?
            ORDER BY events.event_start_time, video_parts.part_number
            """,
            (day_date,),
        ).fetchall()

        return [
            IndexedVideoPart(
                id=int(row["id"]),
                event_id=int(row["event_id"]),
                source_event_id=str(row["source_event_id"]),
                part_number=int(row["part_number"]),
                video_path=station_folder / str(row["video_relative_path"]),
                video_start_time=datetime.fromisoformat(row["video_start_time"]),
                video_end_time=datetime.fromisoformat(row["video_end_time"]),
                frame_count=int(row["declared_frame_count"]),
                recording_fps=float(row["declared_fps"]),
                frame_width=int(row["frame_width"]),
                frame_height=int(row["frame_height"]),
                review_status=str(row["review_status"] or "unread"),
                observation_count=int(row["observation_count"] or 0),
                error_message=(
                    str(row["error_message"]) if row["error_message"] is not None else None
                ),
                last_viewed_frame=(
                    int(row["last_viewed_frame"]) if row["last_viewed_frame"] is not None else None
                ),
            )
            for row in rows
        ]
