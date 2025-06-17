import duckdb
from pathlib import Path

base_dir = Path(__file__).resolve().parents[2]
data_dir = base_dir / 'data'


data_dir.mkdir(parents=True, exist_ok=True)


(data_dir / 'raw_data.duckdb').touch(exist_ok=True)
(data_dir / 'processed_data.duckdb').touch(exist_ok=True)
