# src/di.py

import logging
import importlib
from aiogram import Bot, Dispatcher

from src.utils.file_utils import load_env, load_config, get_env
from src.bot.logger import setup_logger
from src.bot.middleware import LoggingMiddleware, RoleMiddleware, CommandRestrictionMiddleware
from src.bot.handlers.general import router as general_router

from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.utils.paths import DB

from src.data_collector.web_scraper_collector import WebScraperCollector

from src.services.collector_service import CollectorService
from src.services.translate_service import TranslateService
from src.services.chat_gpt_service import ChatGPTService
from src.services.processed_service import ProcessedService
from src.services.polling_service import PollingService

# 1) Load environment and config
load_env()
config = load_config()

# 2) Bot + Logger
bot = Bot(token=get_env("TELEGRAM_TOKEN"), parse_mode="HTML")
logger = setup_logger(config, bot)

# 3) Dispatcher + Middlewares
dp = Dispatcher()
prog_ids         = set(config["users"].get("prog_ids", []))
admin_ids        = set(config["users"].get("admin_ids", []))
suggested_chat   = config["telegram_channels"]["suggested_chat_id"]

dp.update.middleware(LoggingMiddleware(logger))
dp.update.middleware(RoleMiddleware(prog_ids, admin_ids, suggested_chat))
dp.update.middleware(CommandRestrictionMiddleware(prog_ids, suggested_chat))

dp.include_router(general_router)

# 4) DuckDB (единственный файл с двумя таблицами)
db_client      = DuckDBClient(DB)
raw_repo       = DuckDBNewsRepository(db_client, table_name="raw_news")
processed_repo = DuckDBNewsRepository(db_client, table_name="processed_news")

# 5) Web-scraper collector: динамически из конфига
source_map = config.get("source_map", {})
web_scraper_collector = WebScraperCollector(source_map)

# 6) Services
collector_service = CollectorService(
    raw_repo    = raw_repo,
    collectors  = web_scraper_collector.scrapers,
    topics_map  = {},          # не нужен, topic уже в item
    logger      = logger
)

translate_service = TranslateService()

chat_gpt_service = ChatGPTService(
    api_key   = get_env("OPENAI_API_KEY"),
    proxy_url = config.get("gpt_proxy_url")
)

processed_service = ProcessedService(
    raw_repo          = raw_repo,
    processed_repo    = processed_repo,
    translate_service = translate_service,
    chat_gpt_service  = chat_gpt_service,
    logger            = logger
)

polling_service = PollingService(
    collector_service  = collector_service,
    processed_service  = processed_service,
    logger             = logger,
    interval           = config.get("poll_interval", 300),
    first_run          = config.get("first_run", True)
)

__all__ = ["bot", "dp", "logger", "config", "polling_service"]
