import aiohttp, uuid, mimetypes
from hashlib import md5
from pathlib import Path
from urllib.parse import urlparse

class MediaService:
    def __init__(self, logger, media_dir):
        self.logger = logger
        self.media_dir = media_dir  # теперь путь всегда приходит из DI!

    async def download(self, url):
        # a) ручное добавление
        if not url:
            return f"{uuid.uuid4().hex[:16]}.bin"

        # b) скачивание по URL
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return None

        ext = Path(p.path).suffix or ".bin"
        filename = f"{md5(url.encode()).hexdigest()[:16]}{ext}"
        path = self.media_dir / filename
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
                        path = self.media_dir / filename
                    path.write_bytes(await resp.read())
            return filename
        except Exception as e:
            self.logger.error("Не скачалось %s: %s", url, e)
            return None
