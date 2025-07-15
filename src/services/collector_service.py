# src/services/collector_service.py
import hashlib

class CollectorService:
    """
    1. Запускает WebScraperCollector -> получает list[dict].
    2. Скачивает медиa, переводит язык, парсит дату.
    3. Валидирует всё в RawNewsItem.
    4. Отфильтровывает дубликаты и кладёт в raw_repo.
    """

    def __init__(
        self,
        *,
        raw_repo,
        collector,
        translate_service,
        media_service,
        duplicate_filter,
        logger,
        model,  # <--- Pydantic-модель RawNewsItem через DI
        parse_date,  # <--- функция парсинга даты через DI
        test_one_raw=False,
        item_index=2,
    ):
        self.raw_repo = raw_repo
        self.collector = collector
        self.translate_service = translate_service
        self.media_service = media_service
        self.duplicate_filter = duplicate_filter
        self.logger = logger
        self.model = model
        self.parse_date = parse_date
        self.test_one_raw = test_one_raw
        self.item_index = item_index

    @staticmethod
    def _make_id(url):
        """MD5(url) → 16 hex → int -> UBIGINT для DuckDB."""
        return int(hashlib.md5(url.encode()).hexdigest()[:16], 16)

    async def collect_and_save(self):
        raw = await self.collector.collect()
        if self.test_one_raw and raw:
            raw = [raw[self.item_index]]

        items = []
        for r in raw:
            # --- media ---
            media_ids = []
            for murl in r.get("media_urls", []):
                fid = await self.media_service.download(murl)
                if fid:
                    media_ids.append(fid)

            raw_text = r.get("text", "")
            lang = self.translate_service.detect_language(raw_text)
            if lang == "en":
                raw_text = self.translate_service.translate(raw_text)
                lang = "ru"

            # --- модель ---
            item = self.model(
                id=self._make_id(r["url"]),
                title=r["title"],
                url=r["url"],
                date=self.parse_date(r.get("date")),
                text=raw_text,
                media_ids=media_ids,
                language=lang,
                topic=r.get("topic", "auto"),
            )
            items.append(item)

        unique = self.duplicate_filter.filter(items)
        if unique:
            self.raw_repo.insert_news(unique)
            self.logger.debug("Сохранили в raw: %d", len(unique))
