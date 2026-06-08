import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.constants import FEATURE_COLS
from src.monitoring.retrain_check import should_retrain

REFERENCE_PATH = Path("data/reference/reference.parquet")
CURRENT_PATH = Path("data/processed/test.parquet")
DRIFTED_PATH = Path("data/processed/test_drifted.parquet")
REPORT_DIR = Path("reports/drift")


def load_feature_data(path: str | Path, sample_size: int | None = 100_000) -> pd.DataFrame:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")

    df = pd.read_parquet(path)

    missing_features = [feature for feature in FEATURE_COLS if feature not in df.columns]
    if missing_features:
        raise ValueError(f"Missing feature columns: {missing_features}")

    feature_df = df[FEATURE_COLS].copy()

    if sample_size is not None and len(feature_df) > sample_size:
        feature_df = feature_df.sample(n=sample_size, random_state=42)

    return feature_df.reset_index(drop=True)


def calculate_simple_drift_summary(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    mean_shift_threshold: float = 0.1,
) -> dict[str, Any]:
    rows = []

    for feature in FEATURE_COLS:
        reference_mean = float(reference_df[feature].mean())
        current_mean = float(current_df[feature].mean())
        reference_std = float(reference_df[feature].std())

        if reference_std == 0 or pd.isna(reference_std):
            normalized_mean_shift = 0.0
        else:
            normalized_mean_shift = abs(current_mean - reference_mean) / reference_std

        is_drifted = normalized_mean_shift > mean_shift_threshold

        rows.append(
            {
                "feature": feature,
                "reference_mean": reference_mean,
                "current_mean": current_mean,
                "reference_std": reference_std,
                "normalized_mean_shift": normalized_mean_shift,
                "is_drifted": is_drifted,
            }
        )

    drift_by_feature = pd.DataFrame(rows)
    drifted_features = drift_by_feature.loc[
        drift_by_feature["is_drifted"], "feature"
    ].tolist()

    drifted_feature_share = len(drifted_features) / len(FEATURE_COLS)
    dataset_drift_detected = drifted_feature_share >= 0.3

    return {
        "dataset_drift_detected": dataset_drift_detected,
        "n_features": len(FEATURE_COLS),
        "n_drifted_features": len(drifted_features),
        "drifted_feature_share": drifted_feature_share,
        "drifted_features": drifted_features,
        "drift_by_feature": drift_by_feature,
    }


def run_evidently_report(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
):
    try:
        from evidently import DataDefinition, Dataset, Report
        from evidently.presets import DataDriftPreset

        schema = DataDefinition(numerical_columns=FEATURE_COLS)

        current_dataset = Dataset.from_pandas(
            current_df,
            data_definition=schema,
        )
        reference_dataset = Dataset.from_pandas(
            reference_df,
            data_definition=schema,
        )

        report = Report([DataDriftPreset()])
        return report.run(
            current_data=current_dataset,
            reference_data=reference_dataset,
        )

    except ImportError:
        from evidently import Report
        from evidently.presets import DataDriftPreset

        report = Report([DataDriftPreset()])
        return report.run(
            current_data=current_df,
            reference_data=reference_df,
        )


def save_evidently_outputs(evaluation, report_stem: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{report_stem}.json"
    html_path = output_dir / f"{report_stem}.html"

    if hasattr(evaluation, "json"):
        json_content = evaluation.json()
        if isinstance(json_content, str):
            json_path.write_text(json_content, encoding="utf-8")
        else:
            json_path.write_text(json.dumps(json_content, indent=2), encoding="utf-8")

    if hasattr(evaluation, "save_html"):
        evaluation.save_html(str(html_path))
    elif hasattr(evaluation, "save"):
        try:
            evaluation.save(str(html_path))
        except TypeError:
            pass

    print(f"Saved Evidently JSON to {json_path}")

    if html_path.exists():
        print(f"Saved Evidently HTML to {html_path}")
    else:
        print("HTML export was not available for this Evidently version.")


def run_drift_detection(
    reference_path: str | Path = REFERENCE_PATH,
    current_path: str | Path = CURRENT_PATH,
    report_name: str = "data_drift_report",
    sample_size: int | None = 100_000,
    output_dir: str | Path = REPORT_DIR,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reference_df = load_feature_data(reference_path, sample_size=sample_size)
    current_df = load_feature_data(current_path, sample_size=sample_size)

    evaluation = run_evidently_report(
        reference_df=reference_df,
        current_df=current_df,
    )

    save_evidently_outputs(
        evaluation=evaluation,
        report_stem=report_name,
        output_dir=output_dir,
    )

    summary = calculate_simple_drift_summary(
        reference_df=reference_df,
        current_df=current_df,
    )

    retrain_decision = should_retrain(
        drift_detected=summary["dataset_drift_detected"],
        drifted_feature_share=summary["drifted_feature_share"],
    )

    summary_output = {
        "report_name": report_name,
        "reference_path": str(reference_path),
        "current_path": str(current_path),
        "dataset_drift_detected": summary["dataset_drift_detected"],
        "n_features": summary["n_features"],
        "n_drifted_features": summary["n_drifted_features"],
        "drifted_feature_share": summary["drifted_feature_share"],
        "drifted_features": summary["drifted_features"],
        "should_retrain": retrain_decision.should_retrain,
        "retrain_reasons": retrain_decision.reasons,
    }

    summary_path = output_dir / f"{report_name}_summary.json"
    feature_path = output_dir / f"{report_name}_features.csv"

    summary_path.write_text(
        json.dumps(summary_output, indent=2),
        encoding="utf-8",
    )
    summary["drift_by_feature"].to_csv(feature_path, index=False)

    print(f"Saved drift summary to {summary_path}")
    print(f"Saved feature drift table to {feature_path}")
    print(f"Should retrain: {retrain_decision.should_retrain}")
    print(f"Retrain reasons: {retrain_decision.reasons}")

    return summary_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run data drift detection.")

    parser.add_argument(
        "--reference-path",
        type=str,
        default=str(REFERENCE_PATH),
    )
    parser.add_argument(
        "--current-path",
        type=str,
        default=str(CURRENT_PATH),
    )
    parser.add_argument(
        "--report-name",
        type=str,
        default="data_drift_report",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100_000,
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(REPORT_DIR),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_drift_detection(
        reference_path=args.reference_path,
        current_path=args.current_path,
        report_name=args.report_name,
        sample_size=args.sample_size,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()