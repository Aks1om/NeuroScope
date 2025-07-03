# src/services/duplicate_filter_service.py

from typing import List, Dict, Any
from src.data_manager.duckdb_repository import DuckDBNewsRepository

class DuplicateFilterService:
    """
    Фильтрация дубликатов по заголовку и URL на основе указанного DuckDBNewsRepository.
    """

    def __init__(self, repo: DuckDBNewsRepository):
        self.repo = repo

    def filter(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 1) Считываем все существующие пары (title, url) из нужной таблицы
        rows = self.repo.conn.execute(
            f"SELECT title, url FROM {self.repo.table}"
        ).fetchall()
        existing = {(t, u) for t, u in rows}

        cleaned: List[Dict[str, Any]] = []
        for it in items:
            title = it.get("title")
            url   = it.get("url")
            if not title or not url:
                # игнорируем неполные записи
                continue
            if (title, url) in existing:
                # дубликат — пропускаем
                continue
            # новый — добавляем в оба списка
            existing.add((title, url))
            cleaned.append(it)

        return cleaned
