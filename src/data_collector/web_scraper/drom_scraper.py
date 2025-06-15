import requests
from bs4 import BeautifulSoup
from . import WebScraperBase

class DromNewsScraper(WebScraperBase):
    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        news_items = soup.select("div.b-wrapper div.b-content div.b-left-side div.b-media-query.b-random-group div.b-info-block")

        results = []
        for item in news_items:
            a_tag = item.find("a", class_="b-info-block__cont")
            title_tag = item.find("div", class_="b-info-block__title")
            date_tag = item.find("div", class_="b-info-block__text_type_news-date")

            title = title_tag.get_text(strip=True) if title_tag else None
            url = a_tag.get("href") if a_tag else None
            date = date_tag.get_text(strip=True) if date_tag else None

            if url and not url.startswith("http"):
                url = "https://news.drom.ru" + url

            if not title or not url:
                continue

            try:
                full_html = requests.get(url, timeout=10).text
                full_soup = BeautifulSoup(full_html, 'html.parser')

                # Парсим тело новости
                content_block = full_soup.select_one("#news_text")
                full_text = content_block.get_text(strip=True, separator="\n") if content_block else ""

                # Парсим все изображения
                images = []
                for img_tag in full_soup.select("div.news_img > a"):
                    img_url = img_tag.get("href")
                    if img_url:
                        images.append(img_url)

                results.append({
                    "title": title,
                    "url": url,
                    "date": date,
                    "text": full_text,
                    "images": images
                })
            except Exception as e:
                print(f"[!] Не удалось получить подробности для {url}: {e}")

        return results
