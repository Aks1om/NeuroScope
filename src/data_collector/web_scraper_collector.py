from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Sequence

from .web_scrapers import SCRAPER_REGISTRY

logger = logging.getLogger(__name__)


class WebScraperCollector:
    """Запускает все скра-перы и возвращает объединённый список новостей."""

    def __init__(
        self,
        source_map: Dict[str, Sequence[Dict[str, str]]],
        logger: logging.Logger | None = None,
    ) -> None:
        if not isinstance(source_map, dict):
            raise TypeError(
                "source_map must be dict[str, list[dict]] "
                f"(got {type(source_map).__name__})"
            )

        self.logger = logger or logging.getLogger(__name__)
        self.scrapers: list[Any] = []

        for topic, specs in source_map.items():
            for spec in specs:
                if not isinstance(spec, dict):
                    raise TypeError(
                        f"each spec inside source_map[{topic!r}] "
                        f"must be dict (got {type(spec).__name__})"
                    )

                cls_name, url = spec.get("class"), spec.get("url")
                if not cls_name or not url:
                    self.logger.error("Bad spec for %s: %s", topic, spec)
                    continue

                cls = SCRAPER_REGISTRY.get(cls_name)
                if cls is None:
                    self.logger.error("Scraper %s not in registry", cls_name)
                    continue

                inst = cls(url)                # type: ignore[call-arg]
                inst.topic = topic
                self.scrapers.append(inst)

    # --------------------------- helpers --------------------------- #
    async def _safe_run(self, scraper):
        try:
            return await scraper.run()
        except Exception as exc:               # pylint: disable=broad-except
            self.logger.exception("%s failed: %s", scraper.__class__.__name__, exc)
            return []

    # ---------------------------- API ------------------------------ #
    async def collect(self) -> List[Dict[str, Any]]:
        if not self.scrapers:
            return []

        results = await asyncio.gather(*(self._safe_run(s) for s in self.scrapers))

        merged: list[dict] = []
        for scraper, items in zip(self.scrapers, results, strict=True):
            for item in items:
                item.setdefault("topic", scraper.topic)
                merged.append(item)
        return merged
