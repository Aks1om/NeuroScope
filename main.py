# main.py
import sys
import asyncio

from src.utils.config import load_config
from src.logger.logger import setup_logger
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.data_collector.web_scraper_collector import WebScraperCollector
from src.services.translate_service import TranslateService
from src.services.collector_service import CollectorService
from src.services.processed_service import ProcessedService

async def main():
    # 1) Загрузка конфига и логгера (возвращает и Bot для корректного закрытия)
    cfg = load_config('config.yml')
    logger, bot = setup_logger(cfg, __name__)

    # 2) Инициализация БД: raw и processed
    db_clients = DuckDBClient.create_database()
    raw_client = db_clients['raw']
    processed_client = db_clients['processed']
    raw_repo = DuckDBNewsRepository(raw_client.db_path)
    processed_repo = DuckDBNewsRepository(processed_client.db_path)
    logger.info("БД готовы")

    collector_service = CollectorService(
        collectors=[WebScraperCollector(raw_client)],
        logger=logger,  # ← прокидываем сюда
    )
    new_count = collector_service.collect_and_save()

    translate_service = TranslateService()
    processed_service = ProcessedService(
        raw_client=raw_client,
        processed_repo=processed_repo,
        translate_service=translate_service,
        logger=logger,
    )
    processed_count = processed_service.process_and_save()


    #await asyncio.sleep(2)
        #await bot.session.close()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())