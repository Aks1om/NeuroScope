import logging
from typing import List, Dict, Any

from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.services.translate_service import TranslateService

class ProcessedService:
    """
    Сервис для чтения новостей из raw-базы,
    перевода, если нужно, и сохранения в processed-базу.
    """

    def __init__(
        self,
        raw_client: DuckDBClient,
        processed_repo: DuckDBNewsRepository,
        translate_service: TranslateService,
        logger: logging.Logger,
    ):
        self.raw_client = raw_client
        self.processed_repo = processed_repo
        self.translate_service = translate_service
        self.logger = logger

    def process_and_save(self) -> int:
        # Получаем уже обработанные id
        processed_ids = {
            row[0]
            for row in self.processed_repo.client.execute(
                "SELECT id FROM news"
            ).fetchall()
        }
        # Читаем все из raw
        raw_rows = self.raw_client.execute(
            """
            SELECT id, title, url, date, content, media_ids, topic, language
            FROM news
            """
        ).fetchall()

        to_insert: List[Dict[str, Any]] = []
        for id_, title, url, date, content, media_ids, topic, language in raw_rows:
            if id_ in processed_ids:
                continue

            text = content
            if language == 'en':
                try:
                    text = self.translate_service.translate(content)
                except Exception as e:
                    self.logger.error(f"Ошибка перевода для {id_}: {e}")
                    # оставляем оригинал

            to_insert.append({
                'id': id_,
                'title': title,
                'url': url,
                'date': date,
                'content': text,
                'media_ids': media_ids,
                'topic': topic,
                'language': language,
            })

        if not to_insert:
            self.logger.info("Нечего обрабатывать в processed")
            return 0

        # Сохраняем в processed
        self.processed_repo.insert_news([
            {
                'id': item['id'],
                'title': item['title'],
                'url': item['url'],
                'date': item['date'],
                'content': item['content'],
                'images': item['media_ids'] and item['media_ids'].split(',') or [],
            }
            for item in to_insert
        ])
        count = len(to_insert)
        self.logger.info(f"Обработано и сохранено в processed: {count}")
        return count
