"""Pipeline entry point.

    python -m pipeline.run --since 2025-01-01 --max-rows 50000   # first (backfill) load
    python -m pipeline.run                                       # incremental: continues from the last load
    python -m pipeline.run --from-file tests/fixtures/sample_contracts.json   # offline demo
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta

from . import db, quality
from .extract import fetch_contracts
from .transform import to_rows

log = logging.getLogger("pipeline")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SECOP II contracts -> PostgreSQL")
    parser.add_argument("--since", type=date.fromisoformat, help="load contracts signed on/after this date")
    parser.add_argument("--until", type=date.fromisoformat, help="...and before this date")
    parser.add_argument("--max-rows", type=int, default=None, help="cap rows fetched (handy for a first try)")
    parser.add_argument("--from-file", help="load a local JSON file instead of calling the API")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    with db.connect() as conn:
        db.init_schema(conn)
        since = args.since or _incremental_start(conn)
        run_id = conn.execute(
            "INSERT INTO raw.load_runs (since_date, status) VALUES (%s, 'running') RETURNING run_id", (since,)
        ).fetchone()[0]
        conn.commit()

        fetched = upserted = 0
        try:
            pages = [json.load(open(args.from_file, encoding="utf-8"))] if args.from_file \
                else fetch_contracts(since, args.until, args.max_rows)
            for page in pages:
                fetched += len(page)
                upserted += db.upsert_contracts(conn, to_rows(page))
                conn.commit()  # commit per page so a failure mid-backfill keeps progress
            db.build_marts(conn)
            results = quality.run_checks(conn)
            status = "failed_quality" if quality.has_blocking_failures(results) else "success"
        except Exception:
            conn.rollback()
            _finish(conn, run_id, fetched, upserted, "error")
            raise

        _finish(conn, run_id, fetched, upserted, status)

    log.info("run %s: fetched=%s upserted=%s status=%s", run_id, fetched, upserted, status)
    for r in results:
        if not r["passed"]:
            flag = "FAIL" if r["severity"] == "error" else "WARN"
        else:
            flag = "WARN" if r["bad_rows"] else "PASS"
        log.info("  [%s] %-32s bad=%s (%.2f%%)", flag, r["check"], r["bad_rows"], r["bad_pct"])
    return 1 if status == "failed_quality" else 0


def _incremental_start(conn) -> date:
    last = db.last_signed_date(conn)
    # Re-read the last 7 days: SECOP records get updated after signature (payments, state changes).
    return (last - timedelta(days=7)) if last else date.today() - timedelta(days=90)


def _finish(conn, run_id, fetched, upserted, status):
    conn.execute(
        "UPDATE raw.load_runs SET finished_at = now(), rows_fetched = %s, rows_upserted = %s, status = %s "
        "WHERE run_id = %s", (fetched, upserted, status, run_id))
    conn.commit()


if __name__ == "__main__":
    sys.exit(main())
