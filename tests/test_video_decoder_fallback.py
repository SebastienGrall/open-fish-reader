from datetime import UTC, datetime
from pathlib import Path

from open_fish_reader.domain.indexed_video_part import IndexedVideoPart
from open_fish_reader.video.video_decoder import VideoDecoder


def test_decoder_exposes_sequence_method() -> None:
    decoder = VideoDecoder()
    assert callable(decoder.decode_all_frames)


def test_indexed_part_can_be_created() -> None:
    part = IndexedVideoPart(
        id=1,
        event_id=1,
        source_event_id="event",
        part_number=1,
        video_path=Path("video.mp4"),
        video_start_time=datetime.now(UTC),
        video_end_time=datetime.now(UTC),
        frame_count=12,
        recording_fps=20.0,
        frame_width=640,
        frame_height=540,
    )
    assert part.frame_count == 12
