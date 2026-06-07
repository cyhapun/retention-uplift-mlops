import pandas as pd

from src.data.constants import FEATURE_COLS, TREATMENT_COL


def validate_columns(df: pd.DataFrame, target_col: str) -> None:
    required_cols = FEATURE_COLS + [TREATMENT_COL, target_col]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")


def validate_binary_column(df: pd.DataFrame, col: str) -> None:
    values = set(df[col].dropna().unique())

    if not values.issubset({0, 1}):
        raise ValueError(f"Column '{col}' must be binary 0/1. Found values: {sorted(values)}")


def validate_no_empty_dataframe(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Input dataframe is empty.")


def validate_schema(df: pd.DataFrame, target_col: str) -> None:
    validate_no_empty_dataframe(df)
    validate_columns(df, target_col=target_col)
    validate_binary_column(df, TREATMENT_COL)
    validate_binary_column(df, target_col)


def resolve_target_column(
    df: pd.DataFrame,
    primary_target: str = "conversion",
    fallback_target: str = "visit",
) -> str:
    if primary_target in df.columns:
        return primary_target

    if fallback_target in df.columns:
        return fallback_target

    raise ValueError(
        f"Neither primary target '{primary_target}' nor fallback target "
        f"'{fallback_target}' exists in dataframe."
    )