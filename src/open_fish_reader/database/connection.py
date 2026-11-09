import sqlite3
from pathlib import Path
def open_database(path:Path)->sqlite3.Connection:
    path.parent.mkdir(parents=True,exist_ok=True); c=sqlite3.connect(path); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA busy_timeout=5000'); return c
