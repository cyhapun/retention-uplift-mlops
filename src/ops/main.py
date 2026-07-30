import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select

from src.db.database import SessionLocal, init_database
from src.db.models import OperationAudit, OperationRun, SimulationPredictionRun, SimulationRun
from src.monitoring.simulate_drift import (
    DriftSimulationRequest,
    DriftSimulationSummary,
    DriftTransformation,
)
from src.ops.integrations import (
    get_database_summary,
    get_drift_summary,
    get_metrics,
    get_model_summary,
    get_overview,
    get_service_health,
)
from src.ops.runner import ALLOWED_OPERATIONS, OperationRunner
from src.ops.schemas import (
    OperationResponse,
    PolicyHistoryResponse,
    SimulationListResponse,
    SimulationPredictionListResponse,
    SimulationPredictionResponse,
    SimulationResponse,
)
from src.ops.simulation_prediction import (
    PredictionComparisonSummary,
    PredictionModelReference,
    SimulationPredictionRequest,
)
from src.ops.simulation_prediction_service import SimulationPredictionService
from src.ops.simulation_service import SimulationService
from src.policy.schemas import (
    PolicyActivationRequest,
    PolicyAuditResponse,
    PolicyDocument,
    PolicyPreviewRequest,
    PolicyPreviewResponse,
    PolicyRollbackRequest,
    PolicySnapshot,
    PolicyValidationResponse,
)
from src.policy.store import (
    PolicyConflictError,
    activate_policy,
    ensure_policy_seed,
    get_policy_snapshot,
    list_policy_audits,
    list_policy_versions,
    policy_store_enabled,
    preview_policy,
    record_policy_rejection,
    rollback_policy,
    validate_policy_document,
)


def _as_response(operation_run: OperationRun, include_output: bool = False) -> OperationResponse:
    response = OperationResponse.model_validate(operation_run, from_attributes=True)
    if not include_output:
        response.output_tail = None
    return response


def _record_audit(
    operation: str,
    actor: str,
    status: str,
    outcome: str,
    operation_id: str | None = None,
) -> None:
    with SessionLocal() as session:
        session.add(
            OperationAudit(
                audit_id=str(uuid4()),
                operation_id=operation_id,
                operation=operation,
                actor=actor,
                status=status,
                outcome=outcome[:1000],
            )
        )
        session.commit()


def _require_admin(authorization: str | None) -> str:
    configured_token = os.getenv("OPS_ADMIN_TOKEN", "").strip()
    if not configured_token:
        raise HTTPException(status_code=503, detail="Operations control is not configured.")

    if authorization != f"Bearer {configured_token}":
        raise HTTPException(status_code=401, detail="Admin authorization required.")

    return "admin"


def _simulation_response(run: SimulationRun) -> SimulationResponse:
    transformations = [
        DriftTransformation.model_validate(item)
        for item in run.request_payload.get("transformations", [])
    ]
    summary = (
        DriftSimulationSummary.model_validate(run.summary_payload) if run.summary_payload else None
    )
    downloads = []
    if run.status == "succeeded":
        downloads = [
            {
                "format": "parquet",
                "url": f"/api/simulations/{run.simulation_id}/download?format=parquet",
            },
            {"format": "csv", "url": f"/api/simulations/{run.simulation_id}/download?format=csv"},
        ]
    return SimulationResponse(
        simulation_id=run.simulation_id,
        actor=run.actor,
        status=run.status,
        preset=run.preset,
        rows=run.rows,
        transformations=transformations,
        summary=summary,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        expires_at=run.expires_at,
        error_summary=run.error_summary,
        downloads=downloads,
    )


