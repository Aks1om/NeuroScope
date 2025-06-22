# main.py
import sys
import asyncio

from src.utils.config import load_config
from src.logger.logger import setup_logger
from src.utils.paths import RAW_DB, PROCESSED_DB
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.data_collector.web_scraper_collector import WebScraperCollector
from src.services.collector_service import CollectorService
from src.services.translate_service import TranslateService
from src.services.processed_service import ProcessedService

async def main():
    # 1) Загрузка конфига и логгера
    cfg = load_config('config.yml')
    logger, bot = setup_logger(cfg, __name__)
    logger.debug("Конфигурация и логгер инициализированы")

    # 2) Клиенты DuckDB и репозитории
    raw_client = DuckDBClient(RAW_DB)
    processed_client = DuckDBClient(PROCESSED_DB)
    raw_repo = DuckDBNewsRepository(raw_client)
    processed_repo = DuckDBNewsRepository(processed_client)
    logger.debug("Подключены raw и processed базы")

    # 3) Сбор в raw
    collector = CollectorService(
        raw_repo=raw_repo,
        collectors=[WebScraperCollector()],
        logger=logger,
    )
    collector.collect_and_save()

    # 4) Обработка и перевод → processed
    translator = TranslateService()
    processor = ProcessedService(
        raw_repo=raw_repo,
        processed_repo=processed_repo,
        translate_service=translator,
        logger=logger,
    )
    processor.process_and_save()

    #await asyncio.sleep(2)
    #await bot.session.close()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())