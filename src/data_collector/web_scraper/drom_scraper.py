# src/data_collector/web_scraper/drom_scraper.py

from bs4 import BeautifulSoup
from . import WebScraperBase
import requests

class DromNewsScraper(WebScraperBase):
    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        blocks = soup.select(
            "div.b-wrapper div.b-content div.b-left-side "
            "div.b-media-query.b-random-group div.b-info-block"
        )

        results = []
        for block in blocks:
            a_tag = block.find("a", class_="b-info-block__cont")
            title_tag = block.find("div", class_="b-info-block__title")
            date_tag = block.find("div", class_="b-info-block__text_type_news-date")

            title = title_tag.get_text(strip=True) if title_tag else None
            url = a_tag.get("href") if a_tag else None
            date = date_tag.get_text(strip=True) if date_tag else None

            if url and not url.startswith("http"):
                url = f"https://news.drom.ru{url}"

            if not title or not url:
                continue

            try:
                detail_html = requests.get(url, timeout=10).text
                detail_soup = BeautifulSoup(detail_html, 'html.parser')

                # Основной текст
                text_block = detail_soup.select_one("#news_text")
                text = (
                    text_block.get_text(strip=True, separator="\n")
                    if text_block else ""
                )

                # Ссылки на изображения
                media_urls = []
                for img_a in detail_soup.select("div.news_img > a"):
                    href = img_a.get("href")
                    if href:
                        media_urls.append(href)

                results.append({
                    "title": title,
                    "url": url,
                    "date": date,
                    "text": text,
                    "media_urls": media_urls
                })
            except Exception as e:
                # Лучше логировать через ваш logger, здесь для примера print
                print(f"[!] Ошибка при детальном парсинге {url}: {e}")

        return results