import pandas as pd
import pytest

from src.data.constants import FEATURE_COLS, TREATMENT_COL
from src.data.validate_schema import resolve_target_column, validate_schema


def make_valid_df() -> pd.DataFrame:
    data = {col: [0.1, 0.2, 0.3] for col in FEATURE_COLS}
    data[TREATMENT_COL] = [0, 1, 1]
    data["conversion"] = [0, 1, 0]
    return pd.DataFrame(data)


def test_validate_schema_passes_for_valid_dataframe():
    df = make_valid_df()

    validate_schema(df, target_col="conversion")


def test_validate_schema_raises_when_required_column_missing():
    df = make_valid_df().drop(columns=["f0"])

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_schema(df, target_col="conversion")


def test_validate_schema_raises_when_treatment_is_not_binary():
    df = make_valid_df()
    df[TREATMENT_COL] = [0, 1, 2]

    with pytest.raises(ValueError, match="must be binary"):
        validate_schema(df, target_col="conversion")


def test_resolve_target_column_uses_conversion_when_available():
    df = make_valid_df()

    target_col = resolve_target_column(df)

    assert target_col == "conversion"


def test_resolve_target_column_falls_back_to_visit():
    df = make_valid_df().drop(columns=["conversion"])
    df["visit"] = [0, 1, 1]

    target_col = resolve_target_column(df)

    assert target_col == "visit"


def test_resolve_target_column_raises_when_no_target_exists():
    df = make_valid_df().drop(columns=["conversion"])

    with pytest.raises(ValueError, match="Neither primary target"):
        resolve_target_column(df)
