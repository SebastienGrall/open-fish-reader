from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from ..core.constants import VIDEO_FOLDER_NAME


@dataclass(frozen=True, slots=True)
class DaySourceState:
    signature: str
    json_count: int
    video_count: int


def compute_day_source_state(
    day_folder: Path,
) -> DaySourceState:
    videos_folder = day_folder / VIDEO_FOLDER_NAME

    if not videos_folder.is_dir():
        signature = hashlib.sha256(b"missing-videos-folder").hexdigest()

        return DaySourceState(
            signature=signature,
            json_count=0,
            video_count=0,
        )

    source_files = sorted(
        (
            path
            for path in videos_folder.iterdir()
            if path.is_file() and path.suffix.lower() in {".json", ".mp4"}
        ),
        key=lambda path: path.name.casefold(),
    )

    digest = hashlib.sha256()
    json_count = 0
    video_count = 0

    for path in source_files:
        stat = path.stat()

        relative_path = path.relative_to(day_folder).as_posix().casefold()

        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")

        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")

        digest.update(str(stat.st_mtime_ns).encode("ascii"))
        digest.update(b"\0")

        suffix = path.suffix.lower()

        if suffix == ".json":
            json_count += 1
        elif suffix == ".mp4":
            video_count += 1

    digest.update(f"json={json_count}".encode("ascii"))
    digest.update(b"\0")

    digest.update(f"video={video_count}".encode("ascii"))

    return DaySourceState(
        signature=digest.hexdigest(),
        json_count=json_count,
        video_count=video_count,
    )


def compute_day_signature(
    day_folder: Path,
) -> tuple[str, int]:
    """Retourne la signature et le nombre de JSON.

    Cette fonction conserve l'interface utilisée par
    DayIndexingService. La signature prend désormais
    aussi en compte les fichiers MP4.
    """

    state = compute_day_source_state(day_folder)

    return (
        state.signature,
        state.json_count,
    )
