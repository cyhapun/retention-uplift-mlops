import pandas as pd
import pytest
from pydantic import ValidationError

from src.data.constants import FEATURE_COLS
from src.monitoring.simulate_drift import (
    PRESETS,
    DriftSimulationRequest,
    DriftTransformation,
    generate_drift_dataset,
)


def test_presets_resolve_to_bounded_transformations():
    for name, transformations in PRESETS.items():
        request = DriftSimulationRequest(preset=name, rows=10)
        assert request.resolved_transformations() == transformations
        assert all(item.feature in FEATURE_COLS for item in transformations)


def test_unknown_features_and_unsupported_operations_are_rejected():
    with pytest.raises(ValidationError, match="Unsupported feature"):
        DriftTransformation(feature="customer_value", operation="shift", value=1)
    with pytest.raises(ValidationError):
        DriftTransformation.model_validate({"feature": "f0", "operation": "formula", "value": 1})


def test_duplicate_features_and_intensity_limits_are_rejected():
    transformations = [
        {"feature": "f0", "operation": "shift", "value": 1},
        {"feature": "f0", "operation": "scale_percent", "value": 2},
    ]
    with pytest.raises(ValidationError, match="only be configured once"):
        DriftSimulationRequest(transformations=transformations)
    with pytest.raises(ValidationError, match="intensity"):
        DriftTransformation(feature="f0", operation="shift", value=101)


def test_row_limits_are_rejected_before_generation():
    with pytest.raises(ValidationError):
        DriftSimulationRequest(rows=0)
    with pytest.raises(ValidationError):
        DriftSimulationRequest(rows=100_001)

    frame = pd.DataFrame({feature: [1.0, 2.0] for feature in FEATURE_COLS})
    with pytest.raises(ValueError, match="baseline only has"):
        generate_drift_dataset(frame, DriftSimulationRequest(rows=3, preset="low"))
