# Troubleshooting

## Docker daemon is not running

Error:

```text
failed to connect to the docker API
```

Fix:

- Open Docker Desktop.
- Wait until Docker Desktop is running.
- Run:

```bash
docker info
```

## MLflow Invalid Host Header

Error:

```text
Invalid Host header - possible DNS rebinding attack detected
```

Fix:

Ensure the MLflow command in `docker-compose.yml` includes:

```text
--allowed-hosts localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,mlflow,mlflow:5000
```

## MLflow model not found

Error:

```text
models:/uplift_model@champion not found
```

Fix:

Train and register the model inside Docker:

```bash
docker compose up -d postgres mlflow
docker compose run --rm jobs python -m src.models.train_uplift_model
docker compose run --rm jobs python -m src.models.register_uplift_model
docker compose up -d api
```

## Artifact path mismatch

Problem:

Model was registered from Windows local path, but API runs in Linux container.

Fix:

Always train and register inside the jobs container when using Docker:

```bash
docker compose run --rm jobs python -m src.models.train_uplift_model
docker compose run --rm jobs python -m src.models.register_uplift_model
```

## Prometheus target is DOWN

Check:

- `http://localhost:9090` → Status → Targets

Fix:

In `prometheus.yml`, the API target must be:

```yaml
targets: ["api:8000"]
```

Do not use:

```yaml
targets: ["localhost:8000"]
```

inside Docker Compose.

## Grafana dashboard has no data

Generate API traffic:

```powershell
1..20 | ForEach-Object {
  Invoke-RestMethod `
    -Uri "http://localhost:8000/decide-action" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
}
```

Then wait 15–30 seconds for Prometheus scraping.

## PostgreSQL table does not exist

Run:

```bash
docker compose run --rm jobs python -m src.db.init_db
```

## Feedback logs are empty

Check whether decision logs exist:

```sql
SELECT COUNT(*) FROM decision_logs;
```

If zero, call `/decide-action` first.

Then run:

```bash
docker compose run --rm jobs python -m src.feedback.simulate_feedback --limit 1000
```

## Tests fail due to floating point comparison

Use:

```python
pytest.approx(...)
```

instead of exact equality for floats.

## API tests should not require MLflow

API tests should use:

```python
create_app(model=FakeUpliftModel(), enable_decision_logging=False)
```

Do not let unit tests depend on live MLflow or PostgreSQL services.

## Local test dependencies are missing

If test collection reports missing packages such as `mlflow` or `prometheus_client`, install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

For a clean, reproducible environment, run the test suite inside the Docker jobs image:

```powershell
docker compose build jobs
docker compose run --rm --no-deps jobs pytest tests -q
```
