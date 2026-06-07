import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.data.constants import (
    FALLBACK_TARGET_COL,
    FEATURE_COLS,
    INTERIM_DIR,
    PRIMARY_TARGET_COL,
    PROCESSED_DIR,
    RANDOM_STATE,
    RAW_DATA_PATH,
    REFERENCE_DIR,
    TREATMENT_COL,
)
from src.data.load_data import save_parquet
from src.data.validate_schema import resolve_target_column, validate_columns, validate_schema


def assert_has_treatment_and_control(df: pd.DataFrame, dataset_name: str) -> None:
    values = set(df[TREATMENT_COL].dropna().unique())

    if not {0, 1}.issubset(values):
        raise ValueError(
            f"{dataset_name} must contain both treatment=1 and control=0 groups. "
            f"Found treatment values: {sorted(values)}"
        )


def get_model_columns(target_col: str) -> list[str]:
    return FEATURE_COLS + [TREATMENT_COL, target_col]


def read_raw_header(raw_path: str | Path) -> pd.DataFrame:
    raw_path = Path(raw_path)

    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at '{raw_path}'. "
            "Please place the Criteo uplift CSV file in data/raw/."
        )

    return pd.read_csv(raw_path, nrows=0)


def load_raw_sample_from_full_file(
    raw_path: str | Path,
    sample_size: int,
    chunk_size: int = 500_000,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, str, dict[int, int]]:
    """
    Uniformly sample rows across the entire raw CSV using chunked reading.

    This avoids the dangerous pattern of reading only the first N rows, which can
    miss the control group when the raw file is sorted by treatment assignment.
    """
    raw_path = Path(raw_path)
    header_df = read_raw_header(raw_path)

    target_col = resolve_target_column(
        header_df,
        primary_target=PRIMARY_TARGET_COL,
        fallback_target=FALLBACK_TARGET_COL,
    )

    model_columns = get_model_columns(target_col)
    validate_columns(header_df, target_col=target_col)

    rng = np.random.default_rng(random_state)
    reservoir: pd.DataFrame | None = None
    raw_treatment_counts = {0: 0, 1: 0}
    total_rows_seen = 0

    print("Sampling across the full raw file.")
    print(f"Raw path: {raw_path}")
    print(f"Target column: {target_col}")
    print(f"Sample size: {sample_size}")
    print(f"Chunk size: {chunk_size}")

    for chunk_idx, chunk in enumerate(
        pd.read_csv(raw_path, usecols=model_columns, chunksize=chunk_size),
        start=1,
    ):
        validate_schema(chunk, target_col=target_col)

        total_rows_seen += len(chunk)

        counts = chunk[TREATMENT_COL].value_counts()
        raw_treatment_counts[0] += int(counts.get(0, 0))
        raw_treatment_counts[1] += int(counts.get(1, 0))

        chunk = chunk.copy()
        chunk["_sample_key"] = rng.random(len(chunk))

        if reservoir is None:
            reservoir = chunk
        else:
            reservoir = pd.concat([reservoir, chunk], ignore_index=True)

        if len(reservoir) > sample_size:
            reservoir = reservoir.nsmallest(sample_size, "_sample_key").reset_index(drop=True)

        if chunk_idx % 10 == 0:
            print(
                f"Processed chunks: {chunk_idx}, "
                f"rows seen: {total_rows_seen:,}, "
                f"raw treatment counts: {raw_treatment_counts}"
            )

    if reservoir is None or reservoir.empty:
        raise ValueError("No rows were loaded from the raw dataset.")

    sample_df = (
        reservoir.drop(columns=["_sample_key"])
        .sample(frac=1.0, random_state=random_state)
        .reset_index(drop=True)
    )

    assert_has_treatment_and_control(sample_df, dataset_name="sample_df")

    print("Finished full-file sampling.")
    print(f"Total rows seen: {total_rows_seen:,}")
    print(f"Raw treatment counts: {raw_treatment_counts}")
    print("Sample treatment distribution:")
    print(sample_df[TREATMENT_COL].value_counts(normalize=True).sort_index())

    return sample_df, target_col, raw_treatment_counts


def create_sample(df: pd.DataFrame, n: int, random_state: int = RANDOM_STATE) -> pd.DataFrame:
    if len(df) <= n:
        return df.copy()

    return df.sample(n=n, random_state=random_state).reset_index(drop=True)


def make_stratify_labels(df: pd.DataFrame, target_col: str) -> pd.Series | None:
    labels = df[TREATMENT_COL].astype(str) + "_" + df[target_col].astype(str)

    if labels.value_counts().min() < 2:
        return None

    return labels


