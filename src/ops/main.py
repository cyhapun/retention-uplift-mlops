import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from sqlalchemy import select

from src.db.database import SessionLocal, init_database
from src.db.models import OperationAudit, OperationRun
from src.ops.integrations import (
    get_database_summary,
    get_drift_summary,
    get_metrics,
    get_model_summary,
    get_overview,
    get_service_health,
)
from src.ops.runner import ALLOWED_OPERATIONS, OperationRunner
from src.ops.schemas import OperationResponse, PolicyHistoryResponse
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    ensure_policy_seed()
    app.state.runner = OperationRunner()
    app.state.runner.reconcile_stale_jobs()
    yield
    app.state.runner.shutdown()


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
