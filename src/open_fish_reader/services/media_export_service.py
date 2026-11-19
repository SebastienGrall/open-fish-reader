from __future__ import annotations

import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QImage

from ..domain.media_export import MediaExportRequest


@dataclass(frozen=True, slots=True)
class MediaExportResult:
    image_path: Path | None
    video_path: Path | None


class MediaExportService:
    def export(
        self,
        request: MediaExportRequest,
        *,
        image: QImage | None,
        source_video_path: Path | None,
        station_slug: str,
        observed_at: datetime,
        frame_number: int,
    ) -> MediaExportResult:
        if not request.export_image and not request.export_video:
            raise ValueError("Sélectionnez au moins un élément à exporter.")
        if request.export_image and (image is None or image.isNull()):
            raise ValueError("Aucune image n'est actuellement affichée.")
        if request.export_video and (source_video_path is None or not source_video_path.is_file()):
            raise ValueError("Aucune séquence vidéo valide n'est ouverte.")

        output_folder = self._output_folder(request)
        output_folder.mkdir(parents=True, exist_ok=True)

        taxon_code = request.taxon_code or "SANS-TAXON"
        timestamp = observed_at.astimezone().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
        base_name = self._safe_name(f"{station_slug}_{timestamp}_{taxon_code}")

        image_path: Path | None = None
        video_path: Path | None = None

        if request.export_image:
            image_path = self._available_path(
                output_folder / f"{base_name}_image-{frame_number + 1:05d}.png"
            )
            assert image is not None
            if not image.save(str(image_path), "PNG"):
                raise OSError(f"Impossible d'enregistrer l'image : {image_path}")

        if request.export_video:
            assert source_video_path is not None
            suffix = source_video_path.suffix or ".mp4"
            video_path = self._available_path(
                output_folder / f"{base_name}_sequence{suffix.lower()}"
            )
            try:
                shutil.copy2(source_video_path, video_path)
            except OSError:
                if image_path is not None:
                    image_path.unlink(missing_ok=True)
                raise

        return MediaExportResult(image_path=image_path, video_path=video_path)

    def _output_folder(self, request: MediaExportRequest) -> Path:
        if not request.group_by_taxon:
            return request.destination_folder
        if request.taxon_code is None:
            return request.destination_folder / "SANS-TAXON"
        common_name = self._safe_name(request.taxon_common_name or "taxon")
        folder_name = self._safe_name(f"{request.taxon_code}_{common_name}")
        return request.destination_folder / folder_name

    @staticmethod
    def _safe_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        safe_value = re.sub(r'[<>:"/\\|?*]+', "", ascii_value)
        safe_value = re.sub(r"\s+", "-", safe_value.strip())
        safe_value = re.sub(r"-+", "-", safe_value)
        return safe_value.rstrip(". ")[:120] or "export"

    @staticmethod
    def _available_path(path: Path) -> Path:
        if not path.exists():
            return path
        for index in range(1, 10_000):
            candidate = path.with_name(f"{path.stem}_{index:03d}{path.suffix}")
            if not candidate.exists():
                return candidate
        raise OSError(f"Trop de fichiers portent déjà le nom {path.name!r}.")
