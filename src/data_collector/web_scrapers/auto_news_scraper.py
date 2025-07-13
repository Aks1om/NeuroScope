import logging
from . import WebScraperBase
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
from datetime import datetime
import re

# Mapping Russian month names to numbers
MONTHS = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
}

# Default headers to avoid 406 errors
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

class AutonewsNewsScraper(WebScraperBase):
    def __init__(self, url: str):
        super().__init__(url)
        self.logger = logging.getLogger("bot")

    def run(self) -> list[dict]:
        # Fetch list page with proper headers
        resp = requests.get(self.base_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return self.parse(resp.text)

    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        for block in soup.select('div.item-big__inner'):
            # Extract link and title
            link_tag = block.select_one('a.item-big__link')
            href = link_tag.get('href', '') if link_tag else ''
            url = urljoin(self.base_url, href)

            title_tag = block.select_one('span.item-big__title')
            title = title_tag.get_text(strip=True) if title_tag else ''

            # Extract and parse date
            date_tag = block.select_one('span.item-big__date')
            raw_date = date_tag.get_text(strip=True) if date_tag else ''
            date_str = self._parse_date(raw_date)

            try:
                resp = requests.get(url, headers={**HEADERS, 'Referer': self.base_url}, timeout=10)
                resp.raise_for_status()
                detail = BeautifulSoup(resp.text, 'html.parser')

                # Main text
                content_div = detail.select_one("div.article__text[itemprop='articleBody']")
                text = content_div.get_text(strip=True, separator='\n') if content_div else ''

                # Media URLs
                media_urls = []
                if content_div:
                    for img in content_div.find_all('img'):
                        src = img.get('src')
                        if src:
                            media_urls.append(urljoin(self.base_url, src))

                items.append({
                    "title": title,
                    "url": url,
                    "date": date_str,
                    "text": text,
                    "media_urls": media_urls
                })

            except requests.HTTPError as e:
                self.logger.error(f"Error parsing Autonews article {url}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error in Autonews scraper for {url}: {e}", exc_info=True)

        return items

    def _parse_date(self, raw_date: str) -> str:
        # Normalize and remove punctuation
        parts = raw_date.replace(',', '').split()
        if len(parts) < 2:
            return raw_date
        try:
            day = int(parts[0])
            month_str = re.sub(r"[^а-яА-ЯёЁ]", "", parts[1].lower())
            month = MONTHS.get(month_str)
            year = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else datetime.now().year
            if not month:
                raise ValueError
            dt = datetime(year, month, day)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")  # fallback to today
