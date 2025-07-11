# src/services/processed_service.py
from typing import List, Dict, Any
from src.services.duplicate_filter_service import DuplicateFilterService

class ProcessedService:
    """
    1) Загружает сырые новости из raw_news,
    2) переводит англоязычные через TranslateService,
    3) обрабатывает текст через ChatGPTService,
    4) сохраняет в processed_news.
    """

    def __init__(
        self,
        raw_repo,
        processed_repo,
        translate_service,
        chat_gpt_service,
        duplicate_filter,
        logger,
        use_chatgpt
    ):
        self.raw_repo = raw_repo
        self.duplicate_filter = DuplicateFilterService(processed_repo)
        self.processed_repo = processed_repo
        self.translate = translate_service
        self.chat_gpt = chat_gpt_service
        self.duplicate_filter = duplicate_filter
        self.logger = logger
        self.use_chatgpt = use_chatgpt

    # ------------------------------------------------------------------ #
    def process_and_save(self, first_run: bool) -> int:
        done_ids = self.processed_repo.fetch_ids()
        rows = self.raw_repo.fetch_all()

        batch: List[Dict[str, Any]] = []
        for news_id, title, url, date, text, media_ids, lang, topic in rows:
            if news_id in done_ids:
                continue

            out_lang = lang
            if lang == "en":
                try:
                    text = self.translate.translate(text)
                    out_lang = "ru"
                except Exception as e:
                    self.logger.error("Translation failed for %s: %s", news_id, e)

            if first_run or not self.use_chatgpt:
                processed_text = text
            else:
                try:
                    processed_text = self.chat_gpt.process(text)
                except Exception as e:
                    self.logger.error("GPT failed for %s: %s", news_id, e)
                    continue

            batch.append(
                {
                    "id": news_id,
                    "title": title,
                    "url": url,
                    "date": date,
                    "text": processed_text,
                    "media_ids": media_ids,
                    "language": out_lang,
                    "topic": topic,
                }
            )

        if not batch:
            self.logger.debug("No new items to process.")
            return 0

        # --- фильтрация дубликатов по title/url ---
        unique = self.duplicate_filter.filter(batch)

        if not unique:
            self.logger.debug("Все элементы — дубликаты.")
            return 0

        count = self.processed_repo.insert_news(unique)
        self.logger.debug("Сохранили в processed: %d", count)
        return count
