param(
    [switch]$BuildImages,
    [switch]$BuildData,
    [switch]$Train,
    [switch]$SkipRegister,
    [switch]$Monitoring
)

$ErrorActionPreference = "Stop"

Write-Host "RetentionOps Docker Bootstrap" -ForegroundColor Cyan

if ($BuildImages) {
    Write-Host "Building Docker images..." -ForegroundColor Green
    docker compose build
}

Write-Host "Starting infrastructure services: postgres + mlflow..." -ForegroundColor Green
docker compose up -d postgres mlflow

Write-Host "Waiting for infrastructure services..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "Initializing database..." -ForegroundColor Green
docker compose run --rm jobs python -m src.db.init_db

if ($BuildData) {
    Write-Host "Building sample dataset..." -ForegroundColor Green
    docker compose run --rm jobs python -m src.data.make_dataset --sample-size 100000 --chunk-size 500000
}

if ($Train) {
    Write-Host "Training uplift model..." -ForegroundColor Green
    docker compose run --rm jobs python -m src.models.train_uplift_model
}

if (-not $SkipRegister) {
    Write-Host "Registering uplift model..." -ForegroundColor Green
    docker compose run --rm jobs python -m src.models.register_uplift_model
}

Write-Host "Starting API..." -ForegroundColor Green
docker compose up -d api

if ($Monitoring) {
    Write-Host "Starting monitoring services: prometheus + grafana..." -ForegroundColor Green
    docker compose up -d prometheus grafana
}

Write-Host "Current services:" -ForegroundColor Green
docker compose ps

Write-Host ""
Write-Host "URLs:" -ForegroundColor Cyan
Write-Host "MLflow:       http://localhost:5000"
Write-Host "API docs:     http://localhost:8000/docs"
Write-Host "API health:   http://localhost:8000/health"
Write-Host "Prometheus:   http://localhost:9090"
Write-Host "Grafana:      http://localhost:3000"