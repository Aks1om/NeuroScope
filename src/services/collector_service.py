# src/services/collector_service.py
import logging
import hashlib
from typing import Iterable, Dict, Any
from src.services.duplicate_filter_service import DuplicateFilterService

class CollectorService:
    """
    Собирает новости у collectors и сохраняет их в raw-базу.
    Все дубликаты по title/url отбиваются в DuplicateFilterService.
    """

    def __init__(self, raw_repo, collector, translate_service, logger):
        self.raw_repo = raw_repo
        self.collector = collector
        self.translate_service = translate_service
        self.logger = logger
        self.duplicate_filter = DuplicateFilterService(raw_repo)

    def _generate_id(self, url: str) -> int:
        h = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
        return int(h, 16)

    def collect_and_save(self) -> int:
        # 1) Запрашиваем уже «причесанные» элементы
        items = self.collector.collect()
        self.logger.debug(f"WebScraperCollector: собрано {len(items)} новостей")

        # 2) Назначаем id и детектим language
        for it in items:
            it["id"] = self._generate_id(it["url"])
            it["language"] = self.translate_service.detect_language(it["content"])

        # 3) Фильтруем дубликаты по полю (title, url)
        unique = self.duplicate_filter.filter(items)
        if not unique:
            self.logger.debug("Новых уникальных новостей нет")
            return 0

        # 4) Сохраняем в raw_news
        count = self.raw_repo.insert_news(unique)
        self.logger.info(f"Сохранили в raw: {count} новостей")
        return count