$ErrorActionPreference = "Stop"

Write-Host "Repairing legacy MLflow paths inside the named volume..." -ForegroundColor Cyan

docker compose run --rm --no-deps --entrypoint python mlflow scripts/repair_mlflow_paths.py
if ($LASTEXITCODE -ne 0) {
    throw "MLflow path repair failed with exit code $LASTEXITCODE."
}
Write-Host "MLflow path repair completed; the backup remains in the named volume." -ForegroundColor Green
