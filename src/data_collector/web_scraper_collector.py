# src/data_collector/web_scraper_collector.py
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Sequence

from pydantic import BaseModel, HttpUrl, ValidationError

from src.utils.app_config import SourceSpec
from .web_scrapers import SCRAPER_REGISTRY

logger = logging.getLogger(__name__)


class WebScraperCollector:
    """
    Принимает source_map из конфига, валидирует каждую запись,
    создаёт экземпляры скра-перов и асинхронно запускает их.
    """

    def __init__(
        self,
        source_map: Dict[str, Sequence[Dict[str, str]]],
        logger: logging.Logger | None = None,
    ):
        self.log = logger or logging.getLogger(__name__)
        self.scrapers: list[Any] = []

        for topic, raw_specs in source_map.items():
            for raw in raw_specs:
                try:
                    spec: SourceSpec = SourceSpec.parse_obj(raw)
                except ValidationError as e:
                    self.log.error("Bad spec for topic %s: %s", topic, e)
                    continue

                cls = SCRAPER_REGISTRY.get(spec.class_)
                if cls is None:
                    self.log.error("Scraper %s not found in registry", spec.class_)
                    continue

                scraper = cls(str(spec.url))        # type: ignore[call-arg]
                scraper.topic = topic               # передаём тему скра-перу
                self.scrapers.append(scraper)

    # ───────────────────── helpers ───────────────────── #
    async def _safe_run(self, scraper):
        try:
            return await scraper.run()
        except Exception as exc:                     # pylint: disable=broad-except
            self.log.exception("%s failed: %s", scraper.__class__.__name__, exc)
            return []

    # ───────────────────── API ───────────────────────── #
    async def collect(self) -> List[Dict[str, Any]]:
        """
        Возвращает общий список новостей
        (каждая строка дополняется полем 'topic', если скра-пер его не поставил).
        """
        if not self.scrapers:
            return []

        results = await asyncio.gather(*(self._safe_run(s) for s in self.scrapers))
        merged: list[dict] = []

        for scraper, items in zip(self.scrapers, results, strict=True):
            for it in items:
                it.setdefault("topic", scraper.topic)
                merged.append(it)

        return merged
