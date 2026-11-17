from datetime import UTC, datetime
from pathlib import Path

from open_fish_reader.database.connection import open_database
from open_fish_reader.database.taxon_reference_schema import create_taxon_reference_schema


def test_station_copy_can_diverge_from_reference(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "reference.sqlite")
    connection.execute("CREATE TABLE stations (id INTEGER PRIMARY KEY)")
    create_taxon_reference_schema(connection)
    now = datetime.now(UTC).isoformat()
    connection.execute("INSERT INTO development_stages VALUES ('5', 'Adulte', 1, 1)")
    connection.execute(
        """
        INSERT INTO taxon_reference VALUES (
            1, 'ref-uuid', 1, 'SAT', '5', 'Saumon atlantique',
            '2220', 'Salmo salar', 1, ?, ?
        )
        """,
        (now, now),
    )
    connection.execute(
        """
        INSERT INTO taxa VALUES (
            1, 'station-uuid', 1, 'SAT', '5', 'Saumon local',
            '2220', 'Salmo salar', 1, 'S', 1, 'reference', 0, ?, ?
        )
        """,
        (now, now),
    )
    connection.execute("UPDATE taxa SET common_name = 'Saumon station' WHERE id = 1")
    reference_name = connection.execute(
        "SELECT common_name FROM taxon_reference WHERE id = 1"
    ).fetchone()[0]
    station_name = connection.execute("SELECT common_name FROM taxa WHERE id = 1").fetchone()[0]
    assert reference_name == "Saumon atlantique"
    assert station_name == "Saumon station"
    connection.close()
