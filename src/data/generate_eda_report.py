from pathlib import Path

import pandas as pd

from src.data.eda import (
    conversion_by_treatment,
    dataset_overview,
    feature_skewness,
    feature_summary,
    get_target_column,
    save_feature_histograms,
    target_distribution,
    treatment_distribution,
)

TRAIN_PATH = Path("data/processed/train.parquet")
REPORT_DIR = Path("reports/eda")
FIGURE_DIR = REPORT_DIR / "figures"


def save_report_table(df: pd.DataFrame, filename: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = REPORT_DIR / f"{filename}.csv"
    markdown_path = REPORT_DIR / f"{filename}.md"

    df.to_csv(csv_path, index=False)
    markdown_path.write_text(df.to_markdown(index=False), encoding="utf-8")

    print(f"Saved {csv_path}")
    print(f"Saved {markdown_path}")


def main() -> None:
    if not TRAIN_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found at {TRAIN_PATH}. "
            "Run Phase 1 data pipeline before generating EDA report."
        )

    train_df = pd.read_parquet(TRAIN_PATH)
    target_col = get_target_column(train_df)

    overview = dataset_overview(train_df, target_col)
    treatment_report = treatment_distribution(train_df)
    target_report = target_distribution(train_df, target_col)
    treatment_conversion_report = conversion_by_treatment(train_df, target_col)
    features_report = feature_summary(train_df)
    skewness_report = feature_skewness(train_df)

    save_report_table(overview, "dataset_overview")
    save_report_table(treatment_report, "treatment_distribution")
    save_report_table(target_report, "target_distribution")
    save_report_table(treatment_conversion_report, "conversion_by_treatment")
    save_report_table(features_report, "feature_summary")
    save_report_table(skewness_report, "feature_skewness")

    save_feature_histograms(train_df, FIGURE_DIR)

    print("EDA report generated successfully.")
    print(f"Target column: {target_col}")
    print(f"Report directory: {REPORT_DIR}")


if __name__ == "__main__":
    main()