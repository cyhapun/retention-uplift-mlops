import argparse
from pathlib import Path
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
from src.data.load_data import load_raw_data, save_parquet
from src.data.validate_schema import resolve_target_column, validate_schema


def create_sample(df: pd.DataFrame, n: int, random_state: int = RANDOM_STATE) -> pd.DataFrame:
    if len(df) <= n:
        return df.copy()

    return df.sample(n=n, random_state=random_state)


def make_stratify_labels(df: pd.DataFrame, target_col: str) -> pd.Series | None:
    labels = df[TREATMENT_COL].astype(str) + "_" + df[target_col].astype(str)

    # train_test_split stratify can fail if any class has fewer than 2 rows.
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

    return train_df, valid_df, test_df


def select_model_columns(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    cols = FEATURE_COLS + [TREATMENT_COL, target_col]
    return df[cols].copy()


def write_dataset_summary(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str,
) -> None:
    summary = {
        "target_col": target_col,
        "train_rows": len(train_df),
        "valid_rows": len(valid_df),
        "test_rows": len(test_df),
        "train_treatment_rate": train_df[TREATMENT_COL].mean(),
        "valid_treatment_rate": valid_df[TREATMENT_COL].mean(),
        "test_treatment_rate": test_df[TREATMENT_COL].mean(),
        "train_target_rate": train_df[target_col].mean(),
        "valid_target_rate": valid_df[target_col].mean(),
        "test_target_rate": test_df[target_col].mean(),
    }

    summary_df = pd.DataFrame([summary])
    save_parquet(summary_df, PROCESSED_DIR / "dataset_summary.parquet")

    print("Dataset summary:")
    for key, value in summary.items():
        print(f"- {key}: {value}")


def build_datasets(
    raw_path: str | Path = RAW_DATA_PATH,
    read_rows: int | None = 1_000_000,
    train_sample_size: int = 1_000_000,
) -> None:
    raw_path = Path(raw_path)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading raw data from: {raw_path}")
    df = load_raw_data(raw_path, nrows=read_rows)

    target_col = resolve_target_column(
        df,
        primary_target=PRIMARY_TARGET_COL,
        fallback_target=FALLBACK_TARGET_COL,
    )

    print(f"Using target column: {target_col}")

    df = select_model_columns(df, target_col=target_col)
    validate_schema(df, target_col=target_col)

    sample_100k = create_sample(df, n=100_000)
    sample_1m = create_sample(df, n=1_000_000)

    save_parquet(sample_100k, INTERIM_DIR / "sample_100k.parquet")
    save_parquet(sample_1m, INTERIM_DIR / "sample_1m.parquet")

    modeling_df = create_sample(df, n=train_sample_size)
    train_df, valid_df, test_df = split_data(modeling_df, target_col=target_col)

    save_parquet(train_df, PROCESSED_DIR / "train.parquet")
    save_parquet(valid_df, PROCESSED_DIR / "valid.parquet")
    save_parquet(test_df, PROCESSED_DIR / "test.parquet")

    # Reference data will be used later for drift detection.
    save_parquet(train_df, REFERENCE_DIR / "reference.parquet")

    write_dataset_summary(
        train_df=train_df,
        valid_df=valid_df,
        test_df=test_df,
        target_col=target_col,
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
        "--read-rows",
        type=int,
        default=1_000_000,
        help=(
            "Number of rows to read from raw CSV. "
            "Use a smaller value for local development on weak machines."
        ),
    )

    parser.add_argument(
        "--train-sample-size",
        type=int,
        default=1_000_000,
        help="Number of rows used to create train/valid/test datasets.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_datasets(
        raw_path=args.raw_path,
        read_rows=args.read_rows,
        train_sample_size=args.train_sample_size,
    )


if __name__ == "__main__":
    main()