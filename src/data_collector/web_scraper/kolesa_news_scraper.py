import logging
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from . import WebScraperBase

class KolesaNewsScraper(WebScraperBase):
    """
    Асинхронный скрепер для сайта Kolesa.ru.
    Возвращает для каждой новости словарь с ключами:
      title, url, date, text, media_urls
    """
    BASE_HOST = "https://www.kolesa.ru"

    def __init__(self, url: str):
        super().__init__(url)
        self.logger = logging.getLogger("bot")

    async def run(self) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            # Скачиваем страницу списка
            async with session.get(self.base_url, timeout=10) as resp:
                resp.raise_for_status()
                html = await resp.text()
            # Парсим и скачиваем детали
            return await self.parse(html, session)

    async def parse(self, html: str, session: aiohttp.ClientSession) -> list[dict]:
        soup = BeautifulSoup(html, 'html.parser')
        tasks = []
        for link in soup.select('a.post-list-item'):
            href = link.get('href')
            if href and not href.startswith('http'):
                href = urljoin(self.BASE_HOST, href)

            title_tag = link.select_one('span.post-name')
            date_tag  = link.select_one('span.post-meta-item.pull-right')
            title = title_tag.get_text(strip=True) if title_tag else ''
            date  = date_tag.get_text(strip=True) if date_tag else ''

            if not title or not href:
                continue
            tasks.append(self._fetch_detail(title, href, date, session))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Оставляем только успешные словари
        return [r for r in results if isinstance(r, dict)]

    async def _fetch_detail(self, title: str, url: str, date: str, session: aiohttp.ClientSession) -> dict:
        try:
            async with session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                detail_html = await resp.text()
            detail_soup = BeautifulSoup(detail_html, 'html.parser')

            content_block = detail_soup.select_one('div.post-content')
            text = content_block.get_text(strip=True, separator='\n') if content_block else ''

            media_urls = []
            # Галерея
            for img in detail_soup.select('div.post-gallery img'):
                src = img.get('src')
                if src:
                    media_urls.append(src)
            # Главная картинка
            main_img = detail_soup.select_one('span.post-image')
            if main_img and main_img.has_attr('style'):
                style = main_img['style']
                if 'url(' in style:
                    img_url = style.split('url(')[1].split(')')[0].strip('"\'')
                    media_urls.insert(0, img_url)

            return {
                'title': title,
                'url': url,
                'date': date,
                'text': text,
                'media_urls': media_urls
            }
        except Exception as e:
            self.logger.error(f"Error parsing Kolesa article {url}: {e}", exc_info=True)
            return None
