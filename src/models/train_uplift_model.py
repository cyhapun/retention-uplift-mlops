import argparse
import pickle
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from xgboost import XGBClassifier

from src.data.constants import FEATURE_COLS, PROCESSED_DIR, RANDOM_STATE, TREATMENT_COL
from src.data.validate_schema import resolve_target_column, validate_schema
from src.models.evaluation import evaluate_binary_classifier
from src.models.uplift_metrics import (
    compute_uplift_predictions,
    qini_curve,
    uplift_decile_report,
    uplift_summary_metrics,
)

MODEL_DIR = Path("artifacts/uplift")
REPORT_DIR = Path("reports/uplift")

TREATMENT_MODEL_PATH = MODEL_DIR / "treatment_model.pkl"
CONTROL_MODEL_PATH = MODEL_DIR / "control_model.pkl"

VALID_PREDICTIONS_PATH = REPORT_DIR / "valid_uplift_predictions.parquet"
DECILE_REPORT_PATH = REPORT_DIR / "uplift_decile_report.csv"
QINI_CURVE_PATH = REPORT_DIR / "qini_curve.csv"


def assert_treatment_control_present(df: pd.DataFrame, dataset_name: str) -> None:
    treatment_values = set(df[TREATMENT_COL].dropna().unique())

    if not {0, 1}.issubset(treatment_values):
        raise ValueError(
            f"{dataset_name} must contain both treatment=1 and control=0. "
            f"Found treatment values: {sorted(treatment_values)}"
        )


def assert_target_has_positive_and_negative_examples(
    df: pd.DataFrame,
    target_col: str,
    dataset_name: str,
) -> None:
    target_values = set(df[target_col].dropna().unique())

    if not {0, 1}.issubset(target_values):
        raise ValueError(
            f"{dataset_name} must contain both positive and negative target examples. "
            f"Found {target_col} values: {sorted(target_values)}"
        )


def calculate_scale_pos_weight(y: pd.Series) -> float:
    n_positive = int((y == 1).sum())
    n_negative = int((y == 0).sum())

    if n_positive == 0:
        return 1.0

    return n_negative / n_positive


def build_xgboost_model(y_train: pd.Series) -> XGBClassifier:
    scale_pos_weight = calculate_scale_pos_weight(y_train)

    return XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def train_binary_outcome_model(df: pd.DataFrame, target_col: str) -> XGBClassifier:
    x_train = df[FEATURE_COLS]
    y_train = df[target_col]

    assert_target_has_positive_and_negative_examples(
        df=df,
        target_col=target_col,
        dataset_name="binary outcome training data",
    )

    model = build_xgboost_model(y_train)
    model.fit(x_train, y_train)

    return model


def load_train_valid_data() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    train_path = PROCESSED_DIR / "train.parquet"
    valid_path = PROCESSED_DIR / "valid.parquet"

    if not train_path.exists():
        raise FileNotFoundError(
            f"Training data not found at {train_path}. Run the Phase 1 data pipeline first."
        )

    if not valid_path.exists():
        raise FileNotFoundError(
            f"Validation data not found at {valid_path}. Run the Phase 1 data pipeline first."
        )

    train_df = pd.read_parquet(train_path)
    valid_df = pd.read_parquet(valid_path)

    target_col = resolve_target_column(train_df)

    validate_schema(train_df, target_col=target_col)
    validate_schema(valid_df, target_col=target_col)

    assert_treatment_control_present(train_df, dataset_name="train_df")
    assert_treatment_control_present(valid_df, dataset_name="valid_df")

    return train_df, valid_df, target_col


def save_pickle(model, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as f:
        pickle.dump(model, f)


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)


