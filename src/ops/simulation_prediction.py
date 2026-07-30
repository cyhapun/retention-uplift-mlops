"""Pure batch prediction and comparison helpers for Simulation Lab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.data.constants import FEATURE_COLS
from src.policy.config import PolicyConfig
from src.policy.decision_engine import recommend_action_from_policy

PredictionMode = Literal["model_only", "policy_comparison"]


class SimulationPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: PredictionMode = "model_only"
    customer_value: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_mode_value(self) -> "SimulationPredictionRequest":
        if self.mode == "policy_comparison" and self.customer_value is None:
            raise ValueError(
                "A positive scenario customer value is required for policy comparison."
            )
        if self.mode == "model_only" and self.customer_value is not None:
            raise ValueError("Remove customer value when using model-only mode.")
        return self


class PredictionModelReference(BaseModel):
    model_name: str
    model_alias: str
    model_uri: str
    model_version: str


class PredictionComparisonSummary(BaseModel):
    mode: PredictionMode
    rows: int
    model: PredictionModelReference
    customer_value: float | None = None
    baseline_average_uplift: float
    simulated_average_uplift: float
    uplift_delta: float
    recommendation_changed_count: int | None = None
    recommendation_changed_share: float | None = None
    baseline_action_distribution: dict[str, int] = Field(default_factory=dict)
    simulated_action_distribution: dict[str, int] = Field(default_factory=dict)
    baseline_average_expected_value: float | None = None
    simulated_average_expected_value: float | None = None
    expected_value_delta: float | None = None
    baseline_average_roi: float | None = None
    simulated_average_roi: float | None = None
    roi_delta: float | None = None


@dataclass(frozen=True)
class PredictionComparison:
    rows: pd.DataFrame
    summary: PredictionComparisonSummary


def _prediction_frame(model, frame: pd.DataFrame) -> pd.DataFrame:
    missing = [feature for feature in FEATURE_COLS if feature not in frame.columns]
    if missing:
        raise ValueError(f"Missing required features: {missing}")
    prediction = model.predict(frame[FEATURE_COLS].copy())
    if not isinstance(prediction, pd.DataFrame):
        raise ValueError("The model returned an invalid prediction result.")
    required = {"treatment_probability", "control_probability", "uplift_score"}
    missing_outputs = sorted(required - set(prediction.columns))
    if missing_outputs:
        raise ValueError(f"The model response is missing: {missing_outputs}")
    return prediction[list(required)].reset_index(drop=True)


def _distribution(values: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in values.value_counts().sort_index().items()}


def _policy_columns(
    prediction: pd.DataFrame,
    customer_value: float,
    policy_config: PolicyConfig,
) -> pd.DataFrame:
    decisions = [
        recommend_action_from_policy(float(uplift), customer_value, policy_config)
        for uplift in prediction["uplift_score"]
    ]
    return pd.DataFrame(
        {
            "recommended_action": [item["recommended_action"] for item in decisions],
            "treatment_cost": [float(item["treatment_cost"]) for item in decisions],
            "expected_incremental_value": [
                float(item["expected_incremental_value"]) for item in decisions
            ],
            "roi": [float(item["roi"]) for item in decisions],
        }
    )


def compare_predictions(
    model,
    baseline: pd.DataFrame,
    simulated: pd.DataFrame,
    model_reference: PredictionModelReference,
    request: SimulationPredictionRequest,
    policy_config: PolicyConfig | None = None,
) -> PredictionComparison:
    if len(baseline) != len(simulated):
        raise ValueError("Baseline and simulated datasets must contain the same number of rows.")
    if len(baseline) == 0:
        raise ValueError("The simulation contains no rows to predict.")

    baseline_predictions = _prediction_frame(model, baseline)
    simulated_predictions = _prediction_frame(model, simulated)
    result = pd.DataFrame(
        {"simulation_row_id": [f"row_{index:06d}" for index in range(len(baseline))]}
    )
    for prefix, predictions in (
        ("baseline", baseline_predictions),
        ("simulated", simulated_predictions),
    ):
        for column in predictions.columns:
            result[f"{prefix}_{column}"] = predictions[column]

    summary_kwargs = {
        "mode": request.mode,
        "rows": len(result),
        "model": model_reference,
        "customer_value": request.customer_value,
        "baseline_average_uplift": float(baseline_predictions["uplift_score"].mean()),
        "simulated_average_uplift": float(simulated_predictions["uplift_score"].mean()),
        "uplift_delta": float(
            simulated_predictions["uplift_score"].mean()
            - baseline_predictions["uplift_score"].mean()
        ),
    }

    if request.mode == "policy_comparison":
        if policy_config is None:
            raise ValueError("A policy configuration is required for policy comparison.")
        baseline_policy = _policy_columns(
            baseline_predictions, request.customer_value, policy_config
        )
        simulated_policy = _policy_columns(
            simulated_predictions, request.customer_value, policy_config
        )
        for prefix, policy in (("baseline", baseline_policy), ("simulated", simulated_policy)):
            for column in policy.columns:
                result[f"{prefix}_{column}"] = policy[column]
        changed = baseline_policy["recommended_action"] != simulated_policy["recommended_action"]
        baseline_ev = float(baseline_policy["expected_incremental_value"].mean())
        simulated_ev = float(simulated_policy["expected_incremental_value"].mean())
        baseline_roi = float(baseline_policy["roi"].mean())
        simulated_roi = float(simulated_policy["roi"].mean())
        summary_kwargs.update(
            {
                "recommendation_changed_count": int(changed.sum()),
                "recommendation_changed_share": float(changed.mean()),
                "baseline_action_distribution": _distribution(
                    baseline_policy["recommended_action"]
                ),
                "simulated_action_distribution": _distribution(
                    simulated_policy["recommended_action"]
                ),
                "baseline_average_expected_value": baseline_ev,
                "simulated_average_expected_value": simulated_ev,
                "expected_value_delta": simulated_ev - baseline_ev,
                "baseline_average_roi": baseline_roi,
                "simulated_average_roi": simulated_roi,
                "roi_delta": simulated_roi - baseline_roi,
            }
        )
        result["recommendation_changed"] = changed

    return PredictionComparison(
        rows=result,
        summary=PredictionComparisonSummary(**summary_kwargs),
    )
