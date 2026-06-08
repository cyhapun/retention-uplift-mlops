import pandas as pd

from src.data.constants import FEATURE_COLS
from src.monitoring.drift_report import calculate_simple_drift_summary


def test_calculate_simple_drift_summary_detects_shifted_features():
    reference_df = pd.DataFrame({feature: [0.0, 0.0, 0.0, 0.0, 1.0] for feature in FEATURE_COLS})
    current_df = reference_df.copy()
    current_df["f0"] = current_df["f0"] + 10.0

    summary = calculate_simple_drift_summary(
        reference_df=reference_df,
        current_df=current_df,
        mean_shift_threshold=0.1,
    )

    assert "f0" in summary["drifted_features"]
    assert summary["n_drifted_features"] >= 1
