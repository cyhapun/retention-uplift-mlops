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
from src.ops.schemas import OperationResponse


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
