from __future__ import annotations

import hashlib
from pathlib import Path

from .day_scanner import find_video_part_json_files


def compute_day_signature(day_folder: Path) -> tuple[str, int]:
    """Compute a fast signature from JSON names, sizes and modification times."""
    digest = hashlib.sha256()
    json_files = find_video_part_json_files(day_folder)
    for path in json_files:
        stat = path.stat()
        relative = path.relative_to(day_folder).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
    return digest.hexdigest(), len(json_files)
