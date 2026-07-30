from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.monitoring.simulate_drift import DriftSimulationSummary, DriftTransformation
from src.ops.simulation_prediction import (
    PredictionComparisonSummary,
    PredictionModelReference,
    SimulationPredictionRequest,
)
from src.policy.schemas import PolicyAuditResponse, PolicySnapshot


class ServiceStatus(BaseModel):
    name: str
    status: str
    detail: str | None = None
    latency_ms: float | None = None


class ModelSummary(BaseModel):
    model_name: str
    model_alias: str
    model_uri: str
    model_loaded: bool
    mlflow_url: str


class DriftSummary(BaseModel):
    available: bool
    report_name: str | None = None
    dataset_drift_detected: bool | None = None
    n_features: int | None = None
    n_drifted_features: int | None = None
    drifted_feature_share: float | None = None
    drifted_features: list[str] = Field(default_factory=list)
    should_retrain: bool | None = None
    retrain_reasons: list[str] = Field(default_factory=list)
    report_url: str | None = None


class DashboardOverview(BaseModel):
    environment: str
    refreshed_at: datetime
    services: list[ServiceStatus]
    model: ModelSummary
    metrics: dict
    database: dict
    drift: DriftSummary
    links: dict[str, str]


class OperationResponse(BaseModel):
    operation_id: str
    operation: str
    actor: str
    status: str
    command_summary: str
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    output_tail: str | None = None
    error_summary: str | None = None


class SimulationDownload(BaseModel):
    format: Literal["parquet", "csv"]
    url: str
    available: bool = True


class SimulationResponse(BaseModel):
    simulation_id: str
    actor: str
    status: str
    preset: str | None
    rows: int
    transformations: list[DriftTransformation]
    summary: DriftSimulationSummary | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime | None = None
    error_summary: str | None = None
    downloads: list[SimulationDownload] = Field(default_factory=list)


class SimulationListResponse(BaseModel):
    items: list[SimulationResponse]


class SimulationPredictionDownload(BaseModel):
    format: Literal["parquet", "csv"]
    url: str
    available: bool = True


class SimulationPredictionResponse(BaseModel):
    prediction_id: str
    simulation_id: str
    actor: str
    status: str
    request: SimulationPredictionRequest
    model: PredictionModelReference | None = None
    summary: PredictionComparisonSummary | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime | None = None
    error_summary: str | None = None
    downloads: list[SimulationPredictionDownload] = Field(default_factory=list)


class SimulationPredictionListResponse(BaseModel):
    items: list[SimulationPredictionResponse]


class PolicyHistoryResponse(BaseModel):
    versions: list[PolicySnapshot]
    audits: list[PolicyAuditResponse]
