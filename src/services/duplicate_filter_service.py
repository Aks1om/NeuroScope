# src/services/duplicate_filter_service.py
from typing import List, Dict, Any
from src.data_manager.duckdb_repository import DuckDBNewsRepository

class DuplicateFilterService:
    """
    Централизованный сервис фильтрации дубликатов по заголовку и URL.
    """
    def __init__(self, raw_repo: DuckDBNewsRepository):
        self.raw_repo = raw_repo

    def filter(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # получаем существующие заголовки и URL
        rows = self.raw_repo.client.execute(
            "SELECT title, url FROM news"
        ).fetchall()
        existing_titles = {t for t, _ in rows}
        existing_urls   = {u for _, u in rows}

        cleaned = []
        for item in items:
            title = item.get('title')
            url   = item.get('url')
            if not title or not url:
                continue
            if title in existing_titles or url in existing_urls:
                continue
            existing_titles.add(title)
            existing_urls.add(url)
            cleaned.append(item)
        return cleaned
