# src/data_collector/web_scraper_collector.py
import asyncio

class WebScraperCollector:
    """
    Принимает source_map из конфига, валидирует каждую запись,
    создаёт экземпляры скра-перов и асинхронно запускает их.
    """

    def __init__(
        self,
        source_map,
        source_spec_model,
        scraper_registry,
        logger,
    ):
        self.log = logger
        self.scrapers = []

        for topic, raw_specs in source_map.items():
            for raw in raw_specs:
                try:
                    spec = source_spec_model.parse_obj(raw)
                except Exception as e:
                    self.log.error("Bad spec for topic %s: %s", topic, e)
                    continue

                cls = scraper_registry.get(spec.class_)
                if cls is None:
                    self.log.error("Scraper %s not found in registry", spec.class_)
                    continue

                scraper = cls(str(spec.url))
                scraper.topic = topic
                self.scrapers.append(scraper)

    async def _safe_run(self, scraper):
        try:
            return await scraper.run()
        except Exception as exc:
            self.log.exception("%s failed: %s", scraper.__class__.__name__, exc)
            return []

    async def collect(self):
        if not self.scrapers:
            return []

        results = await asyncio.gather(*(self._safe_run(s) for s in self.scrapers))
        merged = []

        for scraper, items in zip(self.scrapers, results, strict=True):
            for it in items:
                it.setdefault("topic", scraper.topic)
                merged.append(it)

        return merged