# src/utils/config.py
import yaml
from pathlib import Path

def load_yaml_config(path="config.yml"):
    with open(path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

CONFIG = load_yaml_config()
