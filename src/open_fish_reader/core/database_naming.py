from __future__ import annotations

import hashlib
from pathlib import Path


def station_database_name(station_slug: str, source_folder: Path) -> str:
    """Return a stable, collision-resistant database filename for a station folder."""
    normalized = str(source_folder.resolve()).casefold().encode("utf-8")
    short_hash = hashlib.sha256(normalized).hexdigest()[:8]
    return f"{station_slug.lower()}_{short_hash}.sqlite"
