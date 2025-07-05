# src/data_collector/web_scraper/drom_scraper.py
import logging
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from . import WebScraperBase

class DromNewsScraper(WebScraperBase):
    def __init__(self, url: str):
        super().__init__(url)
        self.logger = logging.getLogger("bot")

    async def run(self) -> list[dict]:
        """
        Загружает страницу списка новостей и сразу же парсит детали в рамках одной сессии.
        """
        async with aiohttp.ClientSession() as session:
            # 1) Скачиваем HTML списка
            async with session.get(self.base_url, timeout=10) as resp:
                resp.raise_for_status()
                html = await resp.text()
            # 2) Парсим и загружаем детали, используя ту же сессию
            return await self.parse(html, session)

    async def parse(self, html: str, session: aiohttp.ClientSession) -> list[dict]:
        soup = BeautifulSoup(html, 'html.parser')
        blocks = soup.select(
            "div.b-wrapper div.b-content div.b-left-side "
            "div.b-media-query.b-random-group div.b-info-block"
        )
        tasks = []
        for block in blocks:
            a_tag = block.find("a", class_="b-info-block__cont")
            title_tag = block.find("div", class_="b-info-block__title")
            date_tag = block.find("div", class_="b-info-block__text_type_news-date")

            title = title_tag.get_text(strip=True) if title_tag else None
            url = a_tag.get("href") if a_tag else None
            date = date_tag.get_text(strip=True) if date_tag else None

            if url and not url.startswith("http"):
                url = urljoin(self.base_url, url)
            if not title or not url:
                continue

            tasks.append(self._fetch_detail(title, url, date, session))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        items = []
        for r in results:
            if isinstance(r, Exception):
                # Ошибка уже залогирована в _fetch_detail
                continue
            if r:
                items.append(r)
        return items

    async def _fetch_detail(self, title: str, url: str, date: str, session: aiohttp.ClientSession) -> dict | None:
        try:
            async with session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                detail_html = await resp.text()

            detail_soup = BeautifulSoup(detail_html, 'html.parser')
            text_block = detail_soup.select_one("#news_text")
            text = text_block.get_text(strip=True, separator="\n") if text_block else ""
            media_urls = [img.get("href") for img in detail_soup.select("div.news_img > a") if img.get("href")]

            return {
                "title": title,
                "url": url,
                "date": date,
                "text": text,
                "media_urls": media_urls
            }
        except Exception as e:
            self.logger.error(f"Error parsing Drom article {url}: {e}", exc_info=True)
            return None
