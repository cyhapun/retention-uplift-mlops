import os

import mlflow.pyfunc

DEFAULT_MODEL_NAME = "uplift_model"
DEFAULT_MODEL_ALIAS = "champion"


def build_model_uri(
    model_name: str = DEFAULT_MODEL_NAME,
    model_alias: str = DEFAULT_MODEL_ALIAS,
) -> str:
    return f"models:/{model_name}@{model_alias}"


def load_uplift_model(
    model_name: str | None = None,
    model_alias: str | None = None,
):
    model_name = model_name or os.getenv("UPLIFT_MODEL_NAME", DEFAULT_MODEL_NAME)
    model_alias = model_alias or os.getenv("UPLIFT_MODEL_ALIAS", DEFAULT_MODEL_ALIAS)

    model_uri = build_model_uri(
        model_name=model_name,
        model_alias=model_alias,
    )

    return mlflow.pyfunc.load_model(model_uri)
