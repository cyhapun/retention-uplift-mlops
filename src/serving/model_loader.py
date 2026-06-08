import os

import mlflow
import mlflow.pyfunc

DEFAULT_TRACKING_URI = "sqlite:///mlflow.db"
DEFAULT_MODEL_NAME = "uplift_model"
DEFAULT_MODEL_ALIAS = "champion"


def get_model_uri() -> str:
    model_name = os.getenv("UPLIFT_MODEL_NAME", DEFAULT_MODEL_NAME)
    model_alias = os.getenv("UPLIFT_MODEL_ALIAS", DEFAULT_MODEL_ALIAS)

    return f"models:/{model_name}@{model_alias}"


def load_uplift_model():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)
    mlflow.set_tracking_uri(tracking_uri)

    model_uri = get_model_uri()
    return mlflow.pyfunc.load_model(model_uri)