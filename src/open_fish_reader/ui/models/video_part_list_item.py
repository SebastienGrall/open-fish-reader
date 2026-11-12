from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from ...domain.indexed_video_part import IndexedVideoPart


class VideoPartStatus(StrEnum):
    UNREAD = "unread"
    IN_PROGRESS = "in_progress"
    READ = "read"
    OBSERVED = "observed"
    REVIEW = "review"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class VideoPartListItem:
    video_part_id: int
    event_id: int
    source_event_id: str
    part_number: int
    video_path: Path
    video_start_time: datetime
    duration_ms: int
    frame_count: int
    status: VideoPartStatus = VideoPartStatus.UNREAD
    observation_count: int = 0
    error_message: str | None = None

    @classmethod
    def from_indexed_part(
        cls,
        part: IndexedVideoPart,
    ) -> VideoPartListItem:
        duration_ms = max(
            0,
            round((part.video_end_time - part.video_start_time).total_seconds() * 1000),
        )
        status = VideoPartStatus.UNREAD if part.video_path.is_file() else VideoPartStatus.ERROR
        return cls(
            video_part_id=part.id,
            event_id=part.event_id,
            source_event_id=part.source_event_id,
            part_number=part.part_number,
            video_path=part.video_path,
            video_start_time=part.video_start_time,
            duration_ms=duration_ms,
            frame_count=part.frame_count,
            status=status,
            error_message=(
                None if status is VideoPartStatus.UNREAD else "Fichier vidéo introuvable"
            ),
        )
