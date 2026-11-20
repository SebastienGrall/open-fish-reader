import sqlite3

from open_fish_reader.services.database_backup_service import DatabaseBackupService


def test_backup_creates_verified_copy(tmp_path) -> None:
    source_path = tmp_path / "source.sqlite"
    connection = sqlite3.connect(source_path)
    connection.execute("CREATE TABLE example (id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO example (value) VALUES ('ok')")
    connection.commit()
    connection.close()

    result = DatabaseBackupService().backup(
        source_path,
        tmp_path / "backups",
        "station-test",
    )

    assert result.output_path.exists()
    assert result.integrity_check == "ok"
    assert result.foreign_key_error_count == 0
    backup = sqlite3.connect(result.output_path)
    assert backup.execute("SELECT value FROM example").fetchone()[0] == "ok"
    backup.close()
