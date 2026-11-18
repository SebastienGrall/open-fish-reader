from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.passage_query_repository import PassageQueryRepository


def test_delete_decrements_video_part_counter(tmp_path) -> None:
    connection = open_database(tmp_path / "query.sqlite")
    connection.executescript(
        """
        CREATE TABLE passages (id INTEGER PRIMARY KEY, video_part_id INTEGER NOT NULL);
        CREATE TABLE video_parts (
            id INTEGER PRIMARY KEY,
            observation_count INTEGER NOT NULL,
            review_status TEXT NOT NULL
        );
        INSERT INTO video_parts VALUES (3, 1, 'observed');
        INSERT INTO passages VALUES (4, 3);
        """
    )
    with connection:
        video_part_id = PassageQueryRepository(connection).delete(4)
    assert video_part_id == 3
    row = connection.execute("SELECT * FROM video_parts WHERE id = 3").fetchone()
    assert row["observation_count"] == 0
    assert row["review_status"] == "read"
    connection.close()
