# src/services/processed_service.py
from __future__ import annotations

import logging
from typing import List

from src.data_manager.NewsItem import RawNewsItem, ProcessedNewsItem
from src.services.duplicate_filter_service import DuplicateFilterService
from src.utils.file_utils import _parse_date


class ProcessedService:
    """
    1. Берёт всё из raw_repo.
    2. Переводит EN→RU (TranslateService).
    3. При необходимости обрабатывает GPT.
    4. Сохраняет уникальные записи в processed_repo.
    """

    def __init__(
        self,
        *,
        raw_repo,
        processed_repo,
        translate_service,
        chat_gpt_service,
        duplicate_filter: DuplicateFilterService[ProcessedNewsItem],
        logger: logging.Logger,
        use_chatgpt: bool,
    ):
        self.raw_repo = raw_repo
        self.proc_repo = processed_repo
        self.translate = translate_service
        self.chat_gpt = chat_gpt_service
        self.dup_filter = duplicate_filter
        self.logger = logger
        self.use_chatgpt = use_chatgpt

    # ───────────────────────── helpers ───────────────────────── #
    def _already_done_ids(self) -> set[int]:
        rows = self.proc_repo.conn.execute(f"SELECT id FROM {self.proc_repo.table}")
        return {r[0] for r in rows.fetchall()}

    # ───────────────────────── core ──────────────────────────── #
    def process_and_save(self, first_run: bool) -> int:
        done_ids = self._already_done_ids()
        raw_items: List[RawNewsItem] = self.raw_repo.fetch_all()

        batch: List[ProcessedNewsItem] = []

        for item in raw_items:
            if item.id in done_ids:
                continue

            text = item.text
            lang = item.language

            # 1) Перевод, если нужно
            if lang == "en":
                try:
                    text = self.translate.translate(text)
                    lang = "ru"
                except Exception as e:
                    self.logger.error("Translation failed for %s: %s", item.id, e)

            # 2) GPT-обработка
            if not first_run and self.use_chatgpt:
                try:
                    text = self.chat_gpt.process(text)
                except Exception as e:
                    self.logger.error("GPT failed for %s: %s", item.id, e)
                    continue  # пропускаем, если GPT упал

            processed = ProcessedNewsItem(
                id=item.id,
                title=item.title,
                url=item.url,
                date=_parse_date(item.date),
                text=text,
                media_ids=item.media_ids,
                language=lang,
                topic=item.topic,
            )
            batch.append(processed)

        if not batch:
            self.logger.debug("Нет новых элементов для обработки.")
            return 0

        unique = self.dup_filter.filter(batch)
        if not unique:
            self.logger.debug("Все элементы оказались дубликатами.")
            return 0

        saved = self.proc_repo.insert_news(unique)
        self.logger.debug("Сохранили в processed: %d", saved)
        return saved