def train_uplift_model(experiment_name: str = "uplift_model") -> dict[str, object]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    train_df, valid_df, target_col = load_train_valid_data()

    treatment_train_df = train_df[train_df[TREATMENT_COL] == 1].copy()
    control_train_df = train_df[train_df[TREATMENT_COL] == 0].copy()

    treatment_valid_df = valid_df[valid_df[TREATMENT_COL] == 1].copy()
    control_valid_df = valid_df[valid_df[TREATMENT_COL] == 0].copy()

    print("Training T-Learner uplift model")
    print(f"Target column: {target_col}")
    print(f"Train rows: {len(train_df):,}")
    print(f"Valid rows: {len(valid_df):,}")
    print(f"Treatment train rows: {len(treatment_train_df):,}")
    print(f"Control train rows: {len(control_train_df):,}")
    print(f"Treatment target rate: {treatment_train_df[target_col].mean():.6f}")
    print(f"Control target rate: {control_train_df[target_col].mean():.6f}")

    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="t_learner_xgboost"):
        treatment_model = train_binary_outcome_model(
            df=treatment_train_df,
            target_col=target_col,
        )
        control_model = train_binary_outcome_model(
            df=control_train_df,
            target_col=target_col,
        )

        treatment_metrics = evaluate_binary_classifier(
            treatment_model,
            treatment_valid_df[FEATURE_COLS],
            treatment_valid_df[target_col],
        )
        control_metrics = evaluate_binary_classifier(
            control_model,
            control_valid_df[FEATURE_COLS],
            control_valid_df[target_col],
        )

        prediction_df = compute_uplift_predictions(
            treatment_model=treatment_model,
            control_model=control_model,
            x=valid_df[FEATURE_COLS],
        )

        scored_valid_df = pd.concat(
            [
                valid_df.reset_index(drop=True),
                prediction_df.reset_index(drop=True),
            ],
            axis=1,
        )

        decile_report = uplift_decile_report(
            scored_df=scored_valid_df,
            target_col=target_col,
        )
        qini_report = qini_curve(
            scored_df=scored_valid_df,
            target_col=target_col,
        )
        uplift_metrics = uplift_summary_metrics(
            scored_df=scored_valid_df,
            target_col=target_col,
        )

        save_pickle(treatment_model, TREATMENT_MODEL_PATH)
        save_pickle(control_model, CONTROL_MODEL_PATH)
        save_dataframe(scored_valid_df, VALID_PREDICTIONS_PATH)
        save_dataframe(decile_report, DECILE_REPORT_PATH)
        save_dataframe(qini_report, QINI_CURVE_PATH)

        mlflow.log_param("learner_type", "T-Learner")
        mlflow.log_param("base_model", "XGBoost")
        mlflow.log_param("target_col", target_col)
        mlflow.log_param("n_features", len(FEATURE_COLS))
        mlflow.log_param("train_rows", len(train_df))
        mlflow.log_param("valid_rows", len(valid_df))
        mlflow.log_param("treatment_train_rows", len(treatment_train_df))
        mlflow.log_param("control_train_rows", len(control_train_df))

        mlflow.log_metric("treatment_train_target_rate", float(treatment_train_df[target_col].mean()))
        mlflow.log_metric("control_train_target_rate", float(control_train_df[target_col].mean()))
        mlflow.log_metric("valid_treatment_rate", float(valid_df[TREATMENT_COL].mean()))

        for metric_name, metric_value in treatment_metrics.items():
            mlflow.log_metric(f"treatment_model_{metric_name}", metric_value)

        for metric_name, metric_value in control_metrics.items():
            mlflow.log_metric(f"control_model_{metric_name}", metric_value)

        mlflow.log_metrics(uplift_metrics)

        mlflow.sklearn.log_model(treatment_model, artifact_path="treatment_model")
        mlflow.sklearn.log_model(control_model, artifact_path="control_model")

        mlflow.log_artifact(str(TREATMENT_MODEL_PATH))
        mlflow.log_artifact(str(CONTROL_MODEL_PATH))
        mlflow.log_artifact(str(DECILE_REPORT_PATH))
        mlflow.log_artifact(str(QINI_CURVE_PATH))

        print("\nTreatment model metrics:")
        for metric_name, metric_value in treatment_metrics.items():
            print(f"- {metric_name}: {metric_value}")

        print("\nControl model metrics:")
        for metric_name, metric_value in control_metrics.items():
            print(f"- {metric_name}: {metric_value}")

        print("\nUplift metrics:")
        for metric_name, metric_value in uplift_metrics.items():
            print(f"- {metric_name}: {metric_value}")

        print("\nSaved uplift artifacts:")
        print(f"- {TREATMENT_MODEL_PATH}")
        print(f"- {CONTROL_MODEL_PATH}")
        print(f"- {VALID_PREDICTIONS_PATH}")
        print(f"- {DECILE_REPORT_PATH}")
        print(f"- {QINI_CURVE_PATH}")

        return {
            "target_col": target_col,
            "treatment_metrics": treatment_metrics,
            "control_metrics": control_metrics,
            "uplift_metrics": uplift_metrics,
            "treatment_model_path": str(TREATMENT_MODEL_PATH),
            "control_model_path": str(CONTROL_MODEL_PATH),
            "decile_report_path": str(DECILE_REPORT_PATH),
            "qini_curve_path": str(QINI_CURVE_PATH),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train T-Learner uplift model.")

    parser.add_argument(
        "--experiment-name",
        type=str,
        default="uplift_model",
        help="MLflow experiment name.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_uplift_model(experiment_name=args.experiment_name)


if __name__ == "__main__":
    main()