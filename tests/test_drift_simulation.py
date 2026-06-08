import pandas as pd

from src.data.constants import FEATURE_COLS
from src.monitoring.simulate_drift import simulate_feature_drift


def test_simulate_feature_drift_changes_expected_features():
    df = pd.DataFrame(
        {
            feature: [1.0, 2.0, 3.0]
            for feature in FEATURE_COLS
        }
    )

    drifted_df = simulate_feature_drift(df)

    assert drifted_df["f0"].tolist() == [1.5, 3.0, 4.5]
    assert drifted_df["f3"].tolist() == [1.2, 2.2, 3.2]
    assert drifted_df["f7"].tolist() == [0.7, 1.4, 2.1]