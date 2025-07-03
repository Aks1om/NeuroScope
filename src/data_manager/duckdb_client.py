# src/data_manager/duckdb_client.py
import duckdb
from pathlib import Path
from src.utils.paths import DB

class DuckDBClient:
    def __init__(self, db_path: Path | str = DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._ensure_tables()

    def _ensure_tables(self):
        # 1) Сырая таблица
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_news (
          id         BIGINT PRIMARY KEY,
          title      VARCHAR,
          url        VARCHAR,
          date       TIMESTAMP,
          content    VARCHAR,
          media_ids  VARCHAR[],
          language   VARCHAR,
          topic      VARCHAR
        );
        """)

        # 2) Обработанная таблица
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_news (
          id         BIGINT PRIMARY KEY,
          title      VARCHAR,
          url        VARCHAR,
          date       TIMESTAMP,
          content    VARCHAR,
          media_ids  VARCHAR[],
          language   VARCHAR,
          topic      VARCHAR,
          suggested  BOOLEAN DEFAULT FALSE
        );
        """)

    def fetchdf(self, relation):
        """Вернуть результат запроса в виде pandas.DataFrame."""
        return relation.df()
