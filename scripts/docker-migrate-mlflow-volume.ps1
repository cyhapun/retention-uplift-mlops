param(
    [switch]$BuildImage
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." -Resolve)).Path
$localDatabase = Join-Path $projectRoot "mlflow.db"
$localArtifacts = Join-Path $projectRoot "mlruns"

if (-not (Test-Path -LiteralPath $localDatabase) -and -not (Test-Path -LiteralPath $localArtifacts)) {
    Write-Host "No local MLflow data found; nothing to migrate." -ForegroundColor Yellow
    exit 0
}

if ($BuildImage) {
    docker compose build mlflow
}

$migrationScript = @'
import os
import shutil
import sqlite3

source = "/app"
target = "/var/lib/mlflow"
database = os.path.join(source, "mlflow.db")
artifacts = os.path.join(source, "mlruns")

if not os.path.isfile(database) and not os.path.isdir(artifacts):
    print("No local MLflow data found; nothing to migrate.")
    raise SystemExit(0)

if os.listdir(target):
    raise RuntimeError("MLflow volume is not empty; refusing to overwrite existing data.")

if os.path.isfile(database):
    shutil.copy2(database, os.path.join(target, "mlflow.db"))
if os.path.isdir(artifacts):
    shutil.copytree(artifacts, os.path.join(target, "mlruns"))

database_path = os.path.join(target, "mlflow.db")
if os.path.isfile(database_path):
    connection = sqlite3.connect(database_path)
    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        for (table_name,) in tables:
            columns = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
            for _, column_name, column_type, *_ in columns:
                if "CHAR" not in (column_type or "").upper() and "TEXT" not in (column_type or "").upper():
                    continue
                connection.execute(
                    f'UPDATE "{table_name}" SET "{column_name}" = replace("{column_name}", ?, ?) WHERE "{column_name}" LIKE ?',
                    ("/app/mlruns", "/var/lib/mlflow/mlruns", "%/app/mlruns%"),
                )
        connection.commit()
    finally:
        connection.close()

print("Migrated local MLflow data to the Docker volume.")
'@

docker compose run --rm --no-deps --entrypoint python mlflow -c $migrationScript
