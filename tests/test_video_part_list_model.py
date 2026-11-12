from datetime import UTC, datetime, timedelta
from pathlib import Path

from open_fish_reader.domain.indexed_video_part import IndexedVideoPart
from open_fish_reader.ui.models.video_part_list_item import VideoPartListItem, VideoPartStatus
from open_fish_reader.ui.models.video_part_list_model import VideoPartListModel


def make_part(tmp_path: Path) -> IndexedVideoPart:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"video")
    start = datetime(2026, 11, 11, 12, 5, 50, 545000, tzinfo=UTC)
    return IndexedVideoPart(
        id=1,
        event_id=2,
        source_event_id="event",
        part_number=1,
        video_path=path,
        video_start_time=start,
        video_end_time=start + timedelta(seconds=257.828),
        frame_count=2594,
        recording_fps=10.486,
        frame_width=1280,
        frame_height=720,
    )


def test_item_uses_start_time_and_duration(tmp_path: Path) -> None:
    item = VideoPartListItem.from_indexed_part(make_part(tmp_path))
    assert item.video_start_time.strftime("%H:%M:%S") == "12:05:50"
    assert item.duration_ms == 257_828
    assert item.status is VideoPartStatus.UNREAD


def test_status_can_be_updated(tmp_path: Path) -> None:
    model = VideoPartListModel()
    model.set_items([VideoPartListItem.from_indexed_part(make_part(tmp_path))])
    model.update_status(0, VideoPartStatus.READ)
    assert model.item_at(0).status is VideoPartStatus.READ
