# src/data_manager/duckdb_repository.py
import uuid
import os
import re
import requests
from urllib.parse import urlparse
from datetime import datetime

from .duckdb_client import DuckDBClient
from src.utils.file_utils import load_config
from src.utils.paths import MEDIA_DIR
from typing import List, Dict, Any
from .duckdb_client import DuckDBClient


class DuckDBNewsRepository:
    def __init__(self, client: DuckDBClient, table_name: str):
        self.conn = client.conn
        self.table = table_name

    def insert_news(self, items: List[Dict[str, Any]]) -> int:
        """
        Вставить пачку новостей в self.table.
        Ожидаемый формат items: список словарей с ключами
        id, title, url, date, content, media_ids, language, topic
        """
        sql = f"""
        INSERT INTO {self.table} 
          (id, title, url, date, content, media_ids, language, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO NOTHING
        """
        data = [
            (
                item["id"], item["title"], item["url"], item["date"],
                item["content"], item["media_ids"],
                item["language"], item["topic"]
            )
            for item in items
        ]
        cur = self.conn.execute(sql, data)
        return cur.rowcount

    def fetch_all(self) -> List[tuple]:
        """Вернуть все строки из self.table."""
        return self.conn.execute(f"SELECT * FROM {self.table}").fetchall()

    def fetch_ids(self) -> set[int]:
        """Вернуть множество всех id из self.table."""
        rows = self.conn.execute(f"SELECT id FROM {self.table}").fetchall()
        return {r[0] for r in rows}