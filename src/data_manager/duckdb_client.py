# src/data_manager/duckdb_client.py
from pathlib import Path
import duckdb
from src.utils.paths import DB

DDL_RAW = """
CREATE TABLE IF NOT EXISTS raw_news (
    id        UBIGINT PRIMARY KEY,
    title     TEXT,
    url       TEXT,
    date      TIMESTAMP,
    text      TEXT,
    media_ids TEXT,
    language  TEXT,
    topic     TEXT
);
"""

DDL_PROCESSED = """
CREATE TABLE IF NOT EXISTS processed_news (
    id        UBIGINT PRIMARY KEY,
    title     TEXT,
    url       TEXT,
    date      TIMESTAMP,
    text      TEXT,
    media_ids TEXT,
    language  TEXT,
    topic     TEXT,
    suggested BOOLEAN DEFAULT FALSE
);
"""

DDL_SENT = """
CREATE TABLE IF NOT EXISTS sent_news (
    id        UBIGINT PRIMARY KEY,
    title     TEXT,
    url       TEXT,
    date      TIMESTAMP,
    text      TEXT,
    media_ids TEXT,
    language  TEXT,
    topic     TEXT,
    confirmed BOOLEAN DEFAULT FALSE,
    main_message_id    BIGINT,
    others_message_ids TEXT
);
"""

class DuckDBClient:
    """Singleton-подключение к DuckDB + создание схемы."""

    def __init__(self, db_path=DB, reset=False):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if reset and self.path.exists():
            self.path.unlink()
        self.conn = duckdb.connect(self.path)
        self._ensure_schema()

    def _ensure_schema(self):
        self.conn.execute(DDL_RAW)
        self.conn.execute(DDL_PROCESSED)
        self.conn.execute(DDL_SENT)