def _prediction_response(run: SimulationPredictionRun) -> SimulationPredictionResponse:
    request = SimulationPredictionRequest.model_validate(
        {
            key: value
            for key, value in run.request_payload.items()
            if key in {"mode", "customer_value"}
        }
    )
    model = (
        PredictionModelReference.model_validate(run.model_reference)
        if run.model_reference
        else None
    )
    summary = (
        PredictionComparisonSummary.model_validate(run.summary_payload)
        if run.summary_payload
        else None
    )
    downloads = []
    if run.status == "succeeded":
        downloads = [
            {
                "format": "parquet",
                "url": f"/api/simulation-predictions/{run.prediction_id}/download?format=parquet",
            },
            {
                "format": "csv",
                "url": f"/api/simulation-predictions/{run.prediction_id}/download?format=csv",
            },
        ]
    return SimulationPredictionResponse(
        prediction_id=run.prediction_id,
        simulation_id=run.simulation_id,
        actor=run.actor,
        status=run.status,
        request=request,
        model=model,
        summary=summary,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        expires_at=run.expires_at,
        error_summary=run.error_summary,
        downloads=downloads,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    ensure_policy_seed()
    app.state.runner = OperationRunner()
    app.state.runner.reconcile_stale_jobs()
    app.state.simulations = SimulationService()
    app.state.simulations.initialize()
    app.state.predictions = SimulationPredictionService(app.state.simulations)
    app.state.predictions.initialize()
    yield
    app.state.runner.shutdown()
    app.state.predictions.shutdown()
    app.state.simulations.shutdown()


app = FastAPI(
    title="RetentionOps Operations Control Plane",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard/overview")
def dashboard_overview():
    return get_overview()


@app.get("/dashboard/health")
def dashboard_health():
    return {"services": get_service_health()}


@app.get("/dashboard/model")
def dashboard_model():
    return get_model_summary()


@app.get("/dashboard/metrics")
def dashboard_metrics():
    return get_metrics()


@app.get("/dashboard/database")
def dashboard_database():
    return get_database_summary()


@app.get("/dashboard/drift")
def dashboard_drift():
    return get_drift_summary()


def _policy_snapshot_response() -> PolicySnapshot:
    document, version = get_policy_snapshot()
    return PolicySnapshot(
        version_id=version.version_id if version else "yaml-fallback",
        version_number=version.version_number if version else 0,
        created_at=version.created_at if version else None,
        activated_at=version.activated_at if version else None,
        created_by=version.created_by if version else "yaml-fallback",
        editable=policy_store_enabled() and bool(os.getenv("OPS_ADMIN_TOKEN", "").strip()),
        policy=document,
    )


@app.get("/policy", response_model=PolicySnapshot)
def get_policy():
    return _policy_snapshot_response()


@app.post("/policy/validate", response_model=PolicyValidationResponse)
def validate_policy(policy: PolicyDocument):
    try:
        validate_policy_document(policy)
    except ValueError as exc:
        return PolicyValidationResponse(valid=False, errors=[str(exc)], policy=policy)
    return PolicyValidationResponse(valid=True, policy=policy)


@app.post("/policy/preview", response_model=PolicyPreviewResponse)
def policy_preview(request: PolicyPreviewRequest):
    try:
        return preview_policy(request.policy, request.limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/policy/history", response_model=PolicyHistoryResponse)
def policy_history(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    versions = [
        PolicySnapshot(
            version_id=version.version_id,
            version_number=version.version_number,
            created_at=version.created_at,
            activated_at=version.activated_at,
            created_by=version.created_by,
            editable=True,
            policy=PolicyDocument.model_validate(version.config),
        )
        for version in list_policy_versions()
    ]
    audits = [
        PolicyAuditResponse.model_validate(item, from_attributes=True)
        for item in list_policy_audits()
    ]
    return PolicyHistoryResponse(versions=versions, audits=audits)


@app.post("/policy/activate", response_model=PolicySnapshot, status_code=201)
def activate_policy_endpoint(
    request: PolicyActivationRequest,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    try:
        version = activate_policy(
            document=request.policy,
            actor=actor,
            expected_version_id=request.expected_version_id,
            confirm=request.confirm,
            change_summary=request.change_summary,
        )
    except PolicyConflictError as exc:
        record_policy_rejection("activate", actor, str(exc), request.expected_version_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        record_policy_rejection("activate", actor, str(exc), request.expected_version_id)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        record_policy_rejection("activate", actor, str(exc), request.expected_version_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PolicySnapshot(
        version_id=version.version_id,
        version_number=version.version_number,
        created_at=version.created_at,
        activated_at=version.activated_at,
        created_by=version.created_by,
        editable=True,
        policy=request.policy,
    )


@app.post("/policy/rollback/{version_id}", response_model=PolicySnapshot, status_code=201)
def rollback_policy_endpoint(
    version_id: str,
    request: PolicyRollbackRequest,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    try:
        version = rollback_policy(version_id, actor, request.expected_version_id, request.confirm)
    except PolicyConflictError as exc:
        record_policy_rejection("rollback", actor, str(exc), request.expected_version_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, LookupError) as exc:
        record_policy_rejection("rollback", actor, str(exc), version_id)
        status_code = 422 if isinstance(exc, ValueError) else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except RuntimeError as exc:
        record_policy_rejection("rollback", actor, str(exc), version_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PolicySnapshot(
        version_id=version.version_id,
        version_number=version.version_number,
        created_at=version.created_at,
        activated_at=version.activated_at,
        created_by=version.created_by,
        editable=True,
        policy=PolicyDocument.model_validate(version.config),
    )


@app.get("/operations", response_model=list[OperationResponse])
def list_operations(limit: int = 25):
    limit = min(max(limit, 1), 100)
    with SessionLocal() as session:
        operations = session.scalars(
            select(OperationRun).order_by(OperationRun.created_at.desc()).limit(limit)
        ).all()
        return [_as_response(item) for item in operations]


@app.get("/operations/{operation_id}", response_model=OperationResponse)
def get_operation(
    operation_id: str,
    authorization: str | None = Header(default=None),
):
    _require_admin(authorization)
    with SessionLocal() as session:
        operation_run = session.get(OperationRun, operation_id)
        if operation_run is None:
            raise HTTPException(status_code=404, detail="Operation not found.")
        return _as_response(operation_run, include_output=True)


@app.post("/operations/{operation}", response_model=OperationResponse, status_code=202)
def start_operation(
    operation: str,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    if operation not in ALLOWED_OPERATIONS:
        _record_audit(operation, actor, "rejected", "Unsupported operation.")
        raise HTTPException(status_code=404, detail="Unsupported operation.")

    try:
        operation_run = app.state.runner.start(operation=operation, actor=actor)
    except RuntimeError as exc:
        _record_audit(operation, actor, "rejected", str(exc))
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _record_audit(
        operation,
        actor,
        "accepted",
        "Operation queued.",
        operation_id=operation_run.operation_id,
    )
    return _as_response(operation_run)


@app.post("/simulations", response_model=SimulationResponse, status_code=202)
def create_simulation(
    request: DriftSimulationRequest,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    try:
        run = app.state.simulations.create(request, actor)
    except RuntimeError as exc:
        _record_audit("simulate-drift", actor, "rejected", str(exc))
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        _record_audit("simulate-drift", actor, "rejected", str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _simulation_response(run)


@app.get("/simulations", response_model=SimulationListResponse)
def list_simulations(
    limit: int = 25,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    return SimulationListResponse(
        items=[_simulation_response(run) for run in app.state.simulations.list(actor, limit)]
    )


@app.get("/simulations/{simulation_id}", response_model=SimulationResponse)
def get_simulation(
    simulation_id: str,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    run = app.state.simulations.get(simulation_id)
    if run is None or run.actor != actor:
        raise HTTPException(status_code=404, detail="Simulation not found.")
    return _simulation_response(run)


@app.get("/simulations/{simulation_id}/download")
def download_simulation(
    simulation_id: str,
    format: str = Query(default="parquet", pattern="^(parquet|csv)$"),
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    try:
        run = app.state.simulations.get(simulation_id)
        if run is None or run.actor != actor:
            raise LookupError("Simulation not found.")
        if format == "csv":
            run, payload = app.state.simulations.csv_bytes(simulation_id)
            return Response(
                content=payload,
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="drift-simulation-{simulation_id}.csv"'
                    )
                },
            )
        run, path = app.state.simulations.download_path(simulation_id)
        return FileResponse(
            path,
            media_type="application/vnd.apache.parquet",
            filename=f"drift-simulation-{simulation_id}.parquet",
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/simulations/{simulation_id}/predict",
    response_model=SimulationPredictionResponse,
    status_code=202,
)
def create_simulation_prediction(
    simulation_id: str,
    request: SimulationPredictionRequest,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    try:
        run = app.state.predictions.create(simulation_id, actor, request)
    except LookupError as exc:
        _record_audit("simulate-drift-prediction", actor, "rejected", str(exc), simulation_id)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        _record_audit("simulate-drift-prediction", actor, "rejected", str(exc), simulation_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        _record_audit("simulate-drift-prediction", actor, "rejected", str(exc), simulation_id)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _prediction_response(run)


@app.get("/simulation-predictions", response_model=SimulationPredictionListResponse)
def list_simulation_predictions(
    limit: int = 25,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    return SimulationPredictionListResponse(
        items=[_prediction_response(run) for run in app.state.predictions.list(actor, limit)]
    )


@app.get("/simulation-predictions/{prediction_id}", response_model=SimulationPredictionResponse)
def get_simulation_prediction(
    prediction_id: str,
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    run = app.state.predictions.get(prediction_id)
    if run is None or run.actor != actor:
        raise HTTPException(status_code=404, detail="Prediction run not found.")
    return _prediction_response(run)


@app.get("/simulation-predictions/{prediction_id}/download")
def download_simulation_prediction(
    prediction_id: str,
    format: str = Query(default="parquet", pattern="^(parquet|csv)$"),
    authorization: str | None = Header(default=None),
):
    actor = _require_admin(authorization)
    try:
        run = app.state.predictions.get(prediction_id)
        if run is None or run.actor != actor:
            raise LookupError("Prediction run not found.")
        if format == "csv":
            _run, payload = app.state.predictions.csv_bytes(prediction_id)
            return Response(
                content=payload,
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="simulation-predictions-{prediction_id}.csv"'
                    )
                },
            )
        _run, path = app.state.predictions.download_path(prediction_id)
        return FileResponse(
            path,
            media_type="application/vnd.apache.parquet",
            filename=f"simulation-predictions-{prediction_id}.parquet",
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
