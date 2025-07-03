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

    def mark_suggested(self, ids: List[int]) -> None:
        """
        Пометить в self.table все записи с указанными id как suggested = TRUE.
        """
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        sql = f"""
        UPDATE {self.table}
        SET suggested = TRUE
        WHERE id IN ({placeholders})
        """
        self.conn.execute(sql, ids)

    def mark_all_suggested(self) -> None:
        """
        Пометить все записи в таблице как suggested = TRUE.
        """
        sql = f"UPDATE {self.table} SET suggested = TRUE"
        self.conn.execute(sql)

    def fetch_unsuggested(self, limit: int) -> List[Dict[str, Any]]:
        """
        Возвращает до `limit` записей из processed_news,
        у которых suggested = FALSE, с полями:
        id, title, url, content, media_ids
        """
        sql = f"""
        SELECT id, title, url, content, media_ids
        FROM {self.table}
        WHERE suggested = FALSE
        ORDER BY date ASC
        LIMIT ?
        """
        rows = self.conn.execute(sql, [limit]).fetchall()
        return [
            {
                "id": r[0],
                "title": r[1],
                "url": r[2],
                "content": r[3],
                "media_ids": r[4] or []
            }
            for r in rows
        ]