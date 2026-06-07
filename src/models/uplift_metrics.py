import math
from typing import Any

import numpy as np
import pandas as pd

from src.data.constants import TREATMENT_COL


def compute_uplift_predictions(
    treatment_model: Any,
    control_model: Any,
    x: pd.DataFrame,
) -> pd.DataFrame:
    treatment_probability = treatment_model.predict_proba(x)[:, 1]
    control_probability = control_model.predict_proba(x)[:, 1]
    uplift_score = treatment_probability - control_probability

    return pd.DataFrame(
        {
            "treatment_probability": treatment_probability,
            "control_probability": control_probability,
            "uplift_score": uplift_score,
        },
        index=x.index,
    )


def uplift_decile_report(
    scored_df: pd.DataFrame,
    target_col: str,
    uplift_col: str = "uplift_score",
    n_bins: int = 10,
) -> pd.DataFrame:
    df = scored_df.copy()

    if uplift_col not in df.columns:
        raise ValueError(f"Missing uplift column: {uplift_col}")

    if target_col not in df.columns:
        raise ValueError(f"Missing target column: {target_col}")

    ranked_score = df[uplift_col].rank(method="first")
    df["uplift_decile"] = pd.qcut(
        ranked_score,
        q=n_bins,
        labels=False,
        duplicates="drop",
    )

    def bucket_stats(group: pd.DataFrame) -> pd.Series:
        treatment_mask = group[TREATMENT_COL] == 1
        control_mask = group[TREATMENT_COL] == 0

        n_treatment = int(treatment_mask.sum())
        n_control = int(control_mask.sum())

        treatment_rate = (
            group.loc[treatment_mask, target_col].mean() if n_treatment > 0 else math.nan
        )
        control_rate = group.loc[control_mask, target_col].mean() if n_control > 0 else math.nan

        observed_uplift = (
            treatment_rate - control_rate
            if not math.isnan(treatment_rate) and not math.isnan(control_rate)
            else math.nan
        )

        return pd.Series(
            {
                "n_users": len(group),
                "n_treatment": n_treatment,
                "n_control": n_control,
                "treatment_rate": treatment_rate,
                "control_rate": control_rate,
                "observed_uplift": observed_uplift,
                "avg_predicted_uplift": group[uplift_col].mean(),
                "min_predicted_uplift": group[uplift_col].min(),
                "max_predicted_uplift": group[uplift_col].max(),
            }
        )

    report = df.groupby("uplift_decile", observed=True).apply(bucket_stats).reset_index()

    return report.sort_values("uplift_decile", ascending=False).reset_index(drop=True)


def qini_curve(
    scored_df: pd.DataFrame,
    target_col: str,
    uplift_col: str = "uplift_score",
    n_points: int = 100,
) -> pd.DataFrame:
    required_cols = {TREATMENT_COL, target_col, uplift_col}
    missing_cols = required_cols - set(scored_df.columns)

    if missing_cols:
        raise ValueError(f"Missing required columns for Qini curve: {sorted(missing_cols)}")

    df = scored_df.sort_values(uplift_col, ascending=False).reset_index(drop=True)
    n_rows = len(df)

    if n_rows == 0:
        raise ValueError("Cannot compute Qini curve on empty dataframe.")

    treatment = df[TREATMENT_COL].to_numpy()
    outcome = df[target_col].to_numpy()

    cumulative_treatment = np.cumsum(treatment == 1)
    cumulative_control = np.cumsum(treatment == 0)

    cumulative_treatment_outcome = np.cumsum((treatment == 1) * outcome)
    cumulative_control_outcome = np.cumsum((treatment == 0) * outcome)

    total_treatment = cumulative_treatment[-1]
    total_control = cumulative_control[-1]
    total_treatment_outcome = cumulative_treatment_outcome[-1]
    total_control_outcome = cumulative_control_outcome[-1]

    if total_treatment == 0 or total_control == 0:
        raise ValueError("Qini curve requires both treatment and control groups.")

    total_incremental_gain = total_treatment_outcome - (
        total_control_outcome * total_treatment / total_control
    )

    indexes = np.unique(
        np.clip(
            np.round(np.linspace(1, n_rows, n_points)).astype(int) - 1,
            0,
            n_rows - 1,
        )
    )

    rows = []

    for idx in indexes:
        n_selected = idx + 1
        n_treatment = cumulative_treatment[idx]
        n_control = cumulative_control[idx]
        treatment_outcome = cumulative_treatment_outcome[idx]
        control_outcome = cumulative_control_outcome[idx]

        if n_control == 0:
            qini_gain_value = math.nan
        else:
            qini_gain_value = treatment_outcome - control_outcome * n_treatment / n_control

        population_fraction = n_selected / n_rows
        random_gain = total_incremental_gain * population_fraction

        rows.append(
            {
                "n_selected": n_selected,
                "population_fraction": population_fraction,
                "n_treatment": int(n_treatment),
                "n_control": int(n_control),
                "treatment_outcome": float(treatment_outcome),
                "control_outcome": float(control_outcome),
                "qini_gain": float(qini_gain_value),
                "random_gain": float(random_gain),
            }
        )

    return pd.DataFrame(rows)


def area_under_curve(curve_df: pd.DataFrame, x_col: str, y_col: str) -> float:
    valid_curve = curve_df[[x_col, y_col]].replace([np.inf, -np.inf], np.nan).dropna()

    if len(valid_curve) < 2:
        return math.nan

    return float(np.trapz(valid_curve[y_col], valid_curve[x_col]))


def uplift_summary_metrics(
    scored_df: pd.DataFrame,
    target_col: str,
    uplift_col: str = "uplift_score",
) -> dict[str, float]:
    curve = qini_curve(scored_df, target_col=target_col, uplift_col=uplift_col)

    qini_auc = area_under_curve(curve, x_col="population_fraction", y_col="qini_gain")
    random_auc = area_under_curve(curve, x_col="population_fraction", y_col="random_gain")

    decile_report = uplift_decile_report(
        scored_df=scored_df,
        target_col=target_col,
        uplift_col=uplift_col,
    )

    top_decile = decile_report.iloc[0]

    return {
        "mean_predicted_uplift": float(scored_df[uplift_col].mean()),
        "median_predicted_uplift": float(scored_df[uplift_col].median()),
        "share_positive_uplift": float((scored_df[uplift_col] > 0).mean()),
        "qini_auc": qini_auc,
        "random_qini_auc": random_auc,
        "incremental_qini_auc": qini_auc - random_auc,
        "top_decile_observed_uplift": float(top_decile["observed_uplift"]),
        "top_decile_avg_predicted_uplift": float(top_decile["avg_predicted_uplift"]),
    }