from pathlib import Path

import pandas as pd


def load_raw_data(path: Path, nrows: int | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at '{path}'. "
            "Please place the Criteo uplift CSV file in data/raw/."
        )

    return pd.read_csv(path, nrows=nrows)


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found at '{path}'.")

    return pd.read_parquet(path)