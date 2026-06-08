# Troubleshooting

## Docker daemon is not running

Error:

```text
failed to connect to the docker API

Fix:

Open Docker Desktop.
Wait until Docker Desktop is running.
Run:
docker info
MLflow Invalid Host Header

Error:

Invalid Host header - possible DNS rebinding attack detected

Fix:

Ensure the MLflow command in docker-compose.yml includes:

--allowed-hosts localhost,127.0.0.1,mlflow,mlflow:5000,0.0.0.0
MLflow model not found

Error:

models:/uplift_model@champion not found

Fix:

Train and register the model inside Docker:

docker compose up -d postgres mlflow
docker compose run --rm jobs python -m src.models.train_uplift_model
docker compose run --rm jobs python -m src.models.register_uplift_model
docker compose up -d api
Artifact path mismatch

Problem:

Model was registered from Windows local path, but API runs in Linux container.

Fix:

Always train and register inside the jobs container when using Docker:

docker compose run --rm jobs python -m src.models.train_uplift_model
docker compose run --rm jobs python -m src.models.register_uplift_model
Prometheus target is DOWN

Check:

http://localhost:9090 → Status → Targets

Fix:

In prometheus.yml, the API target must be:

targets: ["api:8000"]

Do not use:

targets: ["localhost:8000"]

inside Docker Compose.

Grafana dashboard has no data

Generate API traffic:

1..20 | ForEach-Object {
  Invoke-RestMethod `
    -Uri "http://localhost:8000/decide-action" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
}

Then wait 15–30 seconds for Prometheus scraping.

PostgreSQL table does not exist

Run:

docker compose run --rm jobs python -m src.db.init_db
Feedback logs are empty

Check whether decision logs exist:

SELECT COUNT(*) FROM decision_logs;

If zero, call /decide-action first.

Then run:

docker compose run --rm jobs python -m src.feedback.simulate_feedback --limit 1000
Tests fail due to floating point comparison

Use:

pytest.approx(...)

instead of exact equality for floats.

API tests should not require MLflow

API tests should use:

create_app(model=FakeUpliftModel(), enable_decision_logging=False)

Do not let unit tests depend on live MLflow or PostgreSQL services.