# src/data_manager/duckdb_repository
from __future__ import annotations
import json
from typing import List, TypeVar, Generic, Sequence

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class DuckDBRepository(Generic[T]):
    """Универсальный репозиторий для Raw/Processed моделей."""

    def __init__(self, conn, table: str, model: type[T]):
        self.conn = conn
        self.table = table
        self.Model = model

    # ─── insert ─── #
    def insert_news(self, items: List[T]) -> int:
        if not items:
            return 0
        cols = list(items[0].dict().keys())  # порядок полей
        sql = (
            f"INSERT INTO {self.table} ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' for _ in cols)}) "
            f"ON CONFLICT (id) DO NOTHING"
        )
        for m in items:
            vals = list(m.dict().values())
            vals[2] = str(vals[2])  # url -> str
            vals[cols.index("media_ids")] = json.dumps(vals[cols.index("media_ids")])
            if "album_mids" in cols:
                vals[cols.index("album_mids")] = json.dumps(vals[cols.index("album_mids")])
            self.conn.execute(sql, vals)
        return len(items)

    # ─── helpers ─── #
    def _row_to_model(self, row: Sequence, cols: Sequence[str]) -> T:
        data = {
            k: (
                json.loads(v)
                if k in ("media_ids", "album_mids") else v
            )
            for k, v in zip(cols, row)
        }
        return self.Model(**data)

    # ─── select all ─── #
    def fetch_all(self) -> List[T]:
        rel = self.conn.execute(f"SELECT * FROM {self.table}")
        cols = [c[0] for c in rel.description]
        return [self._row_to_model(r, cols) for r in rel.fetchall()]


    # ─── select ─── #
    def fetch_unsuggested(self, limit: int) -> List[T]:
        rel = self.conn.execute(
            f"SELECT * FROM {self.table} WHERE suggested = FALSE LIMIT ?",
            [limit],
        )
        cols = [c[0] for c in rel.description]
        return [self._row_to_model(r, cols) for r in rel.fetchall()]

    def fetch_by_id(self, id_: int) -> T | None:
        rel = self.conn.execute(f"SELECT * FROM {self.table} WHERE id=?", [id_])
        row = rel.fetchone()
        return None if row is None else self._row_to_model(row, [c[0] for c in rel.description])

    # ─── update partial ─── #
    def update_fields(self, id_: int, **fields):
        if "media_ids" in fields:
            fields["media_ids"] = json.dumps(fields["media_ids"])
        if "album_mids" in fields:
            fields["album_mids"] = json.dumps(fields["album_mids"])
        sets = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE {self.table} SET {sets} WHERE id=?",
            list(fields.values()) + [id_],
        )

    # ─── flags ─── #
    def set_flag(self, flag: str, ids: List[int]):
        if ids:
            ph = ",".join("?" for _ in ids)
            self.conn.execute(
                f"UPDATE {self.table} SET {flag}=TRUE WHERE id IN ({ph})", ids
            )
