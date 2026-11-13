from datetime import UTC, datetime
from pathlib import Path

from open_fish_reader.database.catalog_schema import create_catalog_schema
from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.size_calibration_repository import (
    SizeCalibrationRepository,
)


def test_calibration_is_selected_by_observation_time(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "calibration.sqlite")
    connection.execute("CREATE TABLE stations (id INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO stations VALUES (1)")
    create_catalog_schema(connection)
    repository = SizeCalibrationRepository(connection)
    now = datetime.now(UTC)
    with connection:
        repository.create(
            station_id=1,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            near_mm_per_pixel=1.2,
            middle_mm_per_pixel=1.5,
            far_mm_per_pixel=1.8,
            comment="terrain",
            now=now,
        )
    calibration = repository.find_for_timestamp(1, datetime(2026, 6, 1, tzinfo=UTC))
    assert calibration is not None
    assert calibration.ratio_for_position("middle") == 1.5
    connection.close()
