import requests
from bs4 import BeautifulSoup
from . import WebScraperBase

class AutonewsNewsScraper(WebScraperBase):
    """
    Скрепер для сайта Autonews.ru.
    Извлекает заголовок, URL, дату, полный текст и изображения каждой новости.
    """
    BASE_URL = "https://www.autonews.ru/news/"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # Селектор контейнеров новостей
        news_items = soup.select("div.item-big__inner")

        results = []
        for item in news_items:
            # Селекторы элементов
            a_tag = item.select_one("a.item-big__link")
            title_tag = item.select_one("span.item-big__title")
            date_tag = item.select_one("span.item-big__date")

            title = title_tag.get_text(strip=True) if title_tag else None
            url = a_tag.get("href") if a_tag else None
            date = date_tag.get_text(strip=True) if date_tag else None

            # Преобразование относительных URL
            if url and url.startswith("/"):
                url = "https://www.autonews.ru" + url

            if not title or not url:
                continue

            try:
                # Получаем детальную страницу новости
                full_html = requests.get(url, timeout=10).text
                full_soup = BeautifulSoup(full_html, 'html.parser')

                # Парсим тело новости
                content_block = full_soup.select_one("div.article__text[itemprop='articleBody']")
                full_text = content_block.get_text(strip=True, separator="\n") if content_block else ""

                # Собираем все изображения внутри текста
                images = []
                if content_block:
                    for img_tag in content_block.select("img"):
                        img_url = img_tag.get("src")
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
