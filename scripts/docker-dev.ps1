param(
    [switch]$BuildData,
    [switch]$Train
)

Write-Host "Starting MLflow..." -ForegroundColor Green
docker compose up -d mlflow

Write-Host "Waiting for MLflow to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

if ($BuildData) {
    Write-Host "Building sample dataset..." -ForegroundColor Green
    docker compose run --rm jobs python -m src.data.make_dataset --sample-size 100000 --chunk-size 500000
}

if ($Train) {
    Write-Host "Training uplift model..." -ForegroundColor Green
    docker compose run --rm jobs python -m src.models.train_uplift_model
}

Write-Host "Registering uplift model..." -ForegroundColor Green
docker compose run --rm jobs python -m src.models.register_uplift_model

Write-Host "Starting API..." -ForegroundColor Green
docker compose up -d api

Write-Host "Current services:" -ForegroundColor Green
docker compose ps

Write-Host ""
Write-Host "MLflow: http://localhost:5000" -ForegroundColor Cyan
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health: http://localhost:8000/health" -ForegroundColor Cyan