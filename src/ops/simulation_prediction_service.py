"""Lifecycle service for isolated model predictions over synthetic simulations."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Lock
from uuid import uuid4

import pandas as pd
from sqlalchemy import select

from src.db.database import SessionLocal
from src.db.models import OperationAudit, SimulationPredictionRun, SimulationRun
from src.ops.simulation_prediction import (
    PredictionComparisonSummary,
    PredictionModelReference,
    SimulationPredictionRequest,
    compare_predictions,
)
from src.ops.simulation_service import SimulationConfig, _utc_datetime, utc_now
from src.policy.config import ActionConfig, PolicyConfig
from src.policy.store import get_active_policy, policy_config_to_dict


class SimulationPredictionService:
    def __init__(self, simulations, config: SimulationConfig | None = None) -> None:
        self.simulations = simulations
        self.config = config or simulations.config
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="retentionops-prediction"
        )
        self.lock = Lock()

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)

    def initialize(self) -> None:
        self.config.artifact_root.mkdir(parents=True, exist_ok=True)
        self.reconcile_stale_runs()
        self.cleanup_expired()

    def reconcile_stale_runs(self) -> int:
        reconciled = 0
        with SessionLocal() as session:
            runs = session.scalars(
                select(SimulationPredictionRun).where(
                    SimulationPredictionRun.status.in_(["queued", "running"])
                )
            ).all()
            for run in runs:
                self._remove_artifact(run)
                run.status = "failed"
                run.finished_at = utc_now()
                run.error_summary = (
                    "Control plane restarted before prediction completion could be verified."
                )
                reconciled += 1
            if reconciled:
                session.commit()
        return reconciled

    def cleanup_expired(self) -> int:
        expired = 0
        now = utc_now()
        with SessionLocal() as session:
            runs = session.scalars(
                select(SimulationPredictionRun).where(
                    SimulationPredictionRun.status == "succeeded",
                    SimulationPredictionRun.expires_at <= now,
                )
            ).all()
            for run in runs:
                self._remove_artifact(run)
                run.status = "expired"
                run.finished_at = run.finished_at or now
                expired += 1
            if expired:
                session.commit()
        return expired

    def create(
        self,
        simulation_id: str,
        actor: str,
        request: SimulationPredictionRequest,
    ) -> SimulationPredictionRun:
        with self.lock:
            self.cleanup_expired()
            with SessionLocal() as session:
                simulation = session.get(SimulationRun, simulation_id)
                if simulation is None:
                    raise LookupError("Simulation not found.")
                if simulation.actor != actor:
                    raise LookupError("Simulation not found.")
                if simulation.status != "succeeded":
                    raise ValueError("A completed simulation is required before prediction.")
                if _utc_datetime(simulation.expires_at) <= utc_now():
                    raise ValueError("The selected simulation has expired. Create a new scenario.")
                if not self.simulations.artifact_path(simulation).is_file():
                    raise ValueError("The selected simulation artifact is unavailable.")
                if simulation.rows > self.config.max_prediction_rows:
                    raise ValueError("The simulation exceeds the prediction row limit.")
                active = session.scalar(
                    select(SimulationPredictionRun).where(
                        SimulationPredictionRun.status.in_(["queued", "running"])
                    )
                )
                if active is not None:
                    raise RuntimeError(f"A prediction is already running: {active.prediction_id}")

                policy_payload = None
                policy_version_id = None
                policy_hash = None
                if request.mode == "policy_comparison":
                    policy_config, policy_version = get_active_policy()
                    policy_payload = policy_config_to_dict(policy_config)
                    policy_version_id = policy_version.version_id if policy_version else None
                    policy_hash = hashlib.sha256(
                        json.dumps(policy_payload, sort_keys=True).encode("utf-8")
                    ).hexdigest()

                prediction_id = str(uuid4())
                created_at = utc_now()
                model_name = os.getenv("UPLIFT_MODEL_NAME", "uplift_model")
                model_alias = os.getenv("UPLIFT_MODEL_ALIAS", "champion")
                run = SimulationPredictionRun(
                    prediction_id=prediction_id,
                    simulation_id=simulation_id,
                    actor=actor,
                    status="queued",
                    mode=request.mode,
                    customer_value=request.customer_value,
                    request_payload={
                        "mode": request.mode,
                        "customer_value": request.customer_value,
                        "policy_config": policy_payload,
                    },
                    model_reference={
                        "model_name": model_name,
                        "model_alias": model_alias,
                        "model_uri": f"models:/{model_name}@{model_alias}",
                        "model_version": "pending",
                    },
                    policy_version_id=policy_version_id,
                    policy_config_hash=policy_hash,
                    artifact_filename=f"{prediction_id}.parquet",
                    created_at=created_at,
                    expires_at=min(
                        _utc_datetime(simulation.expires_at),
                        created_at + timedelta(seconds=self.config.retention_seconds),
                    ),
                )
                session.add(run)
                session.add(
                    OperationAudit(
                        audit_id=str(uuid4()),
                        operation_id=prediction_id,
                        operation="simulate-drift-prediction",
                        actor=actor,
                        status="accepted",
                        outcome=f"Prediction queued for simulation {simulation_id}.",
                    )
                )
                session.commit()
                session.refresh(run)
                self.executor.submit(self._run, prediction_id, request, policy_payload)
                return run

    def get(self, prediction_id: str) -> SimulationPredictionRun | None:
        self.cleanup_expired()
        with SessionLocal() as session:
            run = session.get(SimulationPredictionRun, prediction_id)
            if run is None:
                return None
            session.expunge(run)
            return run

    def list(self, actor: str, limit: int = 25) -> list[SimulationPredictionRun]:
        self.cleanup_expired()
        with SessionLocal() as session:
            runs = session.scalars(
                select(SimulationPredictionRun)
                .where(SimulationPredictionRun.actor == actor)
                .order_by(SimulationPredictionRun.created_at.desc())
                .limit(min(max(limit, 1), 100))
            ).all()
            for run in runs:
                session.expunge(run)
            return runs

    def artifact_path(self, run: SimulationPredictionRun) -> Path:
        if not run.artifact_filename or Path(run.artifact_filename).name != run.artifact_filename:
            raise LookupError("Prediction result is unavailable.")
        return self.config.artifact_root / run.artifact_filename

    def download_path(self, prediction_id: str) -> tuple[SimulationPredictionRun, Path]:
        run = self.get(prediction_id)
        if run is None:
            raise LookupError("Prediction run not found.")
        if run.status != "succeeded" or _utc_datetime(run.expires_at) <= utc_now():
            raise LookupError("This prediction result has expired or is not ready for download.")
        path = self.artifact_path(run)
        if not path.is_file():
            raise LookupError("Prediction result is unavailable.")
        self._record_download(run)
        return run, path

    def csv_bytes(self, prediction_id: str) -> tuple[SimulationPredictionRun, bytes]:
        run, path = self.download_path(prediction_id)
        payload = pd.read_parquet(path).to_csv(index=False).encode("utf-8")
        if len(payload) > self.config.max_csv_bytes:
            raise ValueError("The CSV download exceeds the configured size limit.")
        return run, payload

    def _run(
        self, prediction_id, request: SimulationPredictionRequest, policy_payload: dict | None
    ) -> None:
        with SessionLocal() as session:
            run = session.get(SimulationPredictionRun, prediction_id)
            if run is None:
                return
            simulation = session.get(SimulationRun, run.simulation_id)
            if simulation is None:
                self._finish_failure(prediction_id, "The source simulation is unavailable.")
                return
            simulation_rows = simulation.rows
            simulation_artifact = self.simulations.artifact_path(simulation)
            run.status = "running"
            run.started_at = utc_now()
            session.commit()

        final_path = self.config.artifact_root / f"{prediction_id}.parquet"
        temporary_path = self.config.artifact_root / f".{prediction_id}.parquet.tmp"
        try:
            baseline = pd.read_parquet(self.config.baseline_path)
            simulated = pd.read_parquet(simulation_artifact)
            rows = simulation_rows
            if rows > self.config.max_prediction_rows:
                raise ValueError("The simulation exceeds the prediction row limit.")
            baseline = baseline.iloc[:rows].copy(deep=True)
            simulated = simulated.iloc[:rows].copy(deep=True)
            model_name = os.getenv("UPLIFT_MODEL_NAME", "uplift_model")
            model_alias = os.getenv("UPLIFT_MODEL_ALIAS", "champion")
            model = load_champion_model(model_name=model_name, model_alias=model_alias)
            model_version = _model_version(model)
            model_reference = PredictionModelReference(
                model_name=model_name,
                model_alias=model_alias,
                model_uri=f"models:/{model_name}@{model_alias}",
                model_version=model_version,
            )
            policy_config = _policy_config_from_payload(policy_payload) if policy_payload else None
            comparison = compare_predictions(
                model,
                baseline,
                simulated,
                model_reference,
                request,
                policy_config,
            )
            comparison.rows.to_parquet(temporary_path, index=False)
            if temporary_path.stat().st_size > self.config.max_prediction_file_bytes:
                raise ValueError("The prediction result exceeds the configured file size limit.")
            temporary_path.replace(final_path)
            self._finish_success(prediction_id, comparison.summary, final_path.stat().st_size)
        except FileNotFoundError:
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            self._finish_failure(
                prediction_id, "The model, baseline, or simulation artifact is unavailable."
            )
        except Exception as exc:  # Keep worker failures observable instead of leaving runs running.
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            self._finish_failure(prediction_id, str(exc)[:500] or "Prediction failed.")

    def _finish_success(
        self, prediction_id: str, summary: PredictionComparisonSummary, size: int
    ) -> None:
        with SessionLocal() as session:
            run = session.get(SimulationPredictionRun, prediction_id)
            if run is None:
                return
            run.status = "succeeded"
            run.model_reference = summary.model.model_dump()
            run.summary_payload = summary.model_dump()
            run.artifact_size_bytes = size
            run.finished_at = utc_now()
            session.commit()

    def _finish_failure(self, prediction_id: str, message: str) -> None:
        with SessionLocal() as session:
            run = session.get(SimulationPredictionRun, prediction_id)
            if run is None:
                return
            run.status = "failed"
            run.error_summary = message
            run.finished_at = utc_now()
            session.add(
                OperationAudit(
                    audit_id=str(uuid4()),
                    operation_id=prediction_id,
                    operation="simulate-drift-prediction",
                    actor=run.actor,
                    status="failed",
                    outcome=message,
                )
            )
            session.commit()

    def _record_download(self, run: SimulationPredictionRun) -> None:
        with SessionLocal() as session:
            session.add(
                OperationAudit(
                    audit_id=str(uuid4()),
                    operation_id=run.prediction_id,
                    operation="simulate-drift-prediction-download",
                    actor=run.actor,
                    status="downloaded",
                    outcome=f"Prediction result downloaded for simulation {run.simulation_id}.",
                )
            )
            session.commit()

    def _remove_artifact(self, run: SimulationPredictionRun) -> None:
        if run.artifact_filename:
            self.artifact_path(run).unlink(missing_ok=True)
            (self.config.artifact_root / f".{run.artifact_filename}.tmp").unlink(missing_ok=True)


def _model_version(model) -> str:
    metadata = getattr(model, "metadata", None)
    run_id = getattr(metadata, "run_id", None) if metadata is not None else None
    return str(run_id) if run_id else "unknown"


def load_champion_model(model_name: str, model_alias: str):
    from src.serving.model_loader import load_uplift_model

    return load_uplift_model(model_name=model_name, model_alias=model_alias)


def _policy_config_from_payload(payload: dict) -> PolicyConfig:
    actions = {
        name: ActionConfig(
            name=name,
            cost=float(values["cost"]),
            min_expected_value=float(values["min_expected_value"]),
            min_uplift=float(values["min_uplift"]),
            priority=int(values["priority"]),
        )
        for name, values in payload["actions"].items()
    }
    return PolicyConfig(
        actions=actions,
        min_uplift_for_action=float(payload["min_uplift_for_action"]),
        max_daily_budget=float(payload["max_daily_budget"]),
    )
