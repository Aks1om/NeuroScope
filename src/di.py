# src/di.py
import os, shutil
import logging
import importlib
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.utils.file_utils import load_env, load_config, get_env
from src.bot.logger import setup_logger
from src.bot.middleware import LoggingMiddleware, RoleMiddleware, CommandRestrictionMiddleware
from src.bot.handlers.general import router as general_router

from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.utils.paths import *

from src.data_collector.web_scraper_collector import WebScraperCollector

from src.services.collector_service import CollectorService
from src.services.translate_service import TranslateService
from src.services.chat_gpt_service import ChatGPTService
from src.services.processed_service import ProcessedService
from src.services.sending_service import SendingService
from src.services.polling_service import PollingService

# 1) Загрузка конфига и окружения
load_env()
config = load_config()

# 1.5) Если в настройках reset=true, очищаем media и удаляем БД
if config.get("settings", {}).get("reset", True):
    # Удаляем папку media целиком
    if os.path.isdir(MEDIA_DIR):
        shutil.rmtree(MEDIA_DIR)
    # Снова создаём её пустой
    os.makedirs(MEDIA_DIR, exist_ok=True)

    # Удаляем файл БД
    if os.path.isfile(DB):
        os.remove(DB)

# 2) Бот и логгер
bot = Bot(token=get_env("TELEGRAM_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
logger = setup_logger(config, bot)

# 3) Dispatcher + middleware
dp = Dispatcher()
prog_ids    = set(config["users"]["prog_ids"])
admin_ids   = set(config["users"]["admin_ids"])
suggested_chat_id  = int(config["telegram_channels"]["suggested_chat_id"])

async def on_startup(dispatcher: Dispatcher, bot: Bot):
    logger.info("Запуск NeuroScope")
dp.startup.register(on_startup)

dp.update.middleware(LoggingMiddleware(logger))
dp.update.middleware(RoleMiddleware(prog_ids, admin_ids, suggested_chat_id))
dp.update.middleware(CommandRestrictionMiddleware(prog_ids, suggested_chat_id))
dp.include_router(general_router)

# 4) Базы и репозитории
db_client      = DuckDBClient(DB)
raw_repo       = DuckDBNewsRepository(db_client, table_name="raw_news")
processed_repo = DuckDBNewsRepository(db_client, table_name="processed_news")

# 5) Сервисы
web_collector = WebScraperCollector(config["source_map"], logger)
translate_svc = TranslateService()
collector_svc = CollectorService(
    raw_repo=raw_repo,
    collector=web_collector,
    translate_service=translate_svc,
    logger=logger
)

# 6) Перевод + GPT
chatgpt_svc   = ChatGPTService(
    api_key=get_env("OPENAI_API_KEY"),
    proxy_url=get_env("PROXY")
)
processor_svc = ProcessedService(
    raw_repo=raw_repo,
    processed_repo=processed_repo,
    translate_service=translate_svc,
    chat_gpt_service=chatgpt_svc,
    logger=logger
)

# 7) Отправка в Telegram и пометка suggested
sending_svc = SendingService(
    bot=bot,
    chat_id=suggested_chat_id,
    processed_repo=processed_repo,
    logger=logger
)

# 8) Оркестратор polling’а
polling_service = PollingService(
    collector_service=collector_svc,
    processed_service=processor_svc,
    sending_service=sending_svc,
    bot=bot,
    suggest_group_id=suggested_chat_id,
    interval=config.get("poll_interval", 300),
    first_run=config.get("first_run", False),
    logger=logger
)


__all__ = ["bot", "dp", "logger", "config", "polling_service"]
