# src/services/duplicate_filter_service.py
from __future__ import annotations

from typing import List, TypeVar, Generic, Set, Tuple

from pydantic import BaseModel
from src.data_manager.duckdb_repository import DuckDBRepository

T = TypeVar("T", bound=BaseModel)


class DuplicateFilterService(Generic[T]):
    """
    Фильтрация дубликатов по (title, url) на уровне выбранного репозитория.
    Принимает и возвращает список Pydantic-моделей.
    """

    def __init__(self, repo: DuckDBRepository):
        self.repo = repo

    def filter(self, items: List[T]) -> List[T]:
        # загружаем существующие пары title+url
        rows = self.repo.conn.execute(
            f"SELECT title, url FROM {self.repo.table}"
        ).fetchall()
        existing: Set[Tuple[str, str]] = {(t, u) for t, u in rows}

        unique: List[T] = []
        for it in items:
            pair = (it.title, str(it.url))
            if pair in existing:
                continue
            existing.add(pair)
            unique.append(it)
        return unique
