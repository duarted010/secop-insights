# SECOP II Contracts Pipeline 🇨🇴

An end-to-end data pipeline over **Colombia's public procurement data** (SECOP II, published on
[datos.gov.co](https://www.datos.gov.co/resource/jbjy-vk9h)). It extracts contracts from the Socrata API,
loads them incrementally into PostgreSQL, models them with SQL into analysis-ready tables, checks data
quality on every run, and serves the results through a FastAPI service.

**Questions it answers**
- How much does each department spend per month?
- Which entities award the largest share of their budget **without competition** (*contratación directa*)?
- Which entities depend on very few suppliers? (Herfindahl-Hirschman Index)
- How often are contracts **extended**, and does it depend on the contracting modality?
- How much of the money reaches **SMEs (pymes)**, by sector?

## Architecture

```
datos.gov.co (Socrata API)
        │  extract.py — paginated, retries with backoff, incremental watermark
        ▼
 transform.py — column whitelist + PII removal
        │
        ▼
 PostgreSQL
  ├── raw.secop_contracts        upsert on id_contrato (idempotent re-runs)
  ├── raw.load_runs              audit log of every run
  ├── staging.contracts (view)   typed, trimmed, normalized
  ├── marts.*                    5 analysis tables (sql/03_marts.sql)
  └── raw.quality_results        7 data-quality checks per run
        │
        ├── api/main.py          FastAPI (read-only)  → /docs
        └── analysis/report.py   charts + docs/FINDINGS.md
```

## Design decisions

- **Privacy by design.** SECOP publishes personal data (ID numbers, bank account numbers, names of officials
  and of individual contractors). The pipeline keeps an explicit **whitelist** of columns and drops the supplier
  name whenever the supplier is a natural person. A quality check fails the run if a personal name ever lands
  in the database.
- **Idempotent, incremental loads.** Rows are upserted by `id_contrato`. Without `--since`, a run continues from
  the latest signature date already stored, minus a 7-day overlap, because SECOP records keep changing after
  signature (payments, status).
- **ELT with SQL.** Raw values are stored as text and typed in the staging view with safe casts, so one bad
  value becomes a `NULL` that the quality checks count, instead of crashing the load.
- **Quality gates.** `error` checks (duplicate ids, negative values, PII) fail the run. `warn` checks
  (unparseable dates/values, end date before start date) are tolerated up to a threshold, because the source
  is known to be messy. Results are stored and exposed at `/quality/latest`.

## Run it

Requirements: Docker and Python 3.11+.

```bash
cp .env.example .env
docker compose up -d db            # PostgreSQL on localhost:5432
pip install -r requirements.txt

python -m pipeline.run --since 2025-01-01 --max-rows 50000   # first load (real data)
python -m pipeline.run                                       # later: incremental update
python -m analysis.report                                    # charts + docs/FINDINGS.md
uvicorn api.main:app --reload                                # http://localhost:8000/docs
```

Offline demo, no internet needed: `python -m pipeline.run --from-file tests/fixtures/sample_contracts.json`.
The fixture is **synthetic**, with the same shape as the API.

## API

| Endpoint | What it returns |
|---|---|
| `GET /health` | status of the last pipeline run |
| `GET /spend/monthly?departamento=Antioquia` | monthly contract count and value per department |
| `GET /entities/direct-contracting?min_contracts=20` | entities ranked by % of value awarded directly |
| `GET /entities/supplier-concentration?min_suppliers=3` | entities ranked by supplier concentration (HHI) |
| `GET /modalities/extensions` | % of contracts extended and average extra days, by modality |
| `GET /sectors/pyme-share` | share of contracts and value going to SMEs, by sector |
| `GET /quality/latest` | latest result of each data-quality check |

## Tests

```bash
docker compose exec db createdb -U secop secop_test
TEST_DATABASE_URL=postgresql://secop:secop@localhost:5432/secop_test pytest -q
```

Unit tests cover the transform (whitelist, PII removal, deduplication). An end-to-end test loads the synthetic
fixture into PostgreSQL, checks the quality results, and calls every API endpoint. CI runs everything on each
push (GitHub Actions with a Postgres service).

## Findings

See [`docs/FINDINGS.md`](docs/FINDINGS.md). It is generated from real data by `python -m analysis.report`.

## Next steps

- Schedule daily incremental runs (cron / GitHub Actions / Airflow).
- Port the SQL models to dbt for lineage and documentation.
- Add SECOP I and supplier data to compare competitive vs. direct awards over time.

---
Built by **Daniel Duarte** · [LinkedIn](https://linkedin.com/in/daniel-aduarteu) · [GitHub](https://github.com/oxtornado)
