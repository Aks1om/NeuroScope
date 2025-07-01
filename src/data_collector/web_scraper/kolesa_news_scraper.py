import requests
from bs4 import BeautifulSoup
from . import WebScraperBase

class KolesaNewsScraper(WebScraperBase):
    """
    Скрепер для сайта Kolesa.ru.
    Извлекает заголовок, URL, дату, краткое описание, полный текст и изображения каждой новости.
    """
    BASE_URL = "https://www.kolesa.ru/news"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # Селектор карточек новостей
        news_items = soup.select("a.post-list-item")

        results = []
        for item in news_items:
            url = item.get("href")
            title_tag = item.select_one("span.post-name")
            date_tag = item.select_one("span.post-meta-item.pull-right")
            lead_tag = item.select_one("span.post-lead")
            category_tag = item.select_one("span.post-category")
            image_tag = item.select_one("span.post-image")

            title = title_tag.get_text(strip=True) if title_tag else None
            date = date_tag.get_text(strip=True) if date_tag else None
            lead = lead_tag.get_text(strip=True) if lead_tag else ""
            category = category_tag.get_text(strip=True) if category_tag else ""

            # Извлечение URL картинки из стиля background-image
            image = None
            if image_tag and image_tag.has_attr("style"):
                style = image_tag["style"]
                # Ожидаем формат: background-image: url(...)
                try:
                    image = style.split("url(")[1].split(")")[0].strip('"')
                except Exception:
                    image = None

            if not title or not url:
                continue

            # Если нужно, преобразуйте относительные ссылки
            if url.startswith("/"):
                url = "https://www.kolesa.ru" + url

            try:
                # Получаем детальную страницу
                full_html = requests.get(url, timeout=10).text
                detail_soup = BeautifulSoup(full_html, 'html.parser')

                # Парсим тело новости
                content_block = detail_soup.select_one("div.post-content")
                full_text = content_block.get_text(strip=True, separator="\n") if content_block else ""

                # Собираем все изображения внутри галереи
                images = []
                for img in detail_soup.select("div.post-gallery img"):  # Фотографии в галерее
                    img_url = img.get("src")
                    if img_url:
                        images.append(img_url)
                # Добавляем главную картинку, если есть
                if image:
                    images.insert(0, image)

                results.append({
                    "title": title,
                    "url": url,
                    "date": date,
                    "category": category,
                    "lead": lead,
                    "text": full_text,
                    "images": images
                })
            except Exception as e:
                print(f"[!] Ошибка при получении деталей {url}: {e}")

        return results