# src/di.py
from aiogram import Bot, Dispatcher
from src.utils.file_utils import load_env, load_config, get_env
from src.bot.logger import setup_logger
from src.bot.middleware import RoleMiddleware, LoggingMiddleware, CommandRestrictionMiddleware
from src.bot.handlers.general import router as general_router
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.data_collector.web_scraper_collector import WebScraperCollector
from src.services.collector_service import CollectorService
from src.services.translate_service import TranslateService
from src.services.processed_service import ProcessedService
from src.services.polling_service import PollingService
from src.utils.paths import RAW_DB, PROCESSED_DB

# 1) Load env & config
load_env()
config = load_config()

# 2) Bot & Logger
bot = Bot(token=get_env("TELEGRAM_TOKEN"), parse_mode="HTML")
logger = setup_logger(config, bot)

# 3) Dispatcher + Middlewares
dp = Dispatcher()
prog_ids = set(config["users"]["prog_ids"])
manager_ids = set(config["users"]["admin_ids"])
suggest_group_id = config["telegram_channels"]["moderators_chat_id"]

# Middleware order: Logging -> Role -> CommandRestriction
dp.update.middleware(LoggingMiddleware(logger))
dp.update.middleware(RoleMiddleware(prog_ids, manager_ids, suggest_group_id))
dp.update.middleware(CommandRestrictionMiddleware(prog_ids, suggest_group_id))

# Routers
dp.include_router(general_router)

# 4) Database Repositories
raw_client = DuckDBClient(RAW_DB)
processed_client = DuckDBClient(PROCESSED_DB)
raw_repo = DuckDBNewsRepository(raw_client)
processed_repo = DuckDBNewsRepository(processed_client)

# 5) Services
collector = CollectorService(
    raw_repo=raw_repo,
    collectors=[WebScraperCollector()],
    logger=logger
)
translator = TranslateService()
processor = ProcessedService(
    raw_repo=raw_repo,
    processed_repo=processed_repo,
    translate_service=translator,
    logger=logger
)
polling_service = PollingService(
    collector_service=collector,
    processed_service=processor,
    logger=logger,
    interval=config.get("poll_interval", 300),
    first_run=config.get("first_run", True)
)

__all__ = ["bot", "dp", "logger", "config", "polling_service"]