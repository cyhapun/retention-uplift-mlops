# API Examples

## Health Check

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## Model Info

```powershell
Invoke-RestMethod http://localhost:8000/model-info
```

Expected response:

```json
{
  "model_name": "uplift_model",
  "model_alias": "champion",
  "model_uri": "models:/uplift_model@champion",
  "model_loaded": true
}
```

## Decide Action

```powershell
$body = @{
  user_id = "user_001"
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

$response = Invoke-RestMethod `
  -Uri "http://localhost:8000/decide-action" `
  -Method Post `
  -Body $body `
  -ContentType "application/json"

$response
```

Expected fields:

- `decision_id`
- `user_id`
- `treatment_probability`
- `control_probability`
- `uplift_score`
- `customer_value`
- `treatment_cost`
- `expected_incremental_value`
- `roi`
- `recommended_action`
- `decision_reason`
- `model_name`
- `model_alias`
- `model_version`

## Metrics

```powershell
Invoke-WebRequest http://localhost:8000/metrics
```

Expected metrics:

- `retentionops_api_requests_total`
- `retentionops_api_latency_seconds`
- `retentionops_recommended_action_total`
- `retentionops_uplift_score`
- `retentionops_expected_incremental_value`

Decision requests are also written to PostgreSQL when `ENABLE_DECISION_LOGGING=true` (the Docker Compose default). Use `ENABLE_DECISION_LOGGING=false` for isolated API tests that do not need a database.

## Common Validation Error

If a required feature is missing:

```json
{
  "detail": {
    "message": "Missing required features.",
    "missing_features": ["f0"]
  }
}
```
