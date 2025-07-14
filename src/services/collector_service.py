# src/services/collector_service.py
from __future__ import annotations

import hashlib
from typing import List, Dict, Any

from pydantic import HttpUrl

from src.utils.file_utils import _parse_date
from src.data_manager.NewsItem import RawNewsItem


class CollectorService:
    """
    1. Запускает WebScraperCollector -> получает list[dict].
    2. Скачивает медиa, переводит язык, парсит дату.
    3. Валидирует всё в RawNewsItem.
    4. Отфильтровывает дубликаты и кладёт в raw_repo.
    """

    def __init__(
        self,
        *,
        raw_repo,
        collector,
        translate_service,
        media_service,
        duplicate_filter,
        logger,
        test_one_raw: bool = False,
        item_index: int = 2,
    ):
        self.raw_repo = raw_repo
        self.collector = collector
        self.translate = translate_service
        self.media = media_service
        self.dup = duplicate_filter
        self.log = logger
        self.test_one_raw = test_one_raw
        self.item_index = item_index

    # ───────────────────────── helpers ───────────────────────── #
    @staticmethod
    def _make_id(url: str) -> int:
        """MD5(url) → 16 hex → int -> UBIGINT для DuckDB."""
        return int(hashlib.md5(url.encode()).hexdigest()[:16], 16)

    # ───────────────────────── core ──────────────────────────── #
    async def collect_and_save(self) -> None:
        raw: List[Dict[str, Any]] = await self.collector.collect()
        if self.test_one_raw and raw:
            raw = [raw[self.item_index]]

        items: List[RawNewsItem] = []
        for r in raw:
            # ─── media ─── #
            media_ids: list[str] = []
            for murl in r.get("media_urls", []):
                fid = await self.media.download(murl)
                if fid:
                    media_ids.append(fid)

            raw_text = r.get("text", "")
            lang = self.translate.detect_language(raw_text)
            if lang == "en":
                raw_text = self.translate.translate(raw_text)
                lang = "ru"

            # ─── модель ─── #
            item = RawNewsItem(
                id=self._make_id(r["url"]),
                title=r["title"],
                url=HttpUrl(r["url"]),
                date=_parse_date(r.get("date")),
                text=raw_text,
                media_ids=media_ids,
                language=lang,
                topic=r.get("topic", "auto"),
            )
            items.append(item)

        unique = self.dup.filter(items)
        if unique:
            self.raw_repo.insert_news(unique)
            self.log.debug("Сохранили в raw: %d", len(unique))
