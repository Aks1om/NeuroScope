# src/di.py
from aiogram import Bot, Dispatcher
from src.utils.file_utils import load_env, load_config, get_env
from src.bot.logger import setup_logger
from src.bot.middleware import (
    RoleMiddleware,
    LoggingMiddleware,
    CommandRestrictionMiddleware,
)
from src.bot.handlers import general

# 1) Load environment and config
load_env()
config = load_config()

# 2) Bot instance
bot = Bot(token=get_env("TELEGRAM_TOKEN"))

# 3) Logger
logger = setup_logger(config, bot)

# 4) Dispatcher + middlewares
dp = Dispatcher()
prog_ids = set(config["users"]["prog_ids"])
manager_ids = set(config["users"]["admin_ids"])
suggest_group_id = config["telegram_channels"]["moderators_chat_id"]

# Order: Logging -> Role assignment -> Command restriction
dp.update.middleware(LoggingMiddleware(logger))
dp.update.middleware(RoleMiddleware(prog_ids, manager_ids, suggest_group_id))
dp.update.middleware(CommandRestrictionMiddleware(prog_ids, suggest_group_id))

# 5) Include routers
dp.include_router(general.router)

__all__ = ["bot", "dp", "logger", "config"]