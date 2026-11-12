from pathlib import Path

from open_fish_reader.indexing.day_signature import (
    compute_day_source_state,
)


def test_removing_json_and_video_changes_signature(
    tmp_path: Path,
) -> None:
    day_folder = tmp_path / "2026-11-11"
    videos_folder = day_folder / "videos"
    videos_folder.mkdir(parents=True)

    json_path = videos_folder / "part001.json"
    video_path = videos_folder / "part001.mp4"

    json_path.write_text(
        '{"record_type": "video_part"}',
        encoding="utf-8",
    )
    video_path.write_bytes(b"fake-video")

    before = compute_day_source_state(day_folder)

    assert before.json_count == 1
    assert before.video_count == 1

    json_path.unlink()
    video_path.unlink()

    after = compute_day_source_state(day_folder)

    assert after.json_count == 0
    assert after.video_count == 0
    assert after.signature != before.signature


def test_removing_only_video_changes_signature(
    tmp_path: Path,
) -> None:
    day_folder = tmp_path / "2026-11-11"
    videos_folder = day_folder / "videos"
    videos_folder.mkdir(parents=True)

    json_path = videos_folder / "part001.json"
    video_path = videos_folder / "part001.mp4"

    json_path.write_text(
        '{"record_type": "video_part"}',
        encoding="utf-8",
    )
    video_path.write_bytes(b"fake-video")

    before = compute_day_source_state(day_folder)

    video_path.unlink()

    after = compute_day_source_state(day_folder)

    assert after.json_count == 1
    assert after.video_count == 0
    assert after.signature != before.signature
