import requests
from bs4 import BeautifulSoup
from . import WebScraperBase

class AutonewsNewsScraper(WebScraperBase):
    """
    Скрепер для сайта Autonews.ru.
    Извлекает заголовок, URL, дату, полный текст и изображения каждой новости.
    """
    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # Селектор для блоков новостей, аналогично DromNewsScraper
        blocks = soup.select("div.item-big__inner")

        results = []
        for block in blocks:
            a_tag = block.find("a", class_="item-big__link")
            title_tag = block.find("span", class_="item-big__title")
            date_tag = block.find("span", class_="item-big__date")

            title = title_tag.get_text(strip=True) if title_tag else None
            url = a_tag.get("href") if a_tag else None
            date = date_tag.get_text(strip=True) if date_tag else None

            if url and url.startswith("/"):
                url = "https://www.autonews.ru" + url

            if not title or not url:
                continue

            try:
                full_html = requests.get(url, timeout=10).text
                full_soup = BeautifulSoup(full_html, 'html.parser')

                # Основной текст
                content_block = full_soup.select_one("div.article__text[itemprop='articleBody']")
                content = (
                    content_block.get_text(strip=True, separator="\n")
                    if content_block else ""
                )

                # Ссылки на изображения
                media = []
                if content_block:
                    for img_tag in content_block.select("img"):
                        img_url = img_tag.get("src")
                        if img_url:
                            media.append(img_url)

                results.append({
                    "title": title,
                    "url": url,
                    "date": date,
                    "content": content,
                    "media_ids": media
                })
            except Exception as e:
                print(f"[!] Не удалось получить подробности для {url}: {e}")

        return results
