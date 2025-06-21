import logging
from typing import Iterable, Dict, Any

from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository

class CollectorService:
    """
    Сервис для сбора новостей из разных collectors
    и сохранения их в raw-базу DuckDB с фильтрацией дубликатов
    по URL.
    """

    def __init__(
        self,
        raw_client: DuckDBClient,
        collectors: Iterable,
        logger: logging.Logger,
    ):
        self.raw_repo = DuckDBNewsRepository(raw_client)
        self.collectors = collectors
        self.logger = logger

    def collect_and_save(self) -> int:
        all_items: list[Dict[str, Any]] = []
        for collector in self.collectors:
            try:
                items = collector.collect()
                all_items.extend(items)
                self.logger.debug(
                    f"{collector.__class__.__name__} собрал {len(items)} элементов"
                )
            except Exception as e:
                self.logger.error(f"Ошибка в {collector.__class__.__name__}: {e}")

        if not all_items:
            self.logger.info("Новых в raw нет")
            return 0

        rows = self.raw_repo.client.execute(
            "SELECT url FROM news"
        ).fetchall()
        existing_urls = {url for (url,) in rows}

        unique_items: list[Dict[str, Any]] = []
        for item in all_items:
            url = item.get('url')
            if not url:
                continue
            if url in existing_urls:
                continue
            existing_urls.add(url)
            unique_items.append(item)
            print(f"Новая новость: {item}")

        if not unique_items:
            self.logger.info("Новых уникальных новостей нет")
            return 0

        self.raw_repo.insert_news(unique_items)
        count = len(unique_items)
        self.logger.info(f"Сохранили {count} новых в raw")
        return count
