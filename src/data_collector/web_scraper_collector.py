# src/data_collector/web_scraper/web_scraper_collector.py

import importlib
import asyncio
from typing import List, Dict, Any
from urllib.parse import urlparse

class WebScraperCollector:
    """
        Асинхронно запускает все скрейперы, указанные в source_map из конфигурации,
        и собирает результаты в единый список новостей.

        Каждый элемент source_map имеет ключ topic и список спецификаций:
          - module: путь к модулю скрейпера
          - class: имя класса скрейпера
          - url: URL для скрейпера

        В результате метод collect() вернёт List[Dict] с ключами:
          title, url, date, text, media_urls, topic
    """

    def __init__(self, source_map: Dict[str, List[Dict[str, Any]]], logger):
        self.logger = logger
        self.scrapers = []
        for topic, specs in source_map.items():
            for spec in specs:
                module = importlib.import_module(spec["module"])
                cls = getattr(module, spec["class"])
                inst = cls(spec["url"])
                setattr(inst, "topic", topic)
                self.scrapers.append(inst)

    async def collect(self) -> List[Dict[str, Any]]:
        all_news: List[Dict[str, Any]] = []
        tasks = [self._run_scraper(scraper) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                # Ошибка логируется в _run_scraper
                continue
            for item in res:
                # Гарантируем наличие всех нужных полей
                item.setdefault("title", "")
                item.setdefault("url", "")
                item.setdefault("date", "")
                item.setdefault("text", "")
                item.setdefault("media_urls", [])
                # Тема может быть в item или в атрибуте
                item["topic"] = getattr(item, "topic", None) or item.get("topic") or "general"
                all_news.append(item)
        return all_news

    async def _run_scraper(self, scraper) -> List[Dict[str, Any]]:
        try:
            return await scraper.run()
        except Exception as e:
            self.logger.error(f"Ошибка в {scraper.__class__.__name__}: {e}", exc_info=True)
            return []
