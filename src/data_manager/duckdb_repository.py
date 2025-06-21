# src/data_manager/duckdb_repository.py
from .duckdb_client import DuckDBClient
from src.utils.config import load_config
from src.utils.paths import MEDIA_DIR
import uuid, os, re, requests
from urllib.parse import urlparse

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
                # список тем собираем в строку
                topics = src.get('topic') or []
                return ','.join(topics)
        return None

    def insert_news(self, items: list[dict]) -> None:
        """
        Вставить список новостей в таблицу, игнорируя уже существующие по ключу.
        """
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        existing_urls = set(r[0] for r in self.client.execute("SELECT url FROM news").fetchall())

        for item in items:
            url = item.get('url')
            if not url or url in existing_urls:
                continue

            news_id = item.get('id') or str(uuid.uuid4())
            url = item.get('url', '')
            title = item.get('title')
            date = item.get('date')
            content = item.get('text', '')

            topic = self.get_topic_for_url(url)
            language = self.detect_language(content)

            # Сохраняем медиа
            saved_ids = []
            for img_url in item.get('images', []):
                media_id = str(uuid.uuid4())
                ext = os.path.splitext(urlparse(img_url).path)[1] or ''
                file_name = f"{media_id}{ext}"
                file_path = MEDIA_DIR / file_name
                try:
                    resp = requests.get(img_url, timeout=10)
                    resp.raise_for_status()
                    with open(file_path, 'wb') as f:
                        f.write(resp.content)
                    saved_ids.append(media_id)
                except Exception:
                    continue

            media_ids_str = ','.join(saved_ids) if saved_ids else None

            # Вставка в БД
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
            except Exception:
                continue