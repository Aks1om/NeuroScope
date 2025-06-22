# src/services/collector_service.py
import logging
from typing import Iterable, Dict, Any
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.services.duplicate_filter_service import DuplicateFilterService

class CollectorService:
    """
    Собирает новости у collectors и сохраняет их в raw-базу.
    Все дубликаты по title/url отбиваются в DuplicateFilterService.
    """

    def __init__(
        self,
        raw_repo: DuckDBNewsRepository,
        collectors: Iterable,
        logger: logging.Logger,
    ):
        self.raw_repo = raw_repo
        self.collectors = collectors
        self.logger = logger
        self.duplicate_filter = DuplicateFilterService(raw_repo)

    def collect_and_save(self) -> int:
        all_items = []
        for c in self.collectors:
            try:
                news = c.collect()
                all_items.extend(news)
                self.logger.debug(f"{c.__class__.__name__}: собрано {len(news)}")
            except Exception as e:
                self.logger.error(f"Ошибка {c}: {e}")

        if not all_items:
            self.logger.debug("Нет новых сырых новостей")
            return 0

        unique = self.duplicate_filter.filter(all_items)
        if not unique:
            self.logger.debug("Новых уникальных новостей нет")
            return 0

        count = self.raw_repo.insert_news(unique)
        self.logger.debug(f"Сохранили в raw: {count} новостей")