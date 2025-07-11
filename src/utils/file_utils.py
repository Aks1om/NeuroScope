from src.utils.paths import*
import os
import json
from dotenv import load_dotenv
from types import SimpleNamespace
from src.utils.paths import BASE_DIR

def load_env():
    env_path = ENV_DIR
    load_dotenv(dotenv_path=env_path)

def load_config():
    config_path = CONFIG_DIR
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config

def get_env(key):
    value = os.environ.get(key)
    if value is None:
        raise RuntimeError(f"ENV: обязательная переменная {key} не найдена!")
    return value

def dict_to_namespace(d: dict) -> SimpleNamespace:
    """
    Рекурсивно превращает словарь в SimpleNamespace,
    **кроме** ключа 'source_map' – он остаётся dict,
    чтобы WebScraperCollector работал без костылей.
    """
    ns = SimpleNamespace()
    for k, v in d.items():
        if k == "source_map":
            setattr(ns, k, v)                   # ← оставляем dict
        elif isinstance(v, dict):
            setattr(ns, k, dict_to_namespace(v))
        else:
            setattr(ns, k, v)
    return ns