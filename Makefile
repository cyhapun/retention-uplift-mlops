.PHONY: install test lint format clean mlflow-ui

install:
	pip install -r requirements.txt

test:
	pytest tests -q

lint:
	ruff check src tests

format:
	ruff format src tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

mlflow-ui:
	mlflow ui --host 0.0.0.0 --port 5000

.PHONY: data-sample data

data-sample:
	python -m src.data.make_dataset --sample-size 100000 --chunk-size 500000

data:
	python -m src.data.make_dataset --sample-size 1000000 --chunk-size 500000

.PHONY: train-response

train-response:
	python -m src.models.train_response_model

.PHONY: train-uplift

train-uplift:
	python -m src.models.train_uplift_model

.PHONY: test-policy

test-policy:
	pytest tests/test_policy.py tests/test_budget_optimizer.py -q

.PHONY: register-uplift test-registry

register-uplift:
	python -m src.models.register_uplift_model

test-registry:
	python -c "import pandas as pd; from src.data.constants import FEATURE_COLS; from src.serving.model_loader import load_uplift_model; model=load_uplift_model(); X=pd.DataFrame([{f:0.0 for f in FEATURE_COLS}]); print(model.predict(X))"

.PHONY: api test-api

api:
	uvicorn src.serving.main:app --host 0.0.0.0 --port 8000 --reload

test-api:
	pytest tests/test_api.py tests/test_schemas.py -q

.PHONY: docker-build docker-up-infra docker-init-db docker-train-uplift docker-register-uplift docker-up-api docker-up-monitoring docker-stack docker-smoke docker-logs docker-down docker-clean docker-shell

docker-build:
	docker compose build

docker-up-infra:
	docker compose up -d postgres mlflow

docker-init-db:
	docker compose run --rm jobs python -m src.db.init_db

docker-train-uplift:
	docker compose run --rm jobs python -m src.models.train_uplift_model

docker-register-uplift:
	docker compose run --rm jobs python -m src.models.register_uplift_model

docker-up-api:
	docker compose up -d api

docker-up-monitoring:
	docker compose up -d prometheus grafana

docker-stack:
	docker compose up -d postgres mlflow api prometheus grafana

docker-smoke:
	powershell -ExecutionPolicy Bypass -File scripts/docker-smoke-test.ps1

docker-logs:
	docker compose logs -f

docker-down:
	docker compose down

docker-clean:
	docker compose down -v

docker-shell:
	docker compose run --rm jobs bash


.PHONY: init-db docker-postgres docker-init-db docker-psql docker-db-logs test-db

init-db:
	python -m src.db.init_db

test-db:
	pytest tests/test_decision_logging.py -q

docker-postgres:
	docker compose up -d postgres

docker-init-db:
	docker compose run --rm jobs python -m src.db.init_db

docker-psql:
	docker compose exec postgres psql -U retentionops -d retentionops

docker-db-logs:
	docker compose logs -f postgres

.PHONY: docker-monitoring docker-prometheus docker-grafana docker-monitoring-logs test-metrics

test-metrics:
	pytest tests/test_metrics.py tests/test_api.py -q

docker-prometheus:
	docker compose up -d prometheus

docker-grafana:
	docker compose up -d grafana

docker-monitoring:
	docker compose up -d prometheus grafana

docker-monitoring-logs:
	docker compose logs -f prometheus grafana

.PHONY: simulate-drift drift-report drift-report-drifted test-drift docker-simulate-drift docker-drift-report docker-drift-report-drifted

simulate-drift:
	python -m src.monitoring.simulate_drift

drift-report:
	python -m src.monitoring.drift_report --current-path data/processed/test.parquet --report-name data_drift_report

drift-report-drifted:
	python -m src.monitoring.drift_report --current-path data/processed/test_drifted.parquet --report-name data_drift_report_drifted

test-drift:
	pytest tests/test_drift_simulation.py tests/test_retrain_check.py tests/test_drift_report.py -q

docker-simulate-drift:
	docker compose run --rm jobs python -m src.monitoring.simulate_drift

docker-drift-report:
	docker compose run --rm jobs python -m src.monitoring.drift_report --current-path data/processed/test.parquet --report-name data_drift_report

docker-drift-report-drifted:
	docker compose run --rm jobs python -m src.monitoring.drift_report --current-path data/processed/test_drifted.parquet --report-name data_drift_report_drifted

.PHONY: simulate-feedback test-feedback docker-simulate-feedback docker-feedback-summary

simulate-feedback:
	python -m src.feedback.simulate_feedback --limit 1000 --feedback-delay-days 7

test-feedback:
	pytest tests/test_feedback_simulation.py tests/test_feedback_repository.py -q

docker-simulate-feedback:
	docker compose run --rm jobs python -m src.feedback.simulate_feedback --limit 1000 --feedback-delay-days 7

docker-feedback-summary:
	docker compose exec postgres psql -U retentionops -d retentionops -c "SELECT d.recommended_action, COUNT(f.feedback_id) AS n_feedback, AVG(f.observed_outcome) AS observed_outcome_rate, SUM(f.realized_value) AS total_realized_value FROM feedback_logs f JOIN decision_logs d ON d.decision_id = f.decision_id GROUP BY d.recommended_action ORDER BY n_feedback DESC;"

.PHONY: ci ci-docker

ci:
	ruff check src tests
	ruff format src tests --check
	pytest tests -q

ci-docker:
	docker compose config
	docker compose build api jobs
	docker compose run --rm --no-deps jobs pytest tests -q