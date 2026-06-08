import argparse
from pathlib import Path

import mlflow
import mlflow.pyfunc
import pandas as pd
from mlflow.tracking import MlflowClient

from src.models.uplift_wrapper import FEATURE_COLS, UpliftModelWrapper

DEFAULT_TRACKING_URI = "sqlite:///mlflow.db"
DEFAULT_MODEL_NAME = "uplift_model"
DEFAULT_ALIAS = "champion"

TREATMENT_MODEL_PATH = Path("artifacts/uplift/treatment_model.pkl")
CONTROL_MODEL_PATH = Path("artifacts/uplift/control_model.pkl")
VALID_DATA_PATH = Path("data/processed/valid.parquet")


def validate_artifacts() -> None:
    required_files = [
        TREATMENT_MODEL_PATH,
        CONTROL_MODEL_PATH,
        VALID_DATA_PATH,
    ]

    missing_files = [path for path in required_files if not path.exists()]

    if missing_files:
        raise FileNotFoundError(f"Missing required files: {missing_files}")


def get_input_example() -> pd.DataFrame:
    valid_df = pd.read_parquet(VALID_DATA_PATH)
    return valid_df[FEATURE_COLS].head(5)


def get_latest_model_version(client: MlflowClient, model_name: str) -> str:
    model_versions = client.search_model_versions(f"name='{model_name}'")

    if not model_versions:
        raise ValueError(f"No model versions found for model: {model_name}")

    latest_version = max(model_versions, key=lambda version: int(version.version))
    return latest_version.version


def register_uplift_model(
    tracking_uri: str,
    model_name: str,
    alias: str,
) -> None:
    validate_artifacts()

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("uplift_model_registry")

    input_example = get_input_example()

    with mlflow.start_run(run_name="register_uplift_model"):
        model_info = mlflow.pyfunc.log_model(
            artifact_path="uplift_model",
            python_model=UpliftModelWrapper(),
            artifacts={
                "treatment_model": str(TREATMENT_MODEL_PATH),
                "control_model": str(CONTROL_MODEL_PATH),
            },
            input_example=input_example,
            registered_model_name=model_name,
        )

        loaded_model = mlflow.pyfunc.load_model(model_info.model_uri)
        prediction = loaded_model.predict(input_example)

        mlflow.log_param("model_name", model_name)
        mlflow.log_param("model_alias", alias)
        mlflow.log_param("wrapper_type", "UpliftModelWrapper")
        mlflow.log_param("base_model_type", "T-Learner")
        mlflow.log_metric("prediction_rows_checked", len(prediction))
        mlflow.log_metric("mean_registered_uplift", prediction["uplift_score"].mean())

        client = MlflowClient()
        model_version = get_latest_model_version(client, model_name)

        client.set_registered_model_alias(
            name=model_name,
            alias=alias,
            version=model_version,
        )

        print(f"Registered model: {model_name}")
        print(f"Model version: {model_version}")
        print(f"Alias: {alias}")
        print(f"Model URI: models:/{model_name}@{alias}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tracking-uri",
        default=DEFAULT_TRACKING_URI,
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL_NAME,
    )
    parser.add_argument(
        "--alias",
        default=DEFAULT_ALIAS,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    register_uplift_model(
        tracking_uri=args.tracking_uri,
        model_name=args.model_name,
        alias=args.alias,
    )