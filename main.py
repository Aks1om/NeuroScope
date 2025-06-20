# main.py
import sys
import asyncio

from src.utils.config import load_config
from src.logger.logger import setup_logger
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.data_collector.web_scraper_collector import WebScraperCollector


async def main():
    # 1) Загрузка конфига и логгера (возвращает и Bot для корректного закрытия)
    cfg = load_config('config.yml')
    logger, bot = setup_logger(cfg, __name__)

    # 2) Инициализация БД: raw и processed
    db_clients = DuckDBClient.create_database()
    raw_db_client = db_clients['raw']
    processed_db_client = db_clients['processed']
    logger.info(f"✅ БД инициализированы: raw={raw_db_client.db_path}, processed={processed_db_client.db_path}")

    # 3) Репозиторий для сохранения новостей в processed-БД
    repo = DuckDBNewsRepository(processed_db_client.db_path)

    # 4) Коллекторы данных
    collectors = [
        WebScraperCollector(raw_db_client),
    ]

    logger.info("🚀 Запуск цикла сбора данных")

    # 5) Сбор
    items = []
    for collector in collectors:
        try:
            collected = collector.collect()
            logger.debug(f"{collector.__class__.__name__} собрал {len(collected)} элементов")
            items.extend(collected)
        except Exception as e:
            logger.error(f"Ошибка при сборе ({collector.__class__.__name__}): {e}")

    # 6) Сохранение собранных новостей
    if items:
        try:
            repo.insert_news(items)
            logger.info(f"✅ Сохранено новостей: {len(items)}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении новостей: {e}")
    else:
        logger.info("ℹ️ Нет новых новостей для сохранения")

    # 6) Дадим время на отправку логов в Telegram, затем корректно закроем сессию
    #await asyncio.sleep(2)
    #await bot.session.close()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())