from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MediaExportRequest:
    destination_folder: Path
    taxon_code: str | None
    taxon_common_name: str | None
    export_image: bool
    export_video: bool
    group_by_taxon: bool
