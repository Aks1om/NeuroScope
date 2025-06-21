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
    logger.info("Конфигурация и логгер инициализированы")

    # 2) Создание клиентов DuckDB (raw и processed)
    raw_client = DuckDBClient(RAW_DB)
    processed_client = DuckDBClient(PROCESSED_DB)
    logger.info("DuckDB клиенты для raw и processed готовы")

    # 3) Репозитории новостей
    raw_repo = DuckDBNewsRepository(raw_client)
    processed_repo = DuckDBNewsRepository(processed_client)
    logger.info("Репозитории raw и processed готовы")

    # 4) Сбор новостей в raw
    collector_service = CollectorService(
        raw_client=raw_client,
        collectors=[WebScraperCollector()],
        logger=logger,
    )
    new_raw = collector_service.collect_and_save()
    logger.info(f"Собрано новых записей в raw: {new_raw}")

    # 5) Обработка и перевод → сохранение в processed
    translate_service = TranslateService()
    processed_service = ProcessedService(
        raw_client=raw_client,
        processed_repo=processed_repo,
        translate_service=translate_service,
        logger=logger,
    )
    new_processed = processed_service.process_and_save()
    logger.info(f"Сохранено новых записей в processed: {new_processed}")


    #await asyncio.sleep(2)
    #await bot.session.close()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())