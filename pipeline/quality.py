"""Data-quality checks. Each check is a SQL query that counts *bad* rows.

severity "error" fails the pipeline; "warn" is reported but tolerated (SECOP has known messy fields).
Results are stored in raw.quality_results so the API can expose the latest status.
"""
from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class Check:
    name: str
    sql: str
    severity: str = "error"
    max_bad_pct: float = 0.0  # tolerated share of bad rows before the check fails


CHECKS = [
    Check("id_contrato_unique",
          "SELECT count(*) - count(DISTINCT id_contrato) FROM raw.secop_contracts"),
    Check("fecha_firma_parseable",
          "SELECT count(*) FROM staging.contracts WHERE fecha_firma IS NULL",
          severity="warn", max_bad_pct=1.0),
    Check("valor_contrato_parseable",
          "SELECT count(*) FROM staging.contracts WHERE valor_contrato IS NULL",
          severity="warn", max_bad_pct=1.0),
    Check("valor_contrato_non_negative",
          "SELECT count(*) FROM staging.contracts WHERE valor_contrato < 0"),
    Check("fecha_fin_after_inicio",
          "SELECT count(*) FROM staging.contracts WHERE fecha_fin < fecha_inicio",
          severity="warn", max_bad_pct=2.0),
    Check("pagado_not_above_valor",
          "SELECT count(*) FROM staging.contracts WHERE valor_pagado > valor_contrato * 1.5",
          severity="warn", max_bad_pct=1.0),
    Check("no_natural_person_names_stored",
          "SELECT count(*) FROM staging.contracts WHERE NOT proveedor_es_empresa AND proveedor IS NOT NULL"),
]

DDL = """
CREATE TABLE IF NOT EXISTS raw.quality_results (
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    check_name TEXT NOT NULL,
    severity   TEXT NOT NULL,
    bad_rows   BIGINT NOT NULL,
    total_rows BIGINT NOT NULL,
    bad_pct    NUMERIC NOT NULL,
    passed     BOOLEAN NOT NULL
)
"""


def run_checks(conn: psycopg.Connection) -> list[dict]:
    conn.execute(DDL)
    total = conn.execute("SELECT count(*) FROM raw.secop_contracts").fetchone()[0]
    results = []
    for check in CHECKS:
        bad = conn.execute(check.sql).fetchone()[0] or 0
        pct = round(100.0 * bad / total, 3) if total else 0.0
        passed = pct <= check.max_bad_pct
        results.append({"check": check.name, "severity": check.severity, "bad_rows": bad,
                        "total_rows": total, "bad_pct": pct, "passed": passed})
        conn.execute(
            "INSERT INTO raw.quality_results (check_name, severity, bad_rows, total_rows, bad_pct, passed) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (check.name, check.severity, bad, total, pct, passed),
        )
    return results


def has_blocking_failures(results: list[dict]) -> bool:
    return any(not r["passed"] and r["severity"] == "error" for r in results)
