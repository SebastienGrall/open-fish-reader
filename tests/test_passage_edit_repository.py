from datetime import UTC, datetime

from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.passage_edit_repository import PassageEditRepository


def test_update_preserves_measurement(tmp_path) -> None:
    connection = open_database(tmp_path / "edit.sqlite")
    connection.execute(
        """
        CREATE TABLE passages (
            id INTEGER PRIMARY KEY, taxon_id INTEGER, individual_count INTEGER,
            direction INTEGER, confidence TEXT, needs_review INTEGER,
            glass_position TEXT, comment TEXT, updated_at TEXT,
            length_mm INTEGER, length_pixels REAL, calibration_id INTEGER,
            measurement_method TEXT
        )
        """
    )
    connection.execute(
        "INSERT INTO passages VALUES (1, 2, 1, 1, 'certain', 0, 'middle', '', '', 300, 200, 7, 'polyline_calibration')"
    )
    with connection:
        PassageEditRepository(connection).update(
            passage_id=1,
            taxon_id=3,
            individual_count=2,
            direction=-1,
            confidence="probable",
            needs_review=True,
            glass_position="middle",
            comment="corrigé",
            now=datetime.now(UTC),
        )
    row = connection.execute("SELECT * FROM passages WHERE id = 1").fetchone()
    assert row["taxon_id"] == 3
    assert row["length_pixels"] == 200
    assert row["calibration_id"] == 7
    assert row["measurement_method"] == "polyline_calibration"
    connection.close()
