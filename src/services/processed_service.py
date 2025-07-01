# src/services/processed_service.py
import os
import logging
from openai import OpenAI
from typing import List, Dict, Any
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.services.translate_service import TranslateService
from dotenv import load_dotenv


def gpt_process_with_proxy(news_text: str) -> str:
    # Сохраняем старый прокси (если был)
    old_proxy = os.environ.get('HTTPS_PROXY')
    # Устанавливаем нужный прокси только на время работы этого метода
    os.environ['HTTPS_PROXY'] = "socks5://MUqDrt:WS4Yx5@181.177.89.20:9826"

    prompt = (
        "Перепиши этот текст для моего Telegram-канала про автомобили. "
        "Сделай его коротким, дерзким и интересным, как будто пишет живой автолюбитель — добавь немного сарказма и эмоций. "
        "Тон должен быть уверенным и разговорным, с лёгким юмором (и даже негодованием, если уместно), но без лишнего молодёжного сленга — текст должен понравиться и молодым, и тем, кто постарше. "
        "Включи важные детали по теме, будто пишешь с экспертным знанием. Если в исходном посте упоминается фото или видео, отрази это в тексте с подходящим комментарием. "
        "Ограничение: итоговый пост должен быть максимально компактным — не длиннее 2–3 коротких абзацев. "
    )

    try:
        client = OpenAI(
            api_key="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"
        )

        completion = client.chat.completions.create(
            model="gpt-4.1",
            store=True,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": news_text}
            ]
        )
        return completion.choices[0].message.content

    finally:
        # Восстанавливаем старое значение прокси, чтобы не сломать остальной код
        if old_proxy is not None:
            os.environ['HTTPS_PROXY'] = old_proxy
        else:
            os.environ.pop('HTTPS_PROXY', None)


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

            gpt_result = gpt_process_with_proxy(text)

            to_insert.append({
                'id': id_,
                'title': title,
                'url': url,
                'date': date,
                'content': gpt_result,
                'media_ids': media_ids,
                'topic': topic,
                'language': out_lang,
            })

        if not to_insert:
            self.logger.debug("Нет новостей для processed")
            return 0

        count = self.processed_repo.insert_processed_news(to_insert)
        self.logger.debug(f"Сохранили в processed: {count} новостей")
