# src/data_manager/duckdb_client.py
import duckdb
from pathlib import Path

class DuckDBClient:
    """
    Обёртка над подключением к DuckDB: управляет соединением и схемой.
    """
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.conn = duckdb.connect(str(self.db_path))
        self._ensure_tables()

    def _ensure_tables(self):
        # Создаем таблицу новостей, если её нет
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news (
                id UUID PRIMARY KEY,
                title TEXT,
                url TEXT,
                date TIMESTAMP,
                content TEXT,
                sent BOOLEAN DEFAULT FALSE
            );
            """
        )

    def execute(self, sql: str, params: list = None):
        """
        Выполнить запрос без возврата результата или вернуть DuckDBPyRelation.
        """
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    def fetchall(self, relation):
        """
        Забрать все строки из DuckDBPyRelation.
        """
        return relation.fetchall()

    def fetchdf(self, relation):
        """
        Вернуть результат запроса в виде pandas.DataFrame.
        """
        return relation.df()