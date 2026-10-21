from __future__ import annotations

from pathlib import Path

import psycopg

from .config import settings
from .transform import COLUMNS

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or settings.database_url)


def run_sql_file(conn: psycopg.Connection, name: str) -> None:
    conn.execute((SQL_DIR / name).read_text())


def init_schema(conn: psycopg.Connection) -> None:
    run_sql_file(conn, "01_raw.sql")
    run_sql_file(conn, "02_staging.sql")


def build_marts(conn: psycopg.Connection) -> None:
    run_sql_file(conn, "03_marts.sql")


def upsert_contracts(conn: psycopg.Connection, rows: list[dict]) -> int:
    if not rows:
        return 0
    cols = ", ".join(COLUMNS)
    placeholders = ", ".join(f"%({c})s" for c in COLUMNS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNS if c != "id_contrato")
    sql = (
        f"INSERT INTO raw.secop_contracts ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT (id_contrato) DO UPDATE SET {updates}, _loaded_at = now()"
    )
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    return len(rows)


def last_signed_date(conn: psycopg.Connection):
    """Watermark for incremental loads: latest signature date already stored."""
    return conn.execute("SELECT max(staging.to_date(fecha_de_firma)) FROM raw.secop_contracts").fetchone()[0]
