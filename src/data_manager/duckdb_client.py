# src/data_manager/duckdb_client.py
import duckdb
from pathlib import Path
from src.utils.paths import RAW_DB, PROCESSED_DB


class DuckDBClient:
    """
    Обёртка над подключением к DuckDB: управляет соединением и схемой.
    """

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        # Убедимся, что папка для БД существует
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Если файл есть, но нулевой длины — удаляем, чтобы DuckDB создал новый
        if self.db_path.exists() and self.db_path.stat().st_size == 0:
            self.db_path.unlink()

        # Подключаемся (создаст файл, если его нет)
        self.conn = duckdb.connect(str(self.db_path))
        self._ensure_tables()

    def _ensure_tables(self):
        # Создаём таблицу news, если её ещё нет
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id UUID PRIMARY KEY,
                title TEXT,
                url TEXT,
                date TIMESTAMP,
                content TEXT,
                media_id UUID,
                language
            );
        """)

    def execute(self, sql: str, params: list = None):
        """
        Выполнить запрос; если заданы params — с ними.
        Возвращает DuckDBPyRelation или None.
        """
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    def fetchall(self, relation):
        """Забрать все строки из DuckDBPyRelation."""
        return relation.fetchall()

    def fetchdf(self, relation):
        """Вернуть результат запроса в виде pandas.DataFrame."""
        return relation.df()

    @classmethod
    def create_database(cls):
        """
        Создаёт/открывает БД 'raw' и 'processed' и возвращает dict:
        {'raw': DuckDBClient, 'processed': DuckDBClient}.
        """
        clients = {}
        for name, path in {'raw': RAW_DB, 'processed': PROCESSED_DB}.items():
            clients[name] = cls(path)
        return clients