import pandas as pd
import pytest
from pydantic import ValidationError

from src.data.constants import FEATURE_COLS
from src.ops.simulation_prediction import (
    PredictionModelReference,
    SimulationPredictionRequest,
    compare_predictions,
)
from src.policy.config import load_policy_config


class FakeModel:
    def predict(self, frame):
        uplift = frame["f0"].astype(float) * 0.01
        return pd.DataFrame(
            {
                "treatment_probability": 0.5 + uplift,
                "control_probability": 0.5,
                "uplift_score": uplift,
            }
        )


class InvalidModel:
    def predict(self, _frame):
        return pd.DataFrame({"uplift_score": [0.1]})


def frames():
    baseline = pd.DataFrame({feature: [1.0, 2.0, 3.0] for feature in FEATURE_COLS})
    simulated = baseline.copy()
    simulated["f0"] = [2.0, 3.0, 4.0]
    return baseline, simulated


def reference():
    return PredictionModelReference(
        model_name="uplift_model",
        model_alias="champion",
        model_uri="models:/uplift_model@champion",
        model_version="test-version",
    )


def test_model_only_comparison_keeps_policy_fields_unavailable():
    baseline, simulated = frames()
    comparison = compare_predictions(
        FakeModel(),
        baseline,
        simulated,
        reference(),
        SimulationPredictionRequest(),
    )
    assert comparison.summary.mode == "model_only"
    assert comparison.summary.rows == 3
    assert comparison.summary.recommendation_changed_count is None
    assert comparison.summary.simulated_average_uplift > comparison.summary.baseline_average_uplift
    assert list(comparison.rows["simulation_row_id"]) == ["row_000000", "row_000001", "row_000002"]


def test_policy_comparison_calculates_actions_and_value_deltas():
    baseline, simulated = frames()
    request = SimulationPredictionRequest(mode="policy_comparison", customer_value=100)
    comparison = compare_predictions(
        FakeModel(), baseline, simulated, reference(), request, load_policy_config()
    )
    assert comparison.summary.customer_value == 100
    assert comparison.summary.recommendation_changed_count is not None
    assert comparison.summary.baseline_action_distribution
    assert comparison.summary.expected_value_delta is not None
    assert "baseline_recommended_action" in comparison.rows
    assert "simulated_roi" in comparison.rows


def test_prediction_request_validates_mode_and_value():
    with pytest.raises(ValidationError, match="required for policy comparison"):
        SimulationPredictionRequest(mode="policy_comparison")
    with pytest.raises(ValidationError, match="model-only mode"):
        SimulationPredictionRequest(mode="model_only", customer_value=100)
    with pytest.raises(ValidationError):
        SimulationPredictionRequest(mode="policy_comparison", customer_value=0)


def test_prediction_rejects_invalid_model_output():
    baseline, simulated = frames()
    with pytest.raises(ValueError, match="missing"):
        compare_predictions(
            InvalidModel(), baseline, simulated, reference(), SimulationPredictionRequest()
        )


def test_prediction_requires_paired_rows_and_features():
    baseline, simulated = frames()
    with pytest.raises(ValueError, match="same number"):
        compare_predictions(
            FakeModel(), baseline, simulated.iloc[:2], reference(), SimulationPredictionRequest()
        )
    with pytest.raises(ValueError, match="Missing required features"):
        compare_predictions(
            FakeModel(),
            baseline.drop(columns=["f0"]),
            simulated,
            reference(),
            SimulationPredictionRequest(),
        )
