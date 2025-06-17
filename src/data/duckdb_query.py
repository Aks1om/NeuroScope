# src/data_store/duckdb_query.py
from datetime import datetime
from .duckdb_client import DuckDBClient

class DuckDBQuery:
    """
    Утилиты для выборки и фильтрации новостей внутри DuckDB.
    """
    def __init__(self, db_path: str | Path):
        self.client = DuckDBClient(db_path)

    def fetch_unsent(self) -> list[tuple]:
        """
        Вернуть все неотправленные новости.
        """
        rel = self.client.execute(
            "SELECT id, title, url, date, content FROM news WHERE sent = FALSE;"
        )
        return self.client.fetchall(rel)

    def fetch_since(self, cutoff: datetime) -> list[tuple]:
        """
        Вернуть новости не старше cutoff.
        """
        rel = self.client.execute(
            "SELECT id, title, url, date, content FROM news WHERE date >= ?;",
            [cutoff]
        )
        return self.client.fetchall(rel)

    def fetch_by_keywords(self, keywords: list[str]) -> list[tuple]:
        """
        Поиск новостей по ключевым словам в заголовке или контенте.
        """
        pattern = "|".join(keywords)
        rel = self.client.execute(
            "SELECT id, title, url, date, content FROM news \
             WHERE title ~ ? OR content ~ ?;",
            [pattern, pattern]
        )
        return self.client.fetchall(rel)
