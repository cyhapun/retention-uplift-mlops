"""Repair legacy MLflow metadata paths after moving mlruns into a named volume."""

import os
import shutil
import sqlite3
from datetime import datetime, timezone


DATABASE_PATH = "/var/lib/mlflow/mlflow.db"
OLD_PATH = "/app/mlruns"
NEW_PATH = "/var/lib/mlflow/mlruns"


def repair_paths() -> int:
    if not os.path.exists(DATABASE_PATH):
        print("MLflow database not found; nothing to repair.")
        return 0

    backup_path = (
        f"{DATABASE_PATH}.before-path-repair-"
        f"{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    )
    shutil.copy2(DATABASE_PATH, backup_path)
    connection = sqlite3.connect(DATABASE_PATH)
    updated = 0

    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        for (table_name,) in tables:
            columns = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
            for _, column_name, column_type, *_ in columns:
                normalized_type = (column_type or "").upper()
                if "CHAR" not in normalized_type and "TEXT" not in normalized_type:
                    continue
                statement = (
                    f'UPDATE "{table_name}" '
                    f'SET "{column_name}" = replace("{column_name}", ?, ?) '
                    f'WHERE "{column_name}" LIKE ?'
                )
                cursor = connection.execute(
                    statement,
                    (OLD_PATH, NEW_PATH, f"%{OLD_PATH}%"),
                )
                updated += cursor.rowcount
        connection.commit()
    finally:
        connection.close()

    print(f"Updated {updated} MLflow metadata values.")
    print(f"Backup created at {backup_path}.")
    return updated


if __name__ == "__main__":
    repair_paths()
