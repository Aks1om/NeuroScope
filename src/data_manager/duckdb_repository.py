# src/data_manager/duckdb_repository.py
import uuid
import os
import re
import json
import requests
from urllib.parse import urlparse
from datetime import datetime
from types import SimpleNamespace

from src.utils.file_utils import load_config
from src.utils.paths import MEDIA_DIR
from typing import List, Dict, Any


class DuckDBNewsRepository:
    def __init__(self, client, table_name):
        self.conn = client.conn
        self.table = table_name

    def insert_news(self, items: List[Dict[str, Any]]) -> int:
        sql = f"""
        INSERT INTO {self.table}
          (id, title, url, date, text, media_ids, language, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO NOTHING
        """
        data = []
        for item in items:
            date = item.get("date")
            text_value = item.get("text", "")
            # гарантируем, что media_ids — список строк
            mids = item.get("media_ids") or []
            mids_str = [str(mid) for mid in mids]

            data.append((
                item["id"],
                item["title"],
                item["url"],
                date,
                text_value,
                mids_str,
                item["language"],
                item["topic"]
            ))
        for params in data:
            self.conn.execute(sql, params)
        return len(data)

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
        id, title, url, text, media_ids
        """
        sql = f"""
        SELECT id, title, url, text, media_ids
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
                "text": r[3],
                "media_ids": r[4] or []
            }
            for r in rows
        ]

    def fetch_by_id(self, id: int) -> SimpleNamespace | None:
        row = self.conn.execute(
            f"SELECT id, title, url, text, media_ids, topic FROM {self.table} WHERE id=?",
            [id]
        ).fetchone()
        if not row:
            return None
        media_list = json.loads(row[4]) if row[4] else []
        return SimpleNamespace(
            id=row[0],
            title=row[1],
            url=row[2],
            text=row[3],
            media_ids=media_list,
            topic=row[5]
        )

    def update_title(self, id: int, new_title: str):
        self.conn.execute(f"UPDATE {self.table} SET title=? WHERE id=?", [new_title, id])

    def update_text(self, id: int, new_text: str) -> None:
        sql = f"UPDATE {self.table} SET text=? WHERE id=?"
        self.conn.execute(sql, [new_text, id])

    def update_media(self, id: int, media_ids: list[str]) -> None:
        """
        Сохраняем список как JSON-строку, чтобы DuckDB видел ОДНО значение,
        а не вектор параметров.
        """
        sql = f"UPDATE {self.table} SET media_ids=? WHERE id=?"
        self.conn.execute(sql, [json.dumps(media_ids), id])

    def mark_confirmed(self, ids: List[int]) -> None:
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        sql = f"""
        UPDATE {self.table}
        SET confirmed = TRUE
        WHERE id IN ({placeholders})
        """
        self.conn.execute(sql, ids)

    def mark_rejected(self, ids: List[int]) -> None:
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        sql = f"""
        UPDATE {self.table}
        SET suggested = TRUE  -- уже предлагали, но не подтвердили
        WHERE id IN ({placeholders})
        """
        self.conn.execute(sql, ids)