# src/di.py
# ────────────── 0. stdlib / сторонние ────────────── #
import os
import shutil
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ────────────── 1. util-слой ────────────── #
from src.utils.file_utils import *
from src.utils.paths import *
from src.utils.formatters import *
from src.bot.logger import setup_logger
from src.bot.filter import ProgOrAdminFilter
from src.bot.middleware import (
    LoggingMiddleware,
    RoleMiddleware,
    CommandRestrictionMiddleware,
)
from src.bot.handlers.general import router as general_router
from src.bot.handlers.post import build_post_admin_router

# ────────────── 2. модели / БД ────────────── #
from src.data_manager.models import RawNewsItem, ProcessedNewsItem
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBRepository

# ────────────── 3. сервис-слой ────────────── #
from src.services.duplicate_filter_service import DuplicateFilterService
from src.services.media_service import MediaService
from src.services.translate_service import TranslateService
from src.services.chat_gpt_service import ChatGPTService
from src.services.collector_service import CollectorService
from src.services.processed_service import ProcessedService
from src.services.sending_service import SendingService
from src.services.polling_service import PollingService

from src.data_collector.web_scraper_collector import WebScraperCollector

# ────────────── 4. конфиг + окружение ────────────── #
load_env()                                   # .env → os.environ
cfg = load_app_config("config.json")

# ────────────── 5. подготовка файловой среды ────────────── #
if cfg.settings.reset:
    Path(DB).unlink(missing_ok=True)
    if MEDIA_DIR.exists():
        shutil.rmtree(MEDIA_DIR)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# ────────────── 6. бот, логгер, диспетчер ────────────── #
bot = Bot(
    token=os.environ["TELEGRAM_TOKEN"],
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
logger = setup_logger(cfg, bot)

dp = Dispatcher()
dp.update.middleware(LoggingMiddleware(logger))
dp.update.middleware(
    RoleMiddleware(
        cfg.users.prog_ids,
        cfg.users.admin_ids,
        cfg.telegram_channels.suggested_chat_id,
    )
)
dp.update.middleware(
    CommandRestrictionMiddleware(
        cfg.users.prog_ids,
        cfg.telegram_channels.suggested_chat_id,
    )
)
dp.include_router(general_router)

# ────────────── 7. БД и репозитории ────────────── #
db_client      = DuckDBClient(DB)
raw_repo       = DuckDBRepository(db_client.conn, "raw_news",       RawNewsItem)
processed_repo = DuckDBRepository(db_client.conn, "processed_news", ProcessedNewsItem)

# ────────────── 8. сервисы ────────────── #
prog_admin_filter = ProgOrAdminFilter(
    set(cfg.users.prog_ids), set(cfg.users.admin_ids)
)
dp.include_router(build_post_admin_router(processed_repo, prog_admin_filter, cfg))

translate_svc = TranslateService()
dup_raw       = DuplicateFilterService(raw_repo)
dup_proc      = DuplicateFilterService(processed_repo)

web_collector = WebScraperCollector(cfg.source_map, logger)

dup_raw  = DuplicateFilterService(
    repo=raw_repo,
    dub_threshold=cfg.settings.dub_threshold,
    dub_hours_threshold=cfg.settings.dub_hours_threshold,
)

dup_proc = DuplicateFilterService(
    repo=processed_repo,
    dub_threshold=cfg.settings.dub_threshold,
    dub_hours_threshold=cfg.settings.dub_hours_threshold,
)

media_service = MediaService(
    logger=logger,
    media_dir=MEDIA_DIR,
)

collector_service = CollectorService(
    raw_repo=raw_repo,
    collector=web_collector,
    translate_service=translate_svc,
    media_service=media_service,
    duplicate_filter=dup_raw,
    logger=logger,
    model=RawNewsItem,
    parse_date=parse_date,
    test_one_raw=cfg.settings.test_one_raw,
)

chatgpt_service = ChatGPTService(
    api_key  = os.environ.get("OPENAI_API_KEY"),
    proxy_url= os.environ.get("PROXY"),
)

processed_service = ProcessedService(
    raw_repo          = raw_repo,
    processed_repo    = processed_repo,
    translate_service = translate_svc,
    chat_gpt_service  = chatgpt_service,
    duplicate_filter  = dup_proc,
    logger            = logger,
    use_chatgpt       = cfg.settings.use_chatgpt,
)

sending_service = SendingService(
    bot=bot,
    chat_id=cfg.telegram_channels.suggested_chat_id,
    processed_repo=processed_repo,
    logger=logger,
    build_caption=build_caption,
    build_meta=build_meta,
    media_dir=MEDIA_DIR,
)

polling_service = PollingService(
    collector_service = collector_service,
    processed_service = processed_service,
    sending_service   = sending_service,
    bot               = bot,
    suggest_group_id  = cfg.telegram_channels.suggested_chat_id,
    interval          = cfg.settings.poll_interval,
    first_run         = cfg.settings.first_run,
    logger            = logger,
)

# ────────────── 9. экспорт ────────────── #
__all__ = ["bot", "dp", "polling_service", "cfg", "logger"]
