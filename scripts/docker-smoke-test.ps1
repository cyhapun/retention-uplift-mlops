$ErrorActionPreference = "Stop"

Write-Host "Running RetentionOps smoke test..." -ForegroundColor Cyan

Write-Host "Checking API health..." -ForegroundColor Green
$health = Invoke-RestMethod http://localhost:8000/health
Write-Host "Health:" ($health | ConvertTo-Json)

Write-Host "Checking model info..." -ForegroundColor Green
$modelInfo = Invoke-RestMethod http://localhost:8000/model-info
Write-Host "Model info:" ($modelInfo | ConvertTo-Json)

Write-Host "Calling /decide-action..." -ForegroundColor Green
$body = @{
  user_id = "smoke_test_user"
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

Write-Host "Decision response:" ($response | ConvertTo-Json -Depth 5)

if (-not $response.decision_id) {
    throw "Smoke test failed: decision_id is missing"
}

if (-not $response.recommended_action) {
    throw "Smoke test failed: recommended_action is missing"
}

Write-Host "Checking Prometheus metrics endpoint..." -ForegroundColor Green
$metrics = Invoke-WebRequest http://localhost:8000/metrics
if ($metrics.Content -notmatch "retentionops_api_requests_total") {
    throw "Smoke test failed: API metrics are missing"
}

Write-Host "Checking PostgreSQL decision log count..." -ForegroundColor Green
docker compose exec postgres psql -U retentionops -d retentionops -c "SELECT COUNT(*) FROM decision_logs;"

Write-Host "Smoke test completed successfully." -ForegroundColor Cyan