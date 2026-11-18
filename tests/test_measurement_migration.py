from open_fish_reader.database.connection import open_database
from open_fish_reader.database.migration_v8 import migrate_to_v8


def test_v8_adds_measurement_storage(tmp_path) -> None:
    connection = open_database(tmp_path / "v8.sqlite")
    connection.execute("CREATE TABLE size_calibrations (id INTEGER PRIMARY KEY)")
    connection.execute("CREATE TABLE passages (id INTEGER PRIMARY KEY)")
    migrate_to_v8(connection)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(passages)")}
    assert {"length_pixels", "calibration_id", "measurement_method"} <= columns
    assert (
        connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'passage_measurement_points'"
        ).fetchone()
        is not None
    )
    connection.close()
