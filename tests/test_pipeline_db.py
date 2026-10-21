"""End-to-end test against a real PostgreSQL (set TEST_DATABASE_URL; skipped otherwise)."""
import os
from pathlib import Path

import psycopg
import pytest

URL = os.getenv("TEST_DATABASE_URL")
FIXTURE = Path(__file__).parent / "fixtures" / "sample_contracts.json"
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture(scope="module")
def loaded_db():
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS marts, staging, raw CASCADE")
    os.environ["DATABASE_URL"] = URL
    import importlib

    from pipeline import config, db, run
    importlib.reload(config); importlib.reload(db); importlib.reload(run)  # noqa: E702
    exit_code = run.main(["--from-file", str(FIXTURE)])
    yield exit_code


def test_run_succeeds_and_loads_all_valid_rows(loaded_db):
    assert loaded_db == 0
    with psycopg.connect(URL) as conn:
        n = conn.execute("SELECT count(*) FROM raw.secop_contracts").fetchone()[0]
        status = conn.execute("SELECT status FROM raw.load_runs ORDER BY run_id DESC LIMIT 1").fetchone()[0]
    assert n == 400  # 402 records: 1 duplicate collapsed, 1 without id skipped
    assert status == "success"


def test_no_personal_data_reaches_the_database(loaded_db):
    with psycopg.connect(URL) as conn:
        cols = {r[0] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'raw' "
            "AND table_name = 'secop_contracts'")}
        names = conn.execute("SELECT count(*) FROM raw.secop_contracts "
                             "WHERE proveedor_adjudicado = 'Persona Natural Demo'").fetchone()[0]
    assert "n_mero_de_cuenta" not in cols and "documento_proveedor" not in cols
    assert names == 0


def test_quality_checks_flag_the_bad_rows(loaded_db):
    with psycopg.connect(URL) as conn:
        res = dict(conn.execute("SELECT check_name, bad_rows FROM raw.quality_results").fetchall())
    assert res["valor_contrato_parseable"] == 1
    assert res["fecha_fin_after_inicio"] == 1
    assert res["id_contrato_unique"] == 0


def test_api_endpoints(loaded_db):
    from fastapi.testclient import TestClient

    import api.main as api_main
    api_main.settings = type(api_main.settings)(database_url=URL)
    client = TestClient(api_main.app)
    assert client.get("/health").json()["last_run"]["status"] == "success"
    assert len(client.get("/entities/direct-contracting", params={"min_contracts": 1}).json()) > 0
    assert len(client.get("/quality/latest").json()) == 7
    assert client.get("/spend/monthly", params={"departamento": "Antioquia"}).status_code == 200
