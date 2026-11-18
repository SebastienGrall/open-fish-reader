from datetime import UTC, datetime

from open_fish_reader.database.catalog_schema import create_catalog_schema
from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.size_calibration_repository import (
    SizeCalibrationRepository,
)


def test_new_calibration_closes_previous(tmp_path) -> None:
    connection = open_database(tmp_path / "periods.sqlite")
    connection.execute("CREATE TABLE stations (id INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO stations VALUES (1)")
    create_catalog_schema(connection)
    repository = SizeCalibrationRepository(connection)
    now = datetime.now(UTC)
    with connection:
        repository.create(
            station_id=1,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            near_mm_per_pixel=1.0,
            middle_mm_per_pixel=1.2,
            far_mm_per_pixel=1.4,
            comment="A",
            now=now,
        )
        repository.create(
            station_id=1,
            valid_from=datetime(2026, 6, 1, tzinfo=UTC),
            near_mm_per_pixel=1.1,
            middle_mm_per_pixel=1.3,
            far_mm_per_pixel=1.5,
            comment="B",
            now=now,
        )
    rows = repository.list_for_station(1)
    assert rows[0].valid_to is None
    assert rows[1].valid_to == datetime(2026, 6, 1, tzinfo=UTC)
    assert repository.find_for_timestamp(1, datetime(2026, 3, 1, tzinfo=UTC)).comment == "A"
    connection.close()
