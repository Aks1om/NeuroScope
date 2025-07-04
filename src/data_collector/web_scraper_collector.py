# src/data_collector/web_scraper/web_scraper_collector.py

import importlib
from typing import List, Dict, Any
from urllib.parse import urlparse

class WebScraperCollector:
    """
    Динамически создаёт список скраper-ов из config['source_map'].
    У каждого scraper’а выставляет атрибут .topic, и собирает их в .scrapers.
    """

    def __init__(self, source_map: Dict[str, List[Dict[str, Any]]]):
        self.scrapers = []
        for topic, specs in source_map.items():
            for spec in specs:
                module = importlib.import_module(spec["module"])
                cls = getattr(module, spec["class"])
                inst = cls(spec["url"])
                setattr(inst, "topic", topic)
                self.scrapers.append(inst)

    def collect(self) -> List[Dict[str, Any]]:
        all_news: List[Dict[str, Any]] = []
        for scraper in self.scrapers:
            try:
                raw = scraper.run()
                for item in raw:
                    item.setdefault("title", "")
                    item.setdefault("url", "")
                    item.setdefault("date", "")
                    item.setdefault("text", "")
                    item.setdefault("media_urls", [])

                    item["topic"] = getattr(scraper, "topic", "general")
                all_news.extend(raw)
            except Exception as e:
                print(f"[!] Ошибка в {scraper.__class__.__name__}: {e}")
        return all_news
