import pandas as pd
import pytest

from src.data.constants import FEATURE_COLS, TREATMENT_COL
from src.models.train_uplift_model import (
    assert_target_has_positive_and_negative_examples,
    assert_treatment_control_present,
)


def make_valid_uplift_df() -> pd.DataFrame:
    data = {feature: [0.1, 0.2, 0.3, 0.4] for feature in FEATURE_COLS}
    data[TREATMENT_COL] = [1, 1, 0, 0]
    data["conversion"] = [1, 0, 1, 0]

    return pd.DataFrame(data)


def test_assert_treatment_control_present_passes_when_both_groups_exist():
    df = make_valid_uplift_df()

    assert_treatment_control_present(df, dataset_name="test_df")


def test_assert_treatment_control_present_raises_when_control_missing():
    df = make_valid_uplift_df()
    df[TREATMENT_COL] = 1

    with pytest.raises(ValueError, match="must contain both treatment=1 and control=0"):
        assert_treatment_control_present(df, dataset_name="test_df")


def test_assert_target_has_positive_and_negative_examples_passes():
    df = make_valid_uplift_df()

    assert_target_has_positive_and_negative_examples(
        df=df,
        target_col="conversion",
        dataset_name="test_df",
    )


def test_assert_target_has_positive_and_negative_examples_raises_when_single_class():
    df = make_valid_uplift_df()
    df["conversion"] = 0

    with pytest.raises(ValueError, match="must contain both positive and negative"):
        assert_target_has_positive_and_negative_examples(
            df=df,
            target_col="conversion",
            dataset_name="test_df",
        )