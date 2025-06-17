# src/data_store/duckdb_repository.py
from .base import NewsRepository
from .duckdb_client import DuckDBClient
import uuid

class DuckDBNewsRepository(NewsRepository):
    """
    Репозиторий для сохранения и обновления новостей в DuckDB.
    """
    def __init__(self, db_path: str | Path):
        self.client = DuckDBClient(db_path)

    def insert_news(self, items: list[dict]) -> None:
        """
        Вставить список новостей в таблицу, игнорируя уже существующие по ключу.
        """
        for item in items:
            # Генерация UUID, если нет
            news_id = item.get("id") or str(uuid.uuid4())
            try:
                self.client.execute(
                    "INSERT INTO news (id, title, url, date, content) VALUES (?, ?, ?, ?, ?)",
                    [
                        news_id,
                        item.get("title"),
                        item.get("url"),
                        item.get("date"),
                        item.get("content", "")
                    ]
                )
            except Exception:
                # возможно дубликат ключа — пропускаем
                continue

    def mark_as_sent(self, news_id: str) -> None:
        """
        Отметить новость как отправленную.
        """
        self.client.execute(
            "UPDATE news SET sent = TRUE WHERE id = ?;",
            [news_id]
        )