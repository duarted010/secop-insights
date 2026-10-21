.PHONY: up install demo load update report api test down

up:          ## start PostgreSQL (and the API container)
	docker compose up -d db

install:
	pip install -r requirements.txt

demo:        ## offline run with the synthetic sample
	python -m pipeline.run --from-file tests/fixtures/sample_contracts.json

load:        ## first real load: contracts signed since Jan 2025 (capped at 50k rows)
	python -m pipeline.run --since 2025-01-01 --max-rows 50000

update:      ## incremental load from the last watermark
	python -m pipeline.run

report:
	python -m analysis.report

api:
	uvicorn api.main:app --reload

test:
	TEST_DATABASE_URL=postgresql://secop:secop@localhost:5432/secop_test pytest -q

down:
	docker compose down
