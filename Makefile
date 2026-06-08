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

.PHONY: docker-build docker-mlflow docker-api docker-down docker-logs docker-data-sample docker-train-uplift docker-register-uplift docker-test-registry docker-test-api docker-shell

docker-build:
	docker compose build

docker-mlflow:
	docker compose up -d mlflow

docker-api:
	docker compose up -d api

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-data-sample:
	docker compose run --rm jobs python -m src.data.make_dataset --sample-size 100000 --chunk-size 500000

docker-train-uplift:
	docker compose run --rm jobs python -m src.models.train_uplift_model

docker-register-uplift:
	docker compose run --rm jobs python -m src.models.register_uplift_model

docker-test-registry:
	docker compose run --rm jobs python -c "import pandas as pd; from src.data.constants import FEATURE_COLS; from src.serving.model_loader import load_uplift_model; model=load_uplift_model(); X=pd.DataFrame([{f:0.0 for f in FEATURE_COLS}]); print(model.predict(X))"

docker-test-api:
	docker compose run --rm jobs pytest tests/test_api.py tests/test_schemas.py -q

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