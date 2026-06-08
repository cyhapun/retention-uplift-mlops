import numpy as np
import pandas as pd
import pytest

from src.data.constants import FEATURE_COLS
from src.models.uplift_wrapper import validate_model_input


def test_validate_model_input_keeps_feature_columns_in_order():
    df = pd.DataFrame(
        [
            {
                **{feature: 0.1 for feature in FEATURE_COLS},
                "extra_col": 999,
            }
        ]
    )

    result = validate_model_input(df)

    assert list(result.columns) == FEATURE_COLS


def test_validate_model_input_raises_when_feature_missing():
    df = pd.DataFrame([{feature: 0.1 for feature in FEATURE_COLS}])
    df = df.drop(columns=["f0"])

    with pytest.raises(ValueError, match="Missing required features"):
        validate_model_input(df)


def test_validate_model_input_raises_for_non_dataframe():
    with pytest.raises(TypeError, match="model_input must be a pandas DataFrame"):
        validate_model_input(np.array([[1, 2, 3]]))
