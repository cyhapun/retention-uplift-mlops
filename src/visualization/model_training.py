from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.data.constants import FEATURE_COLS, TREATMENT_COL


def summarize_dataset(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "n_rows": len(df),
                "n_features": len(FEATURE_COLS),
                "target_col": target_col,
                "target_rate": float(df[target_col].mean()),
                "treatment_rate": float(df[TREATMENT_COL].mean()),
                "n_treatment": int((df[TREATMENT_COL] == 1).sum()),
                "n_control": int((df[TREATMENT_COL] == 0).sum()),
            }
        ]
    )


def treatment_outcome_summary(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    return (
        df.groupby(TREATMENT_COL, observed=True)[target_col]
        .agg(["count", "mean"])
        .rename(columns={"count": "n_users", "mean": "outcome_rate"})
        .reset_index()
    )


def feature_summary(df: pd.DataFrame) -> pd.DataFrame:
    return df[FEATURE_COLS].describe().T.reset_index().rename(columns={"index": "feature"})


def plot_treatment_outcome_summary(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(
        summary_df[TREATMENT_COL].astype(str),
        summary_df["outcome_rate"],
    )
    ax.set_title("Outcome rate by treatment group")
    ax.set_xlabel("Treatment group")
    ax.set_ylabel("Outcome rate")
    plt.show()


def plot_feature_histograms(df: pd.DataFrame, max_features: int = 6) -> None:
    features = FEATURE_COLS[:max_features]

    for feature in features:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(df[feature].dropna(), bins=40)
        ax.set_title(f"Distribution of {feature}")
        ax.set_xlabel(feature)
        ax.set_ylabel("Count")
        plt.show()


def load_uplift_predictions(
    path: str | Path = "reports/uplift/valid_uplift_predictions.parquet",
) -> pd.DataFrame:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Uplift predictions not found at {path}. "
            "Run the uplift training pipeline first."
        )

    return pd.read_parquet(path)


def load_uplift_decile_report(
    path: str | Path = "reports/uplift/uplift_decile_report.csv",
) -> pd.DataFrame:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Uplift decile report not found at {path}. "
            "Run the uplift training pipeline first."
        )

    return pd.read_csv(path)


def load_qini_curve(
    path: str | Path = "reports/uplift/qini_curve.csv",
) -> pd.DataFrame:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Qini curve not found at {path}. "
            "Run the uplift training pipeline first."
        )

    return pd.read_csv(path)


def plot_uplift_distribution(scored_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(scored_df["uplift_score"].dropna(), bins=40)
    ax.set_title("Predicted uplift score distribution")
    ax.set_xlabel("Uplift score")
    ax.set_ylabel("Count")
    plt.show()


def plot_uplift_decile_report(decile_report: pd.DataFrame) -> None:
    y_col = "observed_uplift" if "observed_uplift" in decile_report.columns else "avg_uplift_score"

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(
        decile_report["uplift_decile"].astype(str),
        decile_report[y_col],
    )
    ax.set_title(f"{y_col} by predicted uplift decile")
    ax.set_xlabel("Uplift decile")
    ax.set_ylabel(y_col)
    plt.show()


def plot_qini_curve(qini_curve: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))

    if "population_fraction" in qini_curve.columns and "qini_gain" in qini_curve.columns:
        ax.plot(
            qini_curve["population_fraction"],
            qini_curve["qini_gain"],
            label="Model",
        )

    if "population_fraction" in qini_curve.columns and "random_gain" in qini_curve.columns:
        ax.plot(
            qini_curve["population_fraction"],
            qini_curve["random_gain"],
            label="Random",
        )

    ax.set_title("Qini curve")
    ax.set_xlabel("Population fraction")
    ax.set_ylabel("Qini gain")
    ax.legend()
    plt.show()