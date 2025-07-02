# src/services/processed_service.py

import logging
from typing import List, Dict, Any
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.services.translate_service import TranslateService
from src.services.chat_gpt_service import ChatGPTService


class ProcessedService:
    """
    Читает raw из БД, переводит через TranslateService,
    обрабатывает через ChatGPTService и сохраняет в processed DB.
    """

    def __init__(
        self,
        raw_repo: DuckDBNewsRepository,
        processed_repo: DuckDBNewsRepository,
        translate_service: TranslateService,
        chat_gpt_service: ChatGPTService,
        logger: logging.Logger,
    ):
        self.raw_repo = raw_repo
        self.processed_repo = processed_repo
        self.translate = translate_service
        self.chat_gpt = chat_gpt_service
        self.logger = logger

    def process_and_save(self) -> int:
        done_ids = {
            row[0]
            for row in self.processed_repo.client.execute("SELECT id FROM news").fetchall()
        }

        rows = self.raw_repo.client.execute(
            "SELECT id, title, url, date, content, media_ids, topic, language FROM news"
        ).fetchall()

        to_insert: List[Dict[str, Any]] = []
        for id_, title, url, date, content, media_ids, topic, lang in rows:
            if id_ in done_ids:
                continue

            text = content
            out_lang = lang
            if lang == 'en':
                try:
                    text = self.translate.translate(content)
                    out_lang = 'ru'
                except Exception as e:
                    self.logger.error(f"Translation failed for {id_}: {e}")

            try:
                processed = self.chat_gpt.process(text)
            except Exception as e:
                self.logger.error(f"GPT processing failed for {id_}: {e}")
                continue

            to_insert.append({
                'id':         id_,
                'title':      title,
                'url':        url,
                'date':       date,
                'content':    processed,
                'media_ids':  media_ids,
                'topic':      topic,
                'language':   out_lang,
            })

        if not to_insert:
            self.logger.debug("No new items to process.")
            return 0

        count = self.processed_repo.insert_processed_news(to_insert)
        self.logger.info(f"Inserted {count} processed news items.")
        return count
