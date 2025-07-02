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
from src.services.chat_gpt_service import ChatGPTService
from src.services.processed_service import ProcessedService
from src.services.polling_service import PollingService
from src.utils.paths import RAW_DB, PROCESSED_DB

# 1) Загрузка конфига и окружения
load_env()
config = load_config()  # ← config.json содержит telegram_channels.moderators_chat_id :contentReference[oaicite:5]{index=5}

# 2) Бот и логгер
bot = Bot(token=get_env("TELEGRAM_TOKEN"), parse_mode="HTML")
logger = setup_logger(config, bot)

# 3) Dispatcher + middleware
dp = Dispatcher()
prog_ids    = set(config["users"]["prog_ids"])
admin_ids   = set(config["users"]["admin_ids"])
suggest_id  = config["telegram_channels"]["moderators_chat_id"]

dp.update.middleware(LoggingMiddleware(logger))
dp.update.middleware(RoleMiddleware(prog_ids, admin_ids, suggest_id))
dp.update.middleware(CommandRestrictionMiddleware(prog_ids, suggest_id))
dp.include_router(general_router)

# 4) Базы и репозитории
db_client        = DuckDBClient(RAW_DB)               # одна БД с двумя таблицами :contentReference[oaicite:6]{index=6}
raw_repo         = DuckDBNewsRepository(db_client, table_name="raw_news")
processed_repo   = DuckDBNewsRepository(db_client, table_name="processed_news")

# 5) Сервисы
web_collector    = WebScraperCollector(config.get("source_map", {}))
collector_svc    = CollectorService(raw_repo=raw_repo, collectors=web_collector.scrapers, logger=logger)
translator_svc   = TranslateService()
chatgpt_svc      = ChatGPTService(api_key=get_env("OPENAI_API_KEY"), proxy_url=get_env("PROXY"))
processor_svc    = ProcessedService(
    raw_repo=raw_repo,
    processed_repo=processed_repo,
    translate_service=translator_svc,
    chat_gpt_service=chatgpt_svc,
    logger=logger
)

# 6) Polling
polling_service = PollingService(
    collector_service=collector_svc,
    processed_service=processor_svc,
    bot=bot,
    suggest_group_id=suggest_id,
    interval=config.get("poll_interval", 300),
    first_run=config.get("first_run", True),
)

__all__ = ["bot", "dp", "logger", "config", "polling_service"]
