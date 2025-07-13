# src/data_collector/web_scrapers/__init__.py
"""
Регистрируем скра-перы для Collector.  __init__ больше не содержит базовый класс.
"""

from typing import Dict, Type
from .base import WebScraperBase

SCRAPER_REGISTRY: Dict[str, Type[WebScraperBase]] = {}


def register(cls: Type[WebScraperBase]):
    """Декоратор @register для автоматической регистрации класса по имени."""
    SCRAPER_REGISTRY[cls.__name__] = cls
    return cls

import pkgutil
import importlib

for mod in pkgutil.walk_packages(__path__, prefix=__name__ + "."):
    # пропустим base и “скрытые” файлы
    if mod.name.endswith(".base") or mod.name.rsplit(".", 1)[-1].startswith("_"):
        continue
    importlib.import_module(mod.name)

# Чтобы старые импорты из (__init__ as WebScraperBase) не упали:
__all__ = ["WebScraperBase", "register", "SCRAPER_REGISTRY"]
