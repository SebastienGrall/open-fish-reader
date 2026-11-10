from datetime import UTC, datetime, timedelta
from pathlib import Path

from open_fish_reader.domain.indexed_video_part import IndexedVideoPart
from open_fish_reader.video.cache_policy import (
    decide_full_cache,
    estimate_decoded_memory_bytes,
)


def make_part(
    frame_count: int,
    width: int = 640,
    height: int = 540,
    fps: float = 20.0,
) -> IndexedVideoPart:
    start = datetime.now(UTC)
    return IndexedVideoPart(
        id=1,
        event_id=1,
        source_event_id="event",
        part_number=1,
        video_path=Path("video.mp4"),
        video_start_time=start,
        video_end_time=start + timedelta(seconds=frame_count / fps),
        frame_count=frame_count,
        recording_fps=fps,
        frame_width=width,
        frame_height=height,
    )


def test_short_ofc_clip_uses_full_cache() -> None:
    decision = decide_full_cache(make_part(frame_count=60))
    assert decision.allow_full_cache is True
    assert decision.estimated_bytes < 128 * 1024 * 1024


def test_five_minute_clip_refuses_full_cache() -> None:
    decision = decide_full_cache(make_part(frame_count=6000))
    assert decision.allow_full_cache is False
    assert decision.estimated_bytes > 5 * 1024 * 1024 * 1024


def test_memory_estimate_is_rgb24_size() -> None:
    part = make_part(frame_count=12)
    assert estimate_decoded_memory_bytes(part) == 640 * 540 * 3 * 12
