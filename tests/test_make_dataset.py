import pandas as pd

from src.data.constants import FEATURE_COLS, TREATMENT_COL
from src.data.make_dataset import load_raw_sample_from_full_file


def test_load_raw_sample_reads_across_entire_sorted_file(tmp_path):
    rows = []

    for i in range(6):
        row = {feature: float(i) for feature in FEATURE_COLS}
        row[TREATMENT_COL] = 1
        row["conversion"] = i % 2
        rows.append(row)

    for i in range(4):
        row = {feature: float(i) for feature in FEATURE_COLS}
        row[TREATMENT_COL] = 0
        row["conversion"] = i % 2
        rows.append(row)

    raw_path = tmp_path / "sorted_criteo.csv"
    pd.DataFrame(rows).to_csv(raw_path, index=False)

    sample_df, target_col, raw_counts = load_raw_sample_from_full_file(
        raw_path=raw_path,
        sample_size=10,
        chunk_size=3,
    )

    assert target_col == "conversion"
    assert raw_counts[1] == 6
    assert raw_counts[0] == 4
    assert set(sample_df[TREATMENT_COL].unique()) == {0, 1}