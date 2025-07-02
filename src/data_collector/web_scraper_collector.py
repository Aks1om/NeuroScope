# src/data_collector/web_scraper/web_scraper_collector.py

import importlib
from typing import List, Dict, Any

class WebScraperCollector:
    """
    Динамически создаёт список скраper-ов из config['source_map'].
    У каждого scraper’а выставляет атрибут .topic, и собирает их в .scrapers.
    """

    def __init__(self, source_map: Dict[str, List[Dict[str, Any]]]):
        self.scrapers = []
        for topic, specs in source_map.items():
            for spec in specs:
                module_name = spec["module"]
                class_name  = spec["class"]
                url         = spec["url"]

                try:
                    module = importlib.import_module(module_name)
                    scraper_cls = getattr(module, class_name)
                except (ImportError, AttributeError) as e:
                    raise ImportError(
                        f"Невозможно загрузить {class_name} из {module_name}: {e}"
                    )

                # Инстанцируем скраper и навешиваем тему
                scraper = scraper_cls(url)
                setattr(scraper, "topic", topic)
                self.scrapers.append(scraper)

    def collect(self) -> List[Dict[str, Any]]:
        """
        Запускает .run() всех скраper-ов, добавляя field 'topic' в каждый item.
        """
        all_news = []
        for scraper in self.scrapers:
            try:
                items = scraper.run()
                for it in items:
                    # если в item ещё нет topic, берем тот, что навесили
                    it.setdefault("topic", getattr(scraper, "topic"))
                all_news.extend(items)
            except Exception as e:
                # логгер здесь не подключён — прокиньте при необходимости
                print(f"[!] Ошибка в {scraper.__class__.__name__}: {e}")
        return all_news
