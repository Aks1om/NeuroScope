import requests
from bs4 import BeautifulSoup
from . import WebScraperBase

class WallpaperTransportScraper(WebScraperBase):
    def parse(self, html):
        """
        Парсит HTML главной страницы и возвращает список новостных элементов.
        Каждый элемент — словарь с ключами: title, url, date, text, images.
        """
        soup = BeautifulSoup(html, 'html.parser')
        news_items = soup.find_all('li', class_='listing__item')

        results = []
        for item in news_items:
            link = item.find('a', class_='listing__link')
            title_tag = item.find('h2', class_='listing__title')
            date_tag = item.find('time')

            title = title_tag.get_text(strip=True) if title_tag else None
            url = link.get('href') if link else None
            date = date_tag.get('datetime') if date_tag else None

            if not url or not title:
                continue

            # Делает URL абсолютным
            if url.startswith('/'):
                url = self.url.rstrip('/') + url

            detail = self._fetch_details(url)
            if detail:
                detail.update({
                    "title": title,
                    "url": url,
                    "date": date
                })
                results.append(detail)

        return results

    def _fetch_details(self, url):
        """
        Фетчит страницу новости и возвращает словарь с текстом и списком изображений.
        """
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Извлекаем основное тело статьи
            article_body = soup.select_one('#article-body')
            full_text = article_body.get_text(strip=True, separator="\n") if article_body else ""

            # Собираем все src картинок внутри тела статьи
            images = []
            if article_body:
                for img in article_body.select('img'):
                    src = img.get('src')
                    if src:
                        images.append(src)

            return {
                "text": full_text,
                "images": images
            }
        except Exception as e:
            print(f"[!] Ошибка при получении деталей {url}: {e}")
            return None

    def format_for_telegram(self, items):
        """
        Форматирует результаты парсинга в список сообщений для Telegram.
        """
        messages = []
        for item in items:
            parts = [
                f"[TELEGRAM] {item.get('title')}",
                f"URL: {item.get('url')}",
                f"Дата: {item.get('date')}",
                f"Текст: {item.get('text')}",
                "Картинки:"
            ]
            for img in item.get('images', []):
                parts.append(f" - {img}")
            messages.append("\n".join(parts))
        return messages
