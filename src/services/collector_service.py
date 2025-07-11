# src/services/collector_service.py
import logging
import hashlib
import asyncio
from typing import Iterable, Dict, Any
from src.services.duplicate_filter_service import DuplicateFilterService
from src.utils.paths import MEDIA_DIR
import os
import requests
from datetime import datetime

class CollectorService:
    """
    Собирает новости у collectors и сохраняет их в raw-базу.
    Все дубликаты по title/url отбиваются в DuplicateFilterService.
    """

    def __init__(
            self,
            raw_repo,
            collector,
            translate_service,
            logger,
            *,
            test_one_raw: bool = False,  # ← логика выбора одной записи
            item_index: int = 0,
    ):
        self.raw_repo = raw_repo
        self.collector = collector
        self.translate_service = translate_service
        self.logger = logger
        self.test_one_raw = test_one_raw
        self.item_index = item_index
        self.duplicate_filter = DuplicateFilterService(raw_repo)

    def _generate_id(self, url: str) -> int:
        h = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
        return int(h, 16)

    async def download_image(self, url: str) -> str | None:
        if not url:
            self.logger.debug("Не удалось скачать: пустой URL")
            return None
        # Выносим синхронную часть в отдельный поток
        return await asyncio.to_thread(self._download_image_sync, url)

    def _download_image_sync(self, url: str) -> str | None:
        # — если это шаблон вида {{ post.preview_url }}, пропускаем
        if '{{' in url and '}}' in url:
            self.logger.debug(f"Пропущен шаблонный URL: {url}")
            return None
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            self.logger.debug(f"Пропущен некорректный URL: {url}")
            return None
        media_id = self._generate_id(url)
        base = os.path.basename(url.split("?")[0])
        ext = os.path.splitext(base)[1]
        filename = f"{media_id}{ext}"
        filepath = MEDIA_DIR / filename

        if not filepath.exists():
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(r.content)
                #self.logger.debug(f"Успешно скачан медиа-файл: {filename}")
            except Exception as e:
                # Логируем реальный URL и текст ошибки
                self.logger.error(f"Не удалось скачать {url}: {e}", exc_info=True)
                return None

        return filename

    def fix_date(self, date_str: str) -> str | None:
        if not date_str:
            return None
        try:
            d = datetime.strptime(date_str, "%d.%m.%Y")
            return d.strftime("%Y-%m-%d")
        except Exception:
            return date_str

    async def collect_and_save(self):
        # 1) Собираем
        items = await self.collector.collect()

        # 1.1) Если нужен ровно один элемент
        if self.test_one_raw and items:
            idx = max(0, min(self.item_index, len(items) - 1))
            items = [items[idx]]
            self.logger.info("Тестовый режим: взята запись #%d", idx)

        # 2) Назначаем
        for item in items:
            media_urls = item.get("media_urls", [])
            media_ids = []
            for url in media_urls:
                file_id = await self.download_image(url)
                if file_id:
                    media_ids.append(str(file_id))

            item["id"] = self._generate_id(item["url"])
            item["date"] = self.fix_date(item.get("date", ""))
            item["media_ids"] = media_ids
            item["language"] = self.translate_service.detect_language(item["text"])

        # 3) Фильтруем дубликаты по полю (title, url)
        unique = self.duplicate_filter.filter(items)
        if not unique:
            self.logger.debug("Новых уникальных новостей нет")

        # 4) Сохраняем в raw_news
        count = self.raw_repo.insert_news(unique)
        self.logger.debug(f"Сохранили в raw: {count} новостей")