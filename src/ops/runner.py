import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from sqlalchemy import select

from src.db.database import SessionLocal
from src.db.models import OperationRun
from src.demo_config import demo_local_history_enabled

ALLOWED_OPERATIONS = {
    "train-uplift": ["python", "-m", "src.models.train_uplift_model"],
    "register-uplift": ["python", "-m", "src.models.register_uplift_model"],
    "drift-report": [
        "python",
        "-m",
        "src.monitoring.drift_report",
        "--current-path",
        "data/processed/test.parquet",
        "--report-name",
        "data_drift_report",
    ],
    "simulate-drift": ["python", "-m", "src.monitoring.simulate_drift"],
    "simulate-feedback": [
        "python",
        "-m",
        "src.feedback.simulate_feedback",
        "--limit",
        "1000",
        "--feedback-delay-days",
        "7",
    ],
}


class OperationRunner:
    def __init__(self, demo_local: bool | None = None) -> None:
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="retentionops-job")
        self.lock = Lock()
        self.timeout_seconds = int(os.getenv("OPS_JOB_TIMEOUT_SECONDS", "3600"))
        self.demo_local = demo_local_history_enabled() if demo_local is None else demo_local
        self._runs: dict[str, OperationRun] = {}

    def reconcile_stale_jobs(self) -> int:
        """Mark jobs from a previous control-plane process as unverified failures."""
        if self.demo_local:
            return 0
        reconciled = 0
        with SessionLocal() as session:
            stale_jobs = session.scalars(
                select(OperationRun).where(OperationRun.status.in_(["queued", "running"]))
            ).all()
            for operation_run in stale_jobs:
                operation_run.status = "failed"
                operation_run.finished_at = datetime.now(timezone.utc)
                operation_run.error_summary = (
                    "Control plane restarted before job completion could be verified."
                )
                reconciled += 1
            if reconciled:
                session.commit()
        return reconciled

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)

    def start(self, operation: str, actor: str) -> OperationRun:
        if self.demo_local and operation == "simulate-feedback":
            raise ValueError(
                "Delayed feedback is simulated in the browser in demo-local history mode."
            )
        command = ALLOWED_OPERATIONS.get(operation)
        if command is None:
            raise ValueError(f"Unsupported operation: {operation}")

        with self.lock:
            if self.demo_local:
                running = next(
                    (item for item in self._runs.values() if item.status == "running"), None
                )
                if running is not None:
                    raise RuntimeError(f"Operation already running: {running.operation_id}")
                operation_run = OperationRun(
                    operation_id=str(uuid4()),
                    operation=operation,
                    actor=actor,
                    status="queued",
                    command_summary=" ".join(command),
                    created_at=datetime.now(timezone.utc),
                )
                self._runs[operation_run.operation_id] = operation_run
                self.executor.submit(self._run, operation_run.operation_id, command)
                return operation_run
            with SessionLocal() as session:
                running = session.scalar(
                    select(OperationRun).where(OperationRun.status == "running")
                )
                if running is not None:
                    raise RuntimeError(f"Operation already running: {running.operation_id}")

                operation_run = OperationRun(
                    operation_id=str(uuid4()),
                    operation=operation,
                    actor=actor,
                    status="queued",
                    command_summary=" ".join(command),
                )
                session.add(operation_run)
                session.commit()
                session.refresh(operation_run)
                operation_id = operation_run.operation_id

        self.executor.submit(self._run, operation_id, command)
        return operation_run

    def _run(self, operation_id: str, command: list[str]) -> None:
        if self.demo_local:
            operation_run = self._runs.get(operation_id)
            if operation_run is None:
                return
            operation_run.status = "running"
            operation_run.started_at = datetime.now(timezone.utc)
            self._run_process(operation_id, command)
            return
        with SessionLocal() as session:
            operation_run = session.get(OperationRun, operation_id)
            if operation_run is None:
                return
            operation_run.status = "running"
            operation_run.started_at = datetime.now(timezone.utc)
            session.commit()

        self._run_process(operation_id, command)

    def _run_process(self, operation_id: str, command: list[str]) -> None:
        try:
            process = subprocess.run(
                command,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            output = (process.stdout + "\n" + process.stderr).strip()
            status = "succeeded" if process.returncode == 0 else "failed"
            error_summary = None if process.returncode == 0 else output[-1000:]
            self._finish(
                operation_id=operation_id,
                status=status,
                exit_code=process.returncode,
                output_tail=output[-8000:],
                error_summary=error_summary,
            )
        except subprocess.TimeoutExpired as exc:
            self._finish(
                operation_id=operation_id,
                status="failed",
                exit_code=None,
                output_tail=str(exc)[-8000:],
                error_summary="Operation timed out.",
            )
        except OSError as exc:
            self._finish(
                operation_id=operation_id,
                status="failed",
                exit_code=None,
                output_tail=str(exc)[-8000:],
                error_summary="Operation could not be started.",
            )

    def _finish(
        self,
        operation_id: str,
        status: str,
        exit_code: int | None,
        output_tail: str,
        error_summary: str | None,
    ) -> None:
        if self.demo_local:
            operation_run = self._runs.get(operation_id)
            if operation_run is None:
                return
            operation_run.status = status
            operation_run.exit_code = exit_code
            operation_run.output_tail = output_tail
            operation_run.error_summary = error_summary
            operation_run.finished_at = datetime.now(timezone.utc)
            return
        with SessionLocal() as session:
            operation_run = session.get(OperationRun, operation_id)
            if operation_run is None:
                return
            operation_run.status = status
            operation_run.exit_code = exit_code
            operation_run.output_tail = output_tail
            operation_run.error_summary = error_summary
            operation_run.finished_at = datetime.now(timezone.utc)
            session.commit()

    def list(self, actor: str | None = None, limit: int = 25) -> list[OperationRun]:
        if not self.demo_local:
            with SessionLocal() as session:
                statement = (
                    select(OperationRun).order_by(OperationRun.created_at.desc()).limit(limit)
                )
                if actor:
                    statement = statement.where(OperationRun.actor == actor)
                return list(session.scalars(statement).all())
        items = list(self._runs.values())
        if actor:
            items = [item for item in items if item.actor == actor]
        return sorted(items, key=lambda item: item.created_at or datetime.min, reverse=True)[:limit]

    def get(self, operation_id: str) -> OperationRun | None:
        if self.demo_local:
            return self._runs.get(operation_id)
        with SessionLocal() as session:
            item = session.get(OperationRun, operation_id)
            if item is not None:
                session.expunge(item)
            return item
