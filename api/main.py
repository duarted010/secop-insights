"""Read-only API over the marts.  Run:  uvicorn api.main:app --reload  ->  http://localhost:8000/docs"""
from __future__ import annotations

from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, Query
from psycopg.rows import dict_row

from pipeline.config import settings

app = FastAPI(
    title="SECOP II Contracts API",
    description="Public procurement analytics for Colombia, built from datos.gov.co (SECOP II).",
    version="1.0.0",
)


def get_conn():
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


Conn = Annotated[psycopg.Connection, Depends(get_conn)]


@app.get("/health")
def health(conn: Conn):
    run = conn.execute(
        "SELECT run_id, finished_at, rows_upserted, status FROM raw.load_runs ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    return {"status": "ok", "last_run": run}


@app.get("/spend/monthly")
def monthly_spend(conn: Conn, departamento: str | None = None):
    sql = "SELECT * FROM marts.monthly_spend_by_department"
    params: list = []
    if departamento:
        sql += " WHERE departamento ILIKE %s"
        params.append(departamento)
    return conn.execute(sql + " ORDER BY mes, departamento", params).fetchall()


@app.get("/entities/direct-contracting")
def direct_contracting(conn: Conn, min_contracts: int = Query(20, ge=1), limit: int = Query(20, le=200)):
    """Entities that award the largest share of their budget without competition."""
    return conn.execute(
        "SELECT * FROM marts.direct_contracting_by_entity WHERE contratos >= %s "
        "ORDER BY pct_valor_directo DESC NULLS LAST LIMIT %s", (min_contracts, limit)
    ).fetchall()


@app.get("/entities/supplier-concentration")
def supplier_concentration(conn: Conn, min_suppliers: int = Query(3, ge=1), limit: int = Query(20, le=200)):
    """Entities whose spending is concentrated in few companies (high HHI)."""
    return conn.execute(
        "SELECT * FROM marts.supplier_concentration WHERE proveedores >= %s "
        "ORDER BY hhi DESC LIMIT %s", (min_suppliers, limit)
    ).fetchall()


@app.get("/modalities/extensions")
def extensions(conn: Conn):
    return conn.execute("SELECT * FROM marts.extensions_by_modality ORDER BY contratos DESC").fetchall()


@app.get("/sectors/pyme-share")
def pyme_share(conn: Conn):
    return conn.execute("SELECT * FROM marts.pyme_share_by_sector ORDER BY contratos_con_empresas DESC").fetchall()


@app.get("/quality/latest")
def quality_latest(conn: Conn):
    return conn.execute(
        "SELECT DISTINCT ON (check_name) * FROM raw.quality_results ORDER BY check_name, checked_at DESC"
    ).fetchall()
