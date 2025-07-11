# src/services/media_service.py
import aiohttp
from pathlib import Path
from src.utils.paths import MEDIA_DIR
from hashlib import md5
from urllib.parse import urlparse

class MediaService:
    def __init__(self, logger):
        self.logger = logger

    async def download(self, url: str) -> str | None:
        """Скачивает файл по URL, кладёт в `media/`, возвращает локальное имя."""
        if not url:
            return None
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        media_id = md5(url.encode()).hexdigest()[:16]
        ext = Path(parsed.path).suffix
        filename = f"{media_id}{ext}"
        path = MEDIA_DIR / filename
        if path.exists():
            return filename
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    resp.raise_for_status()
                    path.write_bytes(await resp.read())
            return filename
        except Exception as e:
            self.logger.error(f"Не удалось скачать {url}: {e}")
            return None