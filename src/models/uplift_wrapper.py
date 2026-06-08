import pickle
from typing import Any

import mlflow.pyfunc
import pandas as pd

FEATURE_COLS = [f"f{i}" for i in range(11)]


class UpliftModelWrapper(mlflow.pyfunc.PythonModel):
    def load_context(self, context: Any) -> None:
        with open(context.artifacts["treatment_model"], "rb") as file:
            self.treatment_model = pickle.load(file)

        with open(context.artifacts["control_model"], "rb") as file:
            self.control_model = pickle.load(file)

    def predict(
        self,
        context: Any,
        model_input: pd.DataFrame,
        params: dict | None = None,
    ) -> pd.DataFrame:
        if not isinstance(model_input, pd.DataFrame):
            model_input = pd.DataFrame(model_input)

        missing_cols = [
            col for col in FEATURE_COLS if col not in model_input.columns
        ]

        if missing_cols:
            raise ValueError(f"Missing feature columns: {missing_cols}")

        features = model_input[FEATURE_COLS]

        treatment_probability = self.treatment_model.predict_proba(features)[:, 1]
        control_probability = self.control_model.predict_proba(features)[:, 1]
        uplift_score = treatment_probability - control_probability

        return pd.DataFrame(
            {
                "treatment_probability": treatment_probability,
                "control_probability": control_probability,
                "uplift_score": uplift_score,
            }
        )