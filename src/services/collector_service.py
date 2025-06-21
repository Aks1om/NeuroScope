# src/services/collector_service.py
from typing import Iterable
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.utils.paths import RAW_DB
import logging

class CollectorService:
    def __init__(
        self,
        collectors: Iterable,
        logger: logging.Logger,
    ):
        self.collectors = collectors
        self.raw_repo = DuckDBNewsRepository(DuckDBClient(RAW_DB))
        self.logger = logger

    def collect_and_save(self) -> int:
        all_items = []
        for col in self.collectors:
            try:
                items = col.collect()
                all_items.extend(items)
                self.logger.debug(f"{col.__class__.__name__} собрал {len(items)} элементов")
            except Exception as e:
                self.logger.error(f"Ошибка в {col.__class__.__name__}: {e}")

        if not all_items:
            self.logger.info("Новых в raw нет")
            return 0

        self.raw_repo.insert_news(all_items)
        self.logger.info(f"Сохранили {len(all_items)} новых в raw")
        return len(all_items)
