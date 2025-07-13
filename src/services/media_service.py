import aiohttp, uuid, mimetypes
from hashlib import md5
from pathlib import Path
from urllib.parse import urlparse
from src.utils.paths import MEDIA_DIR

class MediaService:
    def __init__(self, logger):
        self.logger = logger

    async def download(self, url: str | None) -> str | None:
        # a) ручное добавление
        if not url:
            return f"{uuid.uuid4().hex[:16]}.bin"

        # b) скачивание по URL
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return None

        ext = Path(p.path).suffix or ".bin"          # дефолт
        filename = f"{md5(url.encode()).hexdigest()[:16]}{ext}"
        path = MEDIA_DIR / filename
        if path.exists():
            return filename

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=20) as resp:
                    resp.raise_for_status()
                    # уточняем расширение по Content-Type, если нужно
                    if ext == ".bin":
                        mime = resp.headers.get("content-type", "")
                        ext2 = mimetypes.guess_extension(mime) or ".bin"
                        filename = filename[:-4] + ext2
                        path = MEDIA_DIR / filename
                    path.write_bytes(await resp.read())
            return filename
        except Exception as e:
            self.logger.error("Не скачалось %s: %s", url, e)
            return None
