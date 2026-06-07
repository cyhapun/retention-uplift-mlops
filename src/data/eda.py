from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.data.constants import FEATURE_COLS, TREATMENT_COL


def get_target_column(df: pd.DataFrame) -> str:
    if "conversion" in df.columns:
        return "conversion"

    if "visit" in df.columns:
        return "visit"

    raise ValueError("Expected either 'conversion' or 'visit' target column.")


def dataset_overview(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "n_rows": len(df),
                "n_columns": df.shape[1],
                "target_col": target_col,
                "treatment_rate": df[TREATMENT_COL].mean(),
                "target_rate": df[target_col].mean(),
                "missing_values": int(df.isna().sum().sum()),
                "duplicate_rows": int(df.duplicated().sum()),
            }
        ]
    )


def treatment_distribution(df: pd.DataFrame) -> pd.DataFrame:
    report = (
        df[TREATMENT_COL]
        .value_counts(dropna=False)
        .rename_axis("treatment")
        .reset_index(name="n_users")
    )
    report["share"] = report["n_users"] / report["n_users"].sum()
    report["group"] = report["treatment"].map({0: "control", 1: "treatment"})
    return report[["group", "treatment", "n_users", "share"]]


def target_distribution(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    report = (
        df[target_col]
        .value_counts(dropna=False)
        .rename_axis(target_col)
        .reset_index(name="n_users")
    )
    report["share"] = report["n_users"] / report["n_users"].sum()
    return report[[target_col, "n_users", "share"]]


def conversion_by_treatment(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    report = (
        df.groupby(TREATMENT_COL)
        .agg(
            n_users=(target_col, "size"),
            conversion_rate=(target_col, "mean"),
        )
        .reset_index()
    )
    report["group"] = report[TREATMENT_COL].map({0: "control", 1: "treatment"})
    report = report[["group", TREATMENT_COL, "n_users", "conversion_rate"]]

    control_rate = report.loc[report[TREATMENT_COL] == 0, "conversion_rate"]
    treatment_rate = report.loc[report[TREATMENT_COL] == 1, "conversion_rate"]

    if not control_rate.empty and not treatment_rate.empty:
        difference = float(treatment_rate.iloc[0] - control_rate.iloc[0])
    else:
        difference = float("nan")

    diff_row = pd.DataFrame(
        [
            {
                "group": "difference",
                TREATMENT_COL: None,
                "n_users": None,
                "conversion_rate": difference,
            }
        ]
    )

    return pd.concat([report, diff_row], ignore_index=True)


def feature_summary(df: pd.DataFrame) -> pd.DataFrame:
    return df[FEATURE_COLS].describe().T.reset_index(names="feature")


def feature_skewness(df: pd.DataFrame) -> pd.DataFrame:
    report = df[FEATURE_COLS].skew(numeric_only=True).reset_index()
    report.columns = ["feature", "skewness"]
    report["abs_skewness"] = report["skewness"].abs()
    return report.sort_values("abs_skewness", ascending=False)


def save_feature_histograms(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for feature in FEATURE_COLS:
        plt.figure()
        df[feature].hist(bins=50)
        plt.title(f"Distribution of {feature}")
        plt.xlabel(feature)
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(output_dir / f"{feature}_hist.png")
        plt.close()