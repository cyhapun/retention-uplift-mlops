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
	python -m src.data.make_dataset --read-rows 100000 --train-sample-size 100000

data:
	python -m src.data.make_dataset --read-rows 1000000 --train-sample-size 1000000