def split_data(
    df: pd.DataFrame,
    target_col: str,
    test_size: float = 0.15,
    valid_size: float = 0.15,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    assert_has_treatment_and_control(df, dataset_name="modeling_df")

    temp_size = test_size + valid_size
    stratify_labels = make_stratify_labels(df, target_col)

    train_df, temp_df = train_test_split(
        df,
        test_size=temp_size,
        random_state=random_state,
        stratify=stratify_labels,
    )

    relative_test_size = test_size / temp_size
    temp_stratify_labels = make_stratify_labels(temp_df, target_col)

    valid_df, test_df = train_test_split(
        temp_df,
        test_size=relative_test_size,
        random_state=random_state,
        stratify=temp_stratify_labels,
    )

    assert_has_treatment_and_control(train_df, dataset_name="train_df")
    assert_has_treatment_and_control(valid_df, dataset_name="valid_df")
    assert_has_treatment_and_control(test_df, dataset_name="test_df")

    return (
        train_df.reset_index(drop=True),
        valid_df.reset_index(drop=True),
        test_df.reset_index(drop=True),
    )


def write_dataset_summary(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str,
    raw_treatment_counts: dict[int, int],
) -> None:
    summary = {
        "target_col": target_col,
        "raw_control_rows_seen": raw_treatment_counts.get(0, 0),
        "raw_treatment_rows_seen": raw_treatment_counts.get(1, 0),
        "train_rows": len(train_df),
        "valid_rows": len(valid_df),
        "test_rows": len(test_df),
        "train_treatment_rate": train_df[TREATMENT_COL].mean(),
        "valid_treatment_rate": valid_df[TREATMENT_COL].mean(),
        "test_treatment_rate": test_df[TREATMENT_COL].mean(),
        "train_target_rate": train_df[target_col].mean(),
        "valid_target_rate": valid_df[target_col].mean(),
        "test_target_rate": test_df[target_col].mean(),
        "train_control_rows": int((train_df[TREATMENT_COL] == 0).sum()),
        "valid_control_rows": int((valid_df[TREATMENT_COL] == 0).sum()),
        "test_control_rows": int((test_df[TREATMENT_COL] == 0).sum()),
        "train_treatment_rows": int((train_df[TREATMENT_COL] == 1).sum()),
        "valid_treatment_rows": int((valid_df[TREATMENT_COL] == 1).sum()),
        "test_treatment_rows": int((test_df[TREATMENT_COL] == 1).sum()),
    }

    summary_df = pd.DataFrame([summary])
    save_parquet(summary_df, PROCESSED_DIR / "dataset_summary.parquet")

    print("Dataset summary:")
    for key, value in summary.items():
        print(f"- {key}: {value}")


def build_datasets(
    raw_path: str | Path = RAW_DATA_PATH,
    sample_size: int = 1_000_000,
    chunk_size: int = 500_000,
) -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    df, target_col, raw_treatment_counts = load_raw_sample_from_full_file(
        raw_path=raw_path,
        sample_size=sample_size,
        chunk_size=chunk_size,
    )

    sample_100k = create_sample(df, n=100_000)
    sample_1m = create_sample(df, n=1_000_000)

    assert_has_treatment_and_control(sample_100k, dataset_name="sample_100k")
    assert_has_treatment_and_control(sample_1m, dataset_name="sample_1m")

    save_parquet(sample_100k, INTERIM_DIR / "sample_100k.parquet")
    save_parquet(sample_1m, INTERIM_DIR / "sample_1m.parquet")

    train_df, valid_df, test_df = split_data(df, target_col=target_col)

    save_parquet(train_df, PROCESSED_DIR / "train.parquet")
    save_parquet(valid_df, PROCESSED_DIR / "valid.parquet")
    save_parquet(test_df, PROCESSED_DIR / "test.parquet")

    save_parquet(train_df, REFERENCE_DIR / "reference.parquet")

    write_dataset_summary(
        train_df=train_df,
        valid_df=valid_df,
        test_df=test_df,
        target_col=target_col,
        raw_treatment_counts=raw_treatment_counts,
    )

    print("Saved datasets:")
    print(f"- {INTERIM_DIR / 'sample_100k.parquet'}")
    print(f"- {INTERIM_DIR / 'sample_1m.parquet'}")
    print(f"- {PROCESSED_DIR / 'train.parquet'}")
    print(f"- {PROCESSED_DIR / 'valid.parquet'}")
    print(f"- {PROCESSED_DIR / 'test.parquet'}")
    print(f"- {REFERENCE_DIR / 'reference.parquet'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RetentionOps datasets.")

    parser.add_argument(
        "--raw-path",
        type=str,
        default=str(RAW_DATA_PATH),
        help="Path to raw Criteo uplift CSV file.",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=1_000_000,
        help="Number of rows to sample across the full raw CSV.",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500_000,
        help="Number of rows per CSV chunk.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_datasets(
        raw_path=args.raw_path,
        sample_size=args.sample_size,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
