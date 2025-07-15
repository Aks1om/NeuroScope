# src/data_manager/duckdb_repository.py

import json

class DuckDBRepository:
    """Универсальный репозиторий для Raw и Processed моделей."""

    def __init__(self, conn, table, model):
        self.conn = conn
        self.table = table
        self.Model = model

    def insert_news(self, items):
        if not items:
            return 0
        cols = list(items[0].dict().keys())
        sql = (
            f"INSERT INTO {self.table} ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' for _ in cols)}) "
            f"ON CONFLICT (id) DO NOTHING"
        )
        for m in items:
            vals = list(m.dict().values())
            # url -> str
            vals[cols.index("url")] = str(vals[cols.index("url")])
            # сериализуем media_ids/album_mids
            if "media_ids" in cols:
                vals[cols.index("media_ids")] = json.dumps(vals[cols.index("media_ids")])
            if "album_mids" in cols:
                vals[cols.index("album_mids")] = json.dumps(vals[cols.index("album_mids")])
            self.conn.execute(sql, vals)
        return len(items)

    def _row_to_model(self, row, cols):
        data = {
            k: (
                json.loads(v)
                if k in ("media_ids", "album_mids") and v is not None else v
            )
            for k, v in zip(cols, row)
        }
        return self.Model(**data)

    def fetch_all(self):
        rel = self.conn.execute(f"SELECT * FROM {self.table}")
        cols = [c[0] for c in rel.description]
        return [self._row_to_model(r, cols) for r in rel.fetchall()]

    def fetch_unsuggested(self, limit):
        rel = self.conn.execute(
            f"SELECT * FROM {self.table} WHERE suggested = FALSE LIMIT ?",
            [limit],
        )
        cols = [c[0] for c in rel.description]
        return [self._row_to_model(r, cols) for r in rel.fetchall()]

    def fetch_by_id(self, id_):
        rel = self.conn.execute(f"SELECT * FROM {self.table} WHERE id=?", [id_])
        row = rel.fetchone()
        return None if row is None else self._row_to_model(row, [c[0] for c in rel.description])

    def update_fields(self, id_, **fields):
        if "media_ids" in fields:
            fields["media_ids"] = json.dumps(fields["media_ids"])
        if "album_mids" in fields:
            fields["album_mids"] = json.dumps(fields["album_mids"])
        sets = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE {self.table} SET {sets} WHERE id=?",
            list(fields.values()) + [id_],
        )

    def set_flag(self, flag, ids):
        if ids:
            ph = ",".join("?" for _ in ids)
            self.conn.execute(
                f"UPDATE {self.table} SET {flag}=TRUE WHERE id IN ({ph})", ids
            )
