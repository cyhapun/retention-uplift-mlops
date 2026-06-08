import argparse
from pathlib import Path

import mlflow
import mlflow.pyfunc
import pandas as pd
from mlflow.tracking import MlflowClient

from src.data.constants import FEATURE_COLS
from src.models.uplift_wrapper import UpliftModelWrapper

DEFAULT_TREATMENT_MODEL_PATH = Path("artifacts/uplift/treatment_model.pkl")
DEFAULT_CONTROL_MODEL_PATH = Path("artifacts/uplift/control_model.pkl")
DEFAULT_REGISTERED_MODEL_NAME = "uplift_model"
DEFAULT_ALIAS = "champion"


def validate_artifact_paths(treatment_model_path: Path, control_model_path: Path) -> None:
    missing_paths = [
        path
        for path in [treatment_model_path, control_model_path]
        if not path.exists()
    ]

    if missing_paths:
        raise FileNotFoundError(
            "Missing uplift model artifacts: "
            + ", ".join(str(path) for path in missing_paths)
            + ". Run Phase 4 training before registration."
        )


def create_input_example() -> pd.DataFrame:
    return pd.DataFrame([{feature: 0.0 for feature in FEATURE_COLS}])


def register_uplift_model(
    treatment_model_path: str | Path = DEFAULT_TREATMENT_MODEL_PATH,
    control_model_path: str | Path = DEFAULT_CONTROL_MODEL_PATH,
    registered_model_name: str = DEFAULT_REGISTERED_MODEL_NAME,
    alias: str = DEFAULT_ALIAS,
    experiment_name: str = "uplift_model_registry",
) -> dict[str, str]:
    treatment_model_path = Path(treatment_model_path)
    control_model_path = Path(control_model_path)

    validate_artifact_paths(
        treatment_model_path=treatment_model_path,
        control_model_path=control_model_path,
    )

    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="register_uplift_pyfunc_model") as run:
        model_info = mlflow.pyfunc.log_model(
            artifact_path="uplift_model",
            python_model=UpliftModelWrapper(),
            artifacts={
                "treatment_model": str(treatment_model_path),
                "control_model": str(control_model_path),
            },
            input_example=create_input_example(),
            registered_model_name=registered_model_name,
        )

        client = MlflowClient()

        model_version = model_info.registered_model_version

        if model_version is None:
            latest_versions = client.search_model_versions(
                f"name = '{registered_model_name}'"
            )
            model_version = max(
                int(version.version)
                for version in latest_versions
            )

        client.set_registered_model_alias(
            name=registered_model_name,
            alias=alias,
            version=str(model_version),
        )

        client.set_model_version_tag(
            name=registered_model_name,
            version=str(model_version),
            key="model_type",
            value="t_learner_uplift_pyfunc",
        )
        client.set_model_version_tag(
            name=registered_model_name,
            version=str(model_version),
            key="run_id",
            value=run.info.run_id,
        )

        model_uri = f"models:/{registered_model_name}@{alias}"

        print("Registered uplift model successfully.")
        print(f"- registered_model_name: {registered_model_name}")
        print(f"- version: {model_version}")
        print(f"- alias: {alias}")
        print(f"- model_uri: {model_uri}")

        return {
            "registered_model_name": registered_model_name,
            "model_version": str(model_version),
            "alias": alias,
            "model_uri": model_uri,
            "run_id": run.info.run_id,
            "artifact_uri": model_info.model_uri,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register uplift model in MLflow Model Registry.")

    parser.add_argument(
        "--treatment-model-path",
        type=str,
        default=str(DEFAULT_TREATMENT_MODEL_PATH),
    )
    parser.add_argument(
        "--control-model-path",
        type=str,
        default=str(DEFAULT_CONTROL_MODEL_PATH),
    )
    parser.add_argument(
        "--registered-model-name",
        type=str,
        default=DEFAULT_REGISTERED_MODEL_NAME,
    )
    parser.add_argument(
        "--alias",
        type=str,
        default=DEFAULT_ALIAS,
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default="uplift_model_registry",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    register_uplift_model(
        treatment_model_path=args.treatment_model_path,
        control_model_path=args.control_model_path,
        registered_model_name=args.registered_model_name,
        alias=args.alias,
        experiment_name=args.experiment_name,
    )


if __name__ == "__main__":
    main()