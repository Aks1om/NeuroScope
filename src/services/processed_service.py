# src/services/processed_service.py
import logging
from typing import List, Dict, Any
from src.services.duplicate_filter_service import DuplicateFilterService

class ProcessedService:
    """
    1) Загружает сырые новости из raw_news,
    2) переводит англоязычные через TranslateService,
    3) обрабатывает текст через ChatGPTService,
    4) сохраняет в processed_news.
    """

    def __init__(self, raw_repo, processed_repo, translate_service, chat_gpt_service, logger):
        self.raw_repo = raw_repo
        self.duplicate_filter = DuplicateFilterService(processed_repo)
        self.processed_repo = processed_repo
        self.translate = translate_service
        self.chat_gpt = chat_gpt_service
        self.logger = logger

    def process_and_save(self, first_run):
        # 1) Какие ID уже в processed?
        done_ids = self.processed_repo.fetch_ids()
        # 2) Все сырые записи
        rows = self.raw_repo.fetch_all()

        to_insert: List[Dict[str, Any]] = []
        for (
            news_id, title, url, date,
            text, media_ids, topic, lang
        ) in rows:
            if news_id in done_ids:
                continue

            out_lang = lang

            # 3) Переводим только английские новости
            if lang == 'en':
                try:
                    text = self.translate.translate(text)
                    out_lang = 'ru'
                except Exception as e:
                    self.logger.error(f"Translation failed for {news_id}: {e}")

            # 4) Обработка через ChatGPT
            if not first_run:
                try:
                    processed_text = self.chat_gpt.process(text)
                except Exception as e:
                    self.logger.error(f"GPT processing failed for {news_id}: {e}")
                    continue
            else:
                processed_text = text

            news_item = {
                'id': news_id,
                'title': title,
                'url': url,
                'date': date,
                'text': processed_text,
                'media_ids': media_ids,
                'language': out_lang,
                'topic': topic,
            }
            to_insert.append(news_item)
            self.logger.debug("Prepared for insert: %s", news_item)

        if not to_insert:
            self.logger.debug("No new items to process.")
            return 0

        # 5) Сохраняем все новые обработанные записи
        count = self.processed_repo.insert_news(to_insert)
        self.logger.debug(f"Переделано {count} новостей")
        return count
