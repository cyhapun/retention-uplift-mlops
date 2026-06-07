import argparse
import pickle
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.data.constants import FEATURE_COLS, PROCESSED_DIR, RANDOM_STATE
from src.data.validate_schema import resolve_target_column, validate_schema
from src.models.evaluation import evaluate_binary_classifier

ARTIFACT_DIR = Path("artifacts")
MODEL_OUTPUT_PATH = ARTIFACT_DIR / "response_model.pkl"


def calculate_scale_pos_weight(y: pd.Series) -> float:
    n_positive = int((y == 1).sum())
    n_negative = int((y == 0).sum())

    if n_positive == 0:
        return 1.0

    return n_negative / n_positive


def build_candidate_models(y_train: pd.Series) -> dict[str, object]:
    scale_pos_weight = calculate_scale_pos_weight(y_train)

    return {
        "logistic_regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=20,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


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

    return train_df, valid_df, target_col


def train_response_models(experiment_name: str = "response_model") -> dict[str, object]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    train_df, valid_df, target_col = load_train_valid_data()

    x_train = train_df[FEATURE_COLS]
    y_train = train_df[target_col]

    x_valid = valid_df[FEATURE_COLS]
    y_valid = valid_df[target_col]

    print(f"Training response models with target: {target_col}")
    print(f"Train shape: {x_train.shape}")
    print(f"Valid shape: {x_valid.shape}")
    print(f"Train target rate: {y_train.mean():.6f}")
    print(f"Valid target rate: {y_valid.mean():.6f}")

    models = build_candidate_models(y_train)

    mlflow.set_experiment(experiment_name)

    best_model = None
    best_model_name = None
    best_metrics = None
    best_pr_auc = -1.0

    for model_name, model in models.items():
        print(f"\nTraining model: {model_name}")

        with mlflow.start_run(run_name=model_name):
            model.fit(x_train, y_train)

            metrics = evaluate_binary_classifier(model, x_valid, y_valid)

            mlflow.log_param("model_type", model_name)
            mlflow.log_param("target_col", target_col)
            mlflow.log_param("n_features", len(FEATURE_COLS))
            mlflow.log_param("train_rows", len(train_df))
            mlflow.log_param("valid_rows", len(valid_df))
            mlflow.log_metric("train_target_rate", float(y_train.mean()))
            mlflow.log_metric("valid_target_rate", float(y_valid.mean()))
            mlflow.log_metrics(metrics)

            mlflow.sklearn.log_model(model, artifact_path="model")

            print(f"Metrics for {model_name}:")
            for metric_name, metric_value in metrics.items():
                print(f"- {metric_name}: {metric_value}")

            pr_auc = metrics["pr_auc"]

            if pr_auc > best_pr_auc:
                best_pr_auc = pr_auc
                best_model = model
                best_model_name = model_name
                best_metrics = metrics

    if best_model is None:
        raise RuntimeError("No model was trained successfully.")

    with MODEL_OUTPUT_PATH.open("wb") as f:
        pickle.dump(best_model, f)

    print("\nBest response model:")
    print(f"- model: {best_model_name}")
    print(f"- metrics: {best_metrics}")
    print(f"- saved_to: {MODEL_OUTPUT_PATH}")

    return {
        "best_model_name": best_model_name,
        "best_metrics": best_metrics,
        "model_output_path": str(MODEL_OUTPUT_PATH),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train baseline response models.")

    parser.add_argument(
        "--experiment-name",
        type=str,
        default="response_model",
        help="MLflow experiment name.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_response_models(experiment_name=args.experiment_name)


if __name__ == "__main__":
    main()