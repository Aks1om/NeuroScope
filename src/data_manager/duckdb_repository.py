import uuid
import os
import re
import requests
from urllib.parse import urlparse

from .duckdb_client import DuckDBClient
from src.utils.config import load_config
from src.utils.paths import MEDIA_DIR

class DuckDBNewsRepository:
    """
    Репозиторий для сохранения и обновления новостей в DuckDB.
    """
    def __init__(self, db_source):
        """
        db_source может быть либо путём (str/Path), либо DuckDBClient.
        """
        if isinstance(db_source, DuckDBClient):
            self.client = db_source
        else:
            self.client = DuckDBClient(db_source)
        cfg = load_config('config.yml')
        self.news_sources = getattr(cfg, 'news_sources', [])

    def detect_language(self, text: str) -> str:
        # Простая детекция по наличию кириллицы
        return 'ru' if re.search('[А-Яа-я]', text) else 'en'

    def get_topic_for_url(self, url: str) -> str | None:
        # Сопоставляем url новости с базовым url из конфигурации
        try:
            target_domain = urlparse(url).netloc
        except Exception:
            return None
        for src in self.news_sources:
            base = src.get('url')
            if not base:
                continue
            try:
                src_domain = urlparse(base).netloc
            except Exception:
                continue
            if target_domain.endswith(src_domain):
                topics = src.get('topic') or []
                return ','.join(topics)
        return None

    def insert_news(self, items: list[dict]) -> int:
        """
        Вставить список новостей в таблицу, игнорируя уже существующие по URL
        и не дублируя медиа.
        """
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

        # Собираем уже сохранённые URL, чтобы пропускать дубли
        existing_urls = {
            row[0] for row in self.client.execute("SELECT url FROM news").fetchall()
        }

        inserted = 0
        for item in items:
            url = item.get('url')
            if not url or url in existing_urls:
                continue
            # отмечаем, чтобы не обрабатывать повторно в этом запуске
            existing_urls.add(url)

            news_id = item.get('id') or str(uuid.uuid4())
            title = item.get('title')
            date = item.get('date')
            content = item.get('text', '')
            topic = self.get_topic_for_url(url)
            language = self.detect_language(content)

            # Сохраняем медиа с детерминированными именами, чтобы не дублировать
            saved_ids = []
            for img_url in item.get('images', []):
                media_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, img_url))
                ext = os.path.splitext(urlparse(img_url).path)[1] or ''
                file_name = f"{media_uuid}{ext}"
                file_path = MEDIA_DIR / file_name
                try:
                    if file_path.exists():
                        saved_ids.append(media_uuid)
                        continue
                    resp = requests.get(img_url, timeout=10)
                    resp.raise_for_status()
                    with open(file_path, 'wb') as f:
                        f.write(resp.content)
                    saved_ids.append(media_uuid)
                except Exception:
                    continue

            media_ids_str = ','.join(saved_ids) if saved_ids else None

            # Вставка записи с media_ids
            try:
                self.client.execute(
                    """
                    INSERT INTO news
                    (id, title, url, date, content, media_ids, topic, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        news_id, title, url, date,
                        content, media_ids_str, topic, language
                    ]
                )
                inserted += 1
            except Exception:
                # дубли URL или любая другая ошибка — пропускаем
                continue
        return inserted