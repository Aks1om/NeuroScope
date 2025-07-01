# src/services/processed_service.py
import logging
from typing import List, Dict, Any
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.services.translate_service import TranslateService
from dotenv import load_dotenv

class ProcessedService:
    """
    Читает из raw, переводит английские тексты и сохраняет в processed.
    """

    def __init__(
        self,
        raw_repo: DuckDBNewsRepository,
        processed_repo: DuckDBNewsRepository,
        translate_service: TranslateService,
        logger: logging.Logger,
    ):
        self.raw_repo = raw_repo
        self.processed_repo = processed_repo
        self.translate_service = translate_service
        self.logger = logger

    def process_and_save(self) -> int:
        # уже готовые id
        done = {r[0] for r in self.processed_repo.client.execute(
            "SELECT id FROM news"
        ).fetchall()}

        # сырые записи
        rows = self.raw_repo.client.execute(
            "SELECT id,title,url,date,content,media_ids,topic,language FROM news"
        ).fetchall()

        to_insert: List[Dict[str, Any]] = []
        for id_, title, url, date, content, media_ids, topic, lang in rows:
            if id_ in done:
                continue
            text = content
            out_lang = lang
            # Только английские новости переводим, остальные сохраняем как есть
            if lang == 'en':
                try:
                    text = self.translate_service.translate(content)
                    out_lang = 'ru'
                except Exception as e:
                    self.logger.error(f"Перевод {id_} упал: {e}")

            #GPT_processor

            to_insert.append({
                'id': id_,
                'title': title,
                'url': url,
                'date': date,
                'content': text,
                'media_ids': media_ids,
                'topic': topic,
                'language': out_lang,
            })

        if not to_insert:
            self.logger.debug("Нет новостей для processed")
            return 0

        count = self.processed_repo.insert_processed_news(to_insert)
        self.logger.debug(f"Сохранили в processed: {count} новостей")
