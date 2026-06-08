from pathlib import Path

import pandas as pd

from src.data.constants import FEATURE_COLS

DEFAULT_INPUT_PATH = Path("data/processed/test.parquet")
DEFAULT_OUTPUT_PATH = Path("data/processed/test_drifted.parquet")


def simulate_feature_drift(df: pd.DataFrame) -> pd.DataFrame:
    drifted_df = df.copy()

    # Create obvious numerical distribution shifts.
    drifted_df["f0"] = drifted_df["f0"] * 1.5
    drifted_df["f3"] = drifted_df["f3"] + 0.2
    drifted_df["f7"] = drifted_df["f7"] * 0.7

    return drifted_df


def create_drifted_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset not found at {input_path}")

    df = pd.read_parquet(input_path)

    missing_features = [feature for feature in FEATURE_COLS if feature not in df.columns]
    if missing_features:
        raise ValueError(f"Missing feature columns: {missing_features}")

    drifted_df = simulate_feature_drift(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    drifted_df.to_parquet(output_path, index=False)

    print(f"Saved drifted dataset to {output_path}")

    return output_path


def main() -> None:
    create_drifted_dataset()


if __name__ == "__main__":
    main()
