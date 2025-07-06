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
    ns = SimpleNamespace()
    for key, val in d.items():
        if isinstance(val, dict):
            setattr(ns, key, dict_to_namespace(val))
        else:
            setattr(ns, key, val)
    return ns