from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtGui import QImage

from open_fish_reader.domain.media_export import MediaExportRequest
from open_fish_reader.services.media_export_service import MediaExportService


def test_exports_image_and_video_in_taxon_folder(tmp_path: Path) -> None:
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"video")
    image = QImage(20, 10, QImage.Format.Format_RGB32)
    image.fill(0xFF00FF)
    request = MediaExportRequest(
        destination_folder=tmp_path / "exports",
        taxon_code="AGJ",
        taxon_common_name="Anguille jaune",
        export_image=True,
        export_video=True,
        group_by_taxon=True,
    )
    result = MediaExportService().export(
        request,
        image=image,
        source_video_path=source_video,
        station_slug="poses-rg",
        observed_at=datetime(2026, 11, 11, 12, 6, 31, tzinfo=UTC),
        frame_number=425,
    )
    assert result.image_path is not None and result.image_path.exists()
    assert result.video_path is not None and result.video_path.exists()
    assert result.image_path.parent.name == "AGJ_Anguille-jaune"
    assert result.video_path.read_bytes() == b"video"
