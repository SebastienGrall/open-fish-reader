from datetime import UTC, datetime
from pathlib import Path

from open_fish_reader.database.connection import open_database
from open_fish_reader.database.passage_schema import create_passage_schema
from open_fish_reader.services.passage_service import PassageInput, PassageService


def prepare_database(path: Path) -> None:
    connection = open_database(path)
    connection.executescript(
        """
        CREATE TABLE stations (id INTEGER PRIMARY KEY);
        CREATE TABLE taxa (id INTEGER PRIMARY KEY);
        CREATE TABLE video_parts (
            id INTEGER PRIMARY KEY,
            observation_count INTEGER NOT NULL DEFAULT 0,
            review_status TEXT NOT NULL DEFAULT 'unread'
        );
        INSERT INTO stations VALUES (1);
        INSERT INTO taxa VALUES (2);
        INSERT INTO video_parts VALUES (3, 0, 'unread');
        """
    )
    create_passage_schema(connection)
    connection.commit()
    connection.close()


def test_creates_passage_and_updates_video_part(tmp_path: Path) -> None:
    database_path = tmp_path / "passages.sqlite"
    prepare_database(database_path)
    passage = PassageService().create(
        database_path,
        PassageInput(
            station_id=1,
            video_part_id=3,
            taxon_id=2,
            frame_number=426,
            position_ms=40_568,
            observed_at=datetime(2026, 11, 11, 12, 6, 31, 113000, tzinfo=UTC),
            individual_count=1,
            direction=1,
            confidence="certain",
            needs_review=False,
            glass_position="middle",
            length_mm=None,
            comment="",
        ),
    )
    assert passage.frame_number == 426
    assert passage.position_ms == 40_568
    connection = open_database(database_path)
    row = connection.execute(
        "SELECT observation_count, review_status FROM video_parts WHERE id = 3"
    ).fetchone()
    assert tuple(row) == (1, "observed")
    connection.close()
