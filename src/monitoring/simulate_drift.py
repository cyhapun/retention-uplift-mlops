"""Safe, parameterized generation of synthetic drift datasets.

This module deliberately contains no report generation or production side effects.
It reads a baseline dataset, applies an allowlisted set of numeric transformations,
and writes a new Parquet file selected by the caller.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.data.constants import FEATURE_COLS

DEFAULT_INPUT_PATH = Path("data/processed/test.parquet")
DEFAULT_OUTPUT_PATH = Path("data/processed/test_drifted.parquet")
MAX_FEATURE_INTENSITY = 100.0
MAX_ROWS = 100_000

TransformOperation = Literal["scale_percent", "shift"]
DriftPreset = Literal["low", "medium", "high"]


class DriftTransformation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: str
    operation: TransformOperation
    value: float = Field(..., description="Percent for scale_percent, absolute units for shift")

    @field_validator("feature")
    @classmethod
    def validate_feature(cls, value: str) -> str:
        if value not in FEATURE_COLS:
            raise ValueError(f"Unsupported feature: {value}")
        return value

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: float) -> float:
        if not math.isfinite(value) or abs(value) > MAX_FEATURE_INTENSITY:
            raise ValueError(
                f"Feature intensity must be between {-MAX_FEATURE_INTENSITY} "
                f"and {MAX_FEATURE_INTENSITY}."
            )
        return float(value)


PRESETS: dict[DriftPreset, tuple[DriftTransformation, ...]] = {
    "low": (
        DriftTransformation(feature="f0", operation="scale_percent", value=15),
        DriftTransformation(feature="f3", operation="shift", value=0.05),
    ),
    "medium": (
        DriftTransformation(feature="f0", operation="scale_percent", value=50),
        DriftTransformation(feature="f3", operation="shift", value=0.2),
        DriftTransformation(feature="f7", operation="scale_percent", value=-30),
    ),
    "high": (
        DriftTransformation(feature="f0", operation="scale_percent", value=80),
        DriftTransformation(feature="f3", operation="shift", value=0.5),
        DriftTransformation(feature="f7", operation="scale_percent", value=-50),
        DriftTransformation(feature="f9", operation="shift", value=0.35),
    ),
}


class DriftSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: DriftPreset | None = "medium"
    rows: int = Field(default=10_000, ge=1, le=MAX_ROWS)
    transformations: list[DriftTransformation] | None = Field(
        default=None, max_length=len(FEATURE_COLS)
    )

    @field_validator("transformations")
    @classmethod
    def validate_transformations(
        cls, value: list[DriftTransformation] | None
    ) -> list[DriftTransformation] | None:
        if value is None:
            return value
        features = [item.feature for item in value]
        if len(features) != len(set(features)):
            raise ValueError("Each feature can only be configured once.")
        return value

    def resolved_transformations(self) -> tuple[DriftTransformation, ...]:
        if self.transformations is not None:
            if not self.transformations:
                raise ValueError("At least one feature transformation is required.")
            return tuple(self.transformations)
        if self.preset is None:
            raise ValueError("Choose a drift preset or configure at least one feature.")
        return PRESETS[self.preset]


class FeatureDriftSummary(BaseModel):
    feature: str
    operation: TransformOperation
    value: float
    before_mean: float
    after_mean: float
    before_std: float
    after_std: float


class DriftSimulationSummary(BaseModel):
    rows: int
    affected_feature_count: int
    severity: Literal["low", "medium", "high"]
    affected_features: list[FeatureDriftSummary]


@dataclass(frozen=True)
class GeneratedDriftDataset:
    dataframe: pd.DataFrame
    summary: DriftSimulationSummary


def resolve_transformations(
    preset: DriftPreset | None = "medium",
    transformations: list[DriftTransformation] | None = None,
) -> tuple[DriftTransformation, ...]:
    request = DriftSimulationRequest(preset=preset, transformations=transformations)
    return request.resolved_transformations()


def simulate_feature_drift(
    df: pd.DataFrame,
    transformations: list[DriftTransformation] | None = None,
) -> pd.DataFrame:
    """Apply transformations without mutating ``df``.

    The default medium preset retains the original demo's f0/f3/f7 behavior.
    """

    resolved = resolve_transformations("medium", transformations)
    missing_features = [item.feature for item in resolved if item.feature not in df.columns]
    if missing_features:
        raise ValueError(f"Missing feature columns: {missing_features}")

    drifted_df = df.copy(deep=True)
    for transformation in resolved:
        if transformation.operation == "scale_percent":
            drifted_df[transformation.feature] = drifted_df[transformation.feature] * (
                1 + transformation.value / 100
            )
        else:
            drifted_df[transformation.feature] = (
                drifted_df[transformation.feature] + transformation.value
            )
    return drifted_df


def _safe_float(value: float) -> float:
    return float(value) if pd.notna(value) else 0.0


def summarize_drift(
    before: pd.DataFrame,
    after: pd.DataFrame,
    transformations: tuple[DriftTransformation, ...],
) -> DriftSimulationSummary:
    summaries = []
    for transformation in transformations:
        feature = transformation.feature
        summaries.append(
            FeatureDriftSummary(
                feature=feature,
                operation=transformation.operation,
                value=transformation.value,
                before_mean=_safe_float(before[feature].mean()),
                after_mean=_safe_float(after[feature].mean()),
                before_std=_safe_float(before[feature].std()),
                after_std=_safe_float(after[feature].std()),
            )
        )

    max_intensity = max((abs(item.value) for item in transformations), default=0)
    if max_intensity >= 60 or len(summaries) >= 4:
        severity = "high"
    elif max_intensity >= 25 or len(summaries) >= 3:
        severity = "medium"
    else:
        severity = "low"
    return DriftSimulationSummary(
        rows=len(after),
        affected_feature_count=len(summaries),
        severity=severity,
        affected_features=summaries,
    )


def generate_drift_dataset(
    df: pd.DataFrame,
    request: DriftSimulationRequest,
) -> GeneratedDriftDataset:
    if request.rows > len(df):
        raise ValueError(
            f"Requested {request.rows:,} rows but the baseline only has {len(df):,} rows."
        )
    baseline = df.iloc[: request.rows].copy(deep=True)
    transformations = request.resolved_transformations()
    missing_features = [
        item.feature for item in transformations if item.feature not in baseline.columns
    ]
    if missing_features:
        raise ValueError(f"Missing feature columns: {missing_features}")
    drifted = simulate_feature_drift(baseline, list(transformations))
    return GeneratedDriftDataset(
        dataframe=drifted,
        summary=summarize_drift(baseline, drifted, transformations),
    )


def create_drifted_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    request: DriftSimulationRequest | None = None,
) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset not found at {input_path}")

    df = pd.read_parquet(input_path)
    missing_features = [feature for feature in FEATURE_COLS if feature not in df.columns]
    if missing_features:
        raise ValueError(f"Missing feature columns: {missing_features}")
    request = request or DriftSimulationRequest(preset="medium", rows=min(len(df), MAX_ROWS))
    generated = generate_drift_dataset(df, request)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated.dataframe.to_parquet(output_path, index=False)
    print(f"Saved simulated drift dataset to {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a controlled drift dataset.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--preset", choices=tuple(PRESETS), default="medium")
    args = parser.parse_args()
    input_rows = len(pd.read_parquet(args.input_path))
    create_drifted_dataset(
        input_path=args.input_path,
        output_path=args.output_path,
        request=DriftSimulationRequest(preset=args.preset, rows=min(input_rows, MAX_ROWS)),
    )


if __name__ == "__main__":
    main()
