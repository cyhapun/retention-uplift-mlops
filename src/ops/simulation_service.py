"""Control-plane service for temporary drift simulation artifacts."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

import pandas as pd
from sqlalchemy import select

from src.db.database import SessionLocal
from src.db.models import OperationAudit, SimulationRun
from src.demo_config import demo_local_history_enabled
from src.monitoring.simulate_drift import (
    DriftSimulationRequest,
    DriftSimulationSummary,
    generate_drift_dataset,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SimulationConfig:
    def __init__(self) -> None:
        self.baseline_path = Path(
            os.getenv("DRIFT_SIMULATION_BASELINE_PATH", "data/processed/test.parquet")
        )
        self.artifact_root = Path(
            os.getenv("DRIFT_SIMULATION_ARTIFACT_ROOT", "data/.simulation_artifacts")
        )
        self.retention_seconds = _bounded_int(
            "DRIFT_SIMULATION_RETENTION_SECONDS", 3600, minimum=60, maximum=604800
        )
        self.max_file_bytes = _bounded_int(
            "DRIFT_SIMULATION_MAX_FILE_BYTES",
            50 * 1024 * 1024,
            minimum=1024,
            maximum=500 * 1024 * 1024,
        )
        self.max_csv_bytes = _bounded_int(
            "DRIFT_SIMULATION_MAX_CSV_BYTES",
            100 * 1024 * 1024,
            minimum=1024,
            maximum=500 * 1024 * 1024,
        )
        self.prediction_batch_size = _bounded_int(
            "DRIFT_SIMULATION_PREDICTION_BATCH_SIZE", 10_000, minimum=100, maximum=50_000
        )
        self.max_prediction_rows = _bounded_int(
            "DRIFT_SIMULATION_MAX_PREDICTION_ROWS", 100_000, minimum=1, maximum=100_000
        )
        self.max_prediction_file_bytes = _bounded_int(
            "DRIFT_SIMULATION_MAX_PREDICTION_FILE_BYTES",
            100 * 1024 * 1024,
            minimum=1024,
            maximum=500 * 1024 * 1024,
        )


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


class SimulationService:
    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="retentionops-simulation"
        )
        self.lock = Lock()
        self.demo_local = demo_local_history_enabled()
        self._runs: dict[str, SimulationRun] = {}

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)

    def initialize(self) -> None:
        self.config.artifact_root.mkdir(parents=True, exist_ok=True)
        self.reconcile_stale_runs()
        self.cleanup_expired()

    def reconcile_stale_runs(self) -> int:
        if self.demo_local:
            return 0
        reconciled = 0
        with SessionLocal() as session:
            stale_runs = session.scalars(
                select(SimulationRun).where(SimulationRun.status.in_(["queued", "running"]))
            ).all()
            for run in stale_runs:
                self._remove_artifacts(run)
                run.status = "failed"
                run.finished_at = utc_now()
                run.error_summary = (
                    "Control plane restarted before simulation completion could be verified."
                )
                reconciled += 1
            if reconciled:
                session.commit()
        return reconciled

    def cleanup_expired(self) -> int:
        expired = 0
        now = utc_now()
        if self.demo_local:
            for run in self._runs.values():
                if run.status == "succeeded" and _utc_datetime(run.expires_at) <= now:
                    self._remove_artifacts(run)
                    run.status = "expired"
                    run.finished_at = run.finished_at or now
                    expired += 1
            return expired
        with SessionLocal() as session:
            runs = session.scalars(
                select(SimulationRun).where(
                    SimulationRun.status == "succeeded", SimulationRun.expires_at <= now
                )
            ).all()
            for run in runs:
                self._remove_artifacts(run)
                run.status = "expired"
                run.finished_at = run.finished_at or now
                expired += 1
            if expired:
                session.commit()
        return expired

    def create(self, request: DriftSimulationRequest, actor: str) -> SimulationRun:
        transformations = request.resolved_transformations()
        with self.lock:
            self.cleanup_expired()
            if self.demo_local:
                active = next(
                    (item for item in self._runs.values() if item.status in {"queued", "running"}),
                    None,
                )
                if active is not None:
                    raise RuntimeError(f"A simulation is already running: {active.simulation_id}")
                simulation_id = str(uuid4())
                created_at = utc_now()
                run = SimulationRun(
                    simulation_id=simulation_id,
                    actor=actor,
                    status="queued",
                    preset=request.preset,
                    rows=request.rows,
                    request_payload={
                        "preset": request.preset,
                        "rows": request.rows,
                        "transformations": [item.model_dump() for item in transformations],
                    },
                    artifact_filename=f"{simulation_id}.parquet",
                    created_at=created_at,
                    expires_at=created_at + timedelta(seconds=self.config.retention_seconds),
                )
                self._runs[simulation_id] = run
                self.executor.submit(self._run, simulation_id, request)
                return run
            with SessionLocal() as session:
                active = session.scalar(
                    select(SimulationRun).where(SimulationRun.status.in_(["queued", "running"]))
                )
                if active is not None:
                    raise RuntimeError(f"A simulation is already running: {active.simulation_id}")

                simulation_id = str(uuid4())
                created_at = utc_now()
                run = SimulationRun(
                    simulation_id=simulation_id,
                    actor=actor,
                    status="queued",
                    preset=request.preset,
                    rows=request.rows,
                    request_payload={
                        "preset": request.preset,
                        "rows": request.rows,
                        "transformations": [item.model_dump() for item in transformations],
                    },
                    artifact_filename=f"{simulation_id}.parquet",
                    created_at=created_at,
                    expires_at=created_at + timedelta(seconds=self.config.retention_seconds),
                )
                session.add(run)
                session.add(
                    OperationAudit(
                        audit_id=str(uuid4()),
                        operation_id=simulation_id,
                        operation="simulate-drift",
                        actor=actor,
                        status="accepted",
                        outcome="Simulation queued.",
                    )
                )
                session.commit()
                session.refresh(run)
                self.executor.submit(self._run, simulation_id, request)
                return run

    def get(self, simulation_id: str) -> SimulationRun | None:
        self.cleanup_expired()
        if self.demo_local:
            return self._runs.get(simulation_id)
        with SessionLocal() as session:
            run = session.get(SimulationRun, simulation_id)
            if run is None:
                return None
            session.expunge(run)
            return run

    def list(self, actor: str | None = None, limit: int = 25) -> list[SimulationRun]:
        self.cleanup_expired()
        if self.demo_local:
            runs = list(self._runs.values())
            if actor:
                runs = [run for run in runs if run.actor == actor]
            return sorted(runs, key=lambda run: run.created_at or utc_now(), reverse=True)[:limit]
        with SessionLocal() as session:
            statement = select(SimulationRun).order_by(SimulationRun.created_at.desc())
            if actor:
                statement = statement.where(SimulationRun.actor == actor)
            runs = session.scalars(statement.limit(min(max(limit, 1), 100))).all()
            for run in runs:
                session.expunge(run)
            return runs

    def artifact_path(self, run: SimulationRun) -> Path:
        if not run.artifact_filename or Path(run.artifact_filename).name != run.artifact_filename:
            raise LookupError("Simulation artifact is unavailable.")
        return self.config.artifact_root / run.artifact_filename

    def download_path(self, simulation_id: str) -> tuple[SimulationRun, Path]:
        run = self.get(simulation_id)
        if run is None:
            raise LookupError("Simulation not found.")
        if run.status != "succeeded" or _utc_datetime(run.expires_at) <= utc_now():
            raise LookupError("This simulation has expired or is not ready for download.")
        path = self.artifact_path(run)
        if not path.is_file():
            raise LookupError("Simulation artifact is unavailable.")
        self._record_download(run)
        return run, path

    def csv_bytes(self, simulation_id: str) -> tuple[SimulationRun, bytes]:
        run, path = self.download_path(simulation_id)
        frame = pd.read_parquet(path)
        payload = frame.to_csv(index=False).encode("utf-8")
        if len(payload) > self.config.max_csv_bytes:
            raise ValueError("The CSV download exceeds the configured size limit.")
        return run, payload

    def _record_download(self, run: SimulationRun) -> None:
        if self.demo_local:
            return
        with SessionLocal() as session:
            session.add(
                OperationAudit(
                    audit_id=str(uuid4()),
                    operation_id=run.simulation_id,
                    operation="simulate-drift-download",
                    actor=run.actor,
                    status="downloaded",
                    outcome="Simulation artifact downloaded.",
                )
            )
            session.commit()

    def _run(self, simulation_id: str, request: DriftSimulationRequest) -> None:
        if self.demo_local:
            run = self._runs.get(simulation_id)
            if run is None:
                return
            run.status = "running"
            run.started_at = utc_now()
            self._run_generation(simulation_id, request)
            return
        with SessionLocal() as session:
            run = session.get(SimulationRun, simulation_id)
            if run is None:
                return
            run.status = "running"
            run.started_at = utc_now()
            session.commit()

        self._run_generation(simulation_id, request)

    def _run_generation(self, simulation_id: str, request: DriftSimulationRequest) -> None:
        final_path = self.config.artifact_root / f"{simulation_id}.parquet"
        temporary_path = self.config.artifact_root / f".{simulation_id}.parquet.tmp"
        try:
            self.config.artifact_root.mkdir(parents=True, exist_ok=True)
            if not self.config.baseline_path.is_file():
                raise FileNotFoundError
            baseline = pd.read_parquet(self.config.baseline_path)
            generated = generate_drift_dataset(baseline, request)
            generated.dataframe.to_parquet(temporary_path, index=False)
            if temporary_path.stat().st_size > self.config.max_file_bytes:
                raise ValueError("The generated dataset exceeds the configured file size limit.")
            temporary_path.replace(final_path)
            self._finish_success(simulation_id, generated.summary, final_path.stat().st_size)
        except FileNotFoundError:
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            self._finish_failure(simulation_id, "The configured baseline dataset is unavailable.")
        except Exception as exc:  # Keep a worker failure from leaving a run stuck as running.
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            self._finish_failure(simulation_id, str(exc)[:500] or "Simulation generation failed.")

    def _finish_success(
        self, simulation_id: str, summary: DriftSimulationSummary, size: int
    ) -> None:
        if self.demo_local:
            run = self._runs.get(simulation_id)
            if run is None:
                return
            run.status = "succeeded"
            run.summary_payload = summary.model_dump()
            run.artifact_size_bytes = size
            run.finished_at = utc_now()
            return
        with SessionLocal() as session:
            run = session.get(SimulationRun, simulation_id)
            if run is None:
                return
            run.status = "succeeded"
            run.summary_payload = summary.model_dump()
            run.artifact_size_bytes = size
            run.finished_at = utc_now()
            session.commit()

    def _finish_failure(self, simulation_id: str, message: str) -> None:
        if self.demo_local:
            run = self._runs.get(simulation_id)
            if run is None:
                return
            run.status = "failed"
            run.error_summary = message
            run.finished_at = utc_now()
            return
        with SessionLocal() as session:
            run = session.get(SimulationRun, simulation_id)
            if run is None:
                return
            run.status = "failed"
            run.error_summary = message
            run.finished_at = utc_now()
            session.add(
                OperationAudit(
                    audit_id=str(uuid4()),
                    operation_id=simulation_id,
                    operation="simulate-drift",
                    actor=run.actor,
                    status="failed",
                    outcome=message,
                )
            )
            session.commit()

    def _remove_artifacts(self, run: SimulationRun) -> None:
        if run.artifact_filename:
            self.artifact_path(run).unlink(missing_ok=True)
            (self.config.artifact_root / f".{run.artifact_filename}.tmp").unlink(missing_ok=True)
