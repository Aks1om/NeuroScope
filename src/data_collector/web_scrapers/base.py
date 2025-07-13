# src/data_collector/web_scrapers/base.py
"""
Единый абстрактный класс для всех скра-перов.
Не трогаем Collector – он просто будет импортировать наследников.
"""

from __future__ import annotations

import aiohttp
import requests
from abc import ABC, abstractmethod


class WebScraperBase(ABC):
    """
    Каждый наследник обязан переопределить parse().
    Метод run() скачивает страницу списка и вызывает parse().
    parse() может запрашивать доп-страницы через тот же session.
    Возвращаемый формат: List[dict] с ключами
      title, url, date, text, media_urls
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    # ───────────────────────────────────────── helpers

    def fetch_sync(self, url: str | None = None) -> str:
        """Синхронная скачка – пригодится в parse(), если session не нужен."""
        url = url or self.base_url
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        return resp.text

    # ───────────────────────────────────────── contract

    @abstractmethod
    async def parse(
        self, html: str, session: aiohttp.ClientSession | None = None
    ) -> list[dict]:
        """Парсинг html‐списка; session может быть None, если не нужен."""
        ...

    # ───────────────────────────────────────── entrypoint

    async def run(self) -> list[dict]:
        """Общий pipeline: GET списка -> parse()."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, timeout=10) as resp:
                resp.raise_for_status()
                html = await resp.text()
            return await self.parse(html, session)
