# src/services/collector_service.py
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Iterable

from src.services.duplicate_filter_service import DuplicateFilterService


class CollectorService:
    """
    Собирает новости у collectors и сохраняет их в raw-базу.
    Скачивание медиа вынесено в MediaService.
    """

    def __init__(
        self,
        raw_repo,
        collector,
        translate_service,
        media_service,
        duplicate_filter,
        logger: logging.Logger,
        *,
        test_one_raw: bool = False,
        item_index: int = 0,
    ):
        self.raw_repo = raw_repo
        self.collector = collector
        self.translate_service = translate_service
        self.media_service = media_service
        self.duplicate_filter = duplicate_filter
        self.logger = logger
        self.test_one_raw = test_one_raw
        self.item_index = item_index
        self.duplicate_filter = DuplicateFilterService(raw_repo)

    # ───────────────────────────────────────── helpers ── #
    @staticmethod
    def _generate_id(url: str) -> int:
        return int(hashlib.md5(url.encode()).hexdigest()[:16], 16)

    @staticmethod
    def _fix_date(date_str: str) -> str | None:
        if not date_str:
            return None
        try:
            d = datetime.strptime(date_str, "%d.%m.%Y")
            return d.strftime("%Y-%m-%d")
        except Exception:
            return date_str

    # ───────────────────────────────────────── main ──── #
    async def collect_and_save(self):
        # 1) Собираем
        items: list[Dict[str, Any]] = await self.collector.collect()

        # 1.1) Тестовый режим: берём один элемент
        if self.test_one_raw and items:
            idx = max(0, min(self.item_index, len(items) - 1))
            items = [items[idx]]
            self.logger.info("Тестовый режим: взята запись #%d", idx)

        # 2) Обрабатываем каждую новость
        for item in items:
            # 2.1) Скачиваем медиа
            media_urls: Iterable[str] = item.get("media_urls", [])
            media_ids: list[str] = []
            for url in media_urls:
                file_id = await self.media_service.download(url)
                if file_id:
                    media_ids.append(file_id)

            # 2.2) Дополнительные поля под базу
            item["id"] = self._generate_id(item["url"])
            item["date"] = self._fix_date(item.get("date", ""))
            item["media_ids"] = media_ids
            item["language"] = self.translate_service.detect_language(item["text"])

        # 3) Фильтруем дубликаты
        unique = self.duplicate_filter.filter(items)
        if not unique:
            self.logger.debug("Новых уникальных новостей нет")

        # 4) Сохраняем
        count = self.raw_repo.insert_news(unique)
        self.logger.debug("Сохранили в raw: %d новостей", count)
