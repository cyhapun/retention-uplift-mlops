import pickle
from pathlib import Path

import mlflow.pyfunc
import pandas as pd

from src.data.constants import FEATURE_COLS


class UpliftModelWrapper(mlflow.pyfunc.PythonModel):
    def load_context(self, context) -> None:
        with open(context.artifacts["treatment_model"], "rb") as f:
            self.treatment_model = pickle.load(f)

        with open(context.artifacts["control_model"], "rb") as f:
            self.control_model = pickle.load(f)

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        feature_df = validate_model_input(model_input)

        treatment_probability = self.treatment_model.predict_proba(feature_df)[:, 1]
        control_probability = self.control_model.predict_proba(feature_df)[:, 1]
        uplift_score = treatment_probability - control_probability

        return pd.DataFrame(
            {
                "treatment_probability": treatment_probability,
                "control_probability": control_probability,
                "uplift_score": uplift_score,
            }
        )


def validate_model_input(model_input: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(model_input, pd.DataFrame):
        raise TypeError("model_input must be a pandas DataFrame.")

    missing_features = [feature for feature in FEATURE_COLS if feature not in model_input.columns]

    if missing_features:
        raise ValueError(f"Missing required features: {missing_features}")

    return model_input[FEATURE_COLS].copy()


def load_pickle_model(path: str | Path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found at {path}")

    with path.open("rb") as f:
        return pickle.load(f)