# RetentionOps Demo Guide

This guide shows how to run the full RetentionOps stack locally.

## Prerequisites

- Docker Desktop running
- Docker Compose available
- Raw Criteo uplift dataset placed under:

```text
data/raw/criteo-uplift.csv
```

## First-Time Setup

Create local environment file:

```powershell
Copy-Item .env.example .env
```

Build Docker images:

```bash
docker compose build
```

## Run Full Stack

If processed data already exists:

```powershell
.\scripts\docker-bootstrap.ps1 -Train -Monitoring
```

If processed data does not exist:

```powershell
.\scripts\docker-bootstrap.ps1 -BuildData -Train -Monitoring
```

This starts:

- PostgreSQL
- MLflow
- FastAPI
- Prometheus
- Grafana

### URLs

| Service | URL |
|---------|-----|
| MLflow | http://localhost:5000 |
| FastAPI docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Grafana login:

- username: `admin`
- password: `admin`

## Smoke Test

Run:

```powershell
.\scripts\docker-smoke-test.ps1
```

The smoke test checks:

- `GET /health`
- `GET /model-info`
- `POST /decide-action`
- `GET /metrics`
- PostgreSQL decision log count

## Example API Request

```powershell
$body = @{
  user_id = "demo_user_001"
  customer_value = 100
  features = @{
    f0 = 0.0
    f1 = 0.0
    f2 = 0.0
    f3 = 0.0
    f4 = 0.0
    f5 = 0.0
    f6 = 0.0
    f7 = 0.0
    f8 = 0.0
    f9 = 0.0
    f10 = 0.0
  }
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
  -Uri "http://localhost:8000/decide-action" `
  -Method Post `
  -Body $body `
  -ContentType "application/json"
```

Expected response includes:

- `decision_id`
- `treatment_probability`
- `control_probability`
- `uplift_score`
- `expected_incremental_value`
- `recommended_action`
- `model_name`
- `model_alias`
- `model_version`

## Check Decision Logs

```bash
docker compose exec postgres psql -U retentionops -d retentionops
```

```sql
SELECT COUNT(*) FROM decision_logs;

SELECT
  decision_id,
  user_id,
  uplift_score,
  expected_incremental_value,
  recommended_action,
  created_at
FROM decision_logs
ORDER BY created_at DESC
LIMIT 5;
```

## Generate Monitoring Data

Call `/decide-action` multiple times:

```powershell
1..20 | ForEach-Object {
  Invoke-RestMethod `
    -Uri "http://localhost:8000/decide-action" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
}
```

Then open Grafana:

http://localhost:3000

Dashboard:

- Dashboards → RetentionOps → RetentionOps Monitoring

## Run Drift Detection

```bash
docker compose run --rm jobs python -m src.monitoring.drift_report --current-path data/processed/test.parquet --report-name data_drift_report
```

Simulate drift:

```bash
docker compose run --rm jobs python -m src.monitoring.simulate_drift
```

Run drifted report:

```bash
docker compose run --rm jobs python -m src.monitoring.drift_report --current-path data/processed/test_drifted.parquet --report-name data_drift_report_drifted
```

## Simulate Delayed Feedback

```bash
docker compose run --rm jobs python -m src.feedback.simulate_feedback --limit 1000 --feedback-delay-days 7
```

Check feedback logs:

```sql
SELECT COUNT(*) FROM feedback_logs;
```

## Stop Stack

Keep volumes:

```bash
docker compose down
```

Remove volumes:

```bash
docker compose down -v
```