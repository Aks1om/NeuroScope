# src/services/duplicate_filter_service.py

from typing import List, Dict, Any
from src.data_manager.duckdb_repository import DuckDBNewsRepository

class DuplicateFilterService:
    """
    Сервис для фильтрации дубликатов новостей по заголовку.
    """

    def __init__(self, raw_repo: DuckDBNewsRepository):
        self.raw_repo = raw_repo

    def filter(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Убирает из списка те новости, заголовки которых уже есть в raw-репозитории.
        :param items: список новостей в формате словарей, где ключ 'title' -> заголовок
        :return: отфильтрованный список только новых элементов
        """
        # Получаем все существующие заголовки из raw
        existing = {
            row[0] for row in self.raw_repo.client.execute(
                "SELECT title FROM news"
            ).fetchall()
        }
        # Оставляем только новости с уникальными заголовками
        new_items = [item for item in items if item.get('title') not in existing]
        return new_items
