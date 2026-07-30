import hashlib
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.constants import FEATURE_COLS
from src.db.database import Base
from src.db.models import SimulationRun
from src.monitoring.simulate_drift import DriftSimulationRequest
from src.ops.simulation_service import SimulationConfig, SimulationService


@pytest.fixture
def simulation_environment(tmp_path, monkeypatch):
    database_engine = create_engine(f"sqlite:///{tmp_path / 'simulation.db'}")
    Base.metadata.create_all(database_engine)
    session_factory = sessionmaker(bind=database_engine, autoflush=False, autocommit=False)
    monkeypatch.setattr("src.ops.simulation_service.SessionLocal", session_factory)

    baseline_path = tmp_path / "baseline.parquet"
    pd.DataFrame({feature: [1.0, 2.0, 3.0] for feature in FEATURE_COLS}).to_parquet(
        baseline_path, index=False
    )
    config = SimulationConfig()
    config.baseline_path = baseline_path
    config.artifact_root = tmp_path / "artifacts"
    config.retention_seconds = 60
    return session_factory, config


def _wait_for_completion(service: SimulationService, simulation_id: str):
    for _ in range(250):
        run = service.get(simulation_id)
        if run and run.status in {"succeeded", "failed", "expired"}:
            return run
        time.sleep(0.02)
    pytest.fail("Simulation did not finish within the test timeout")


def test_simulation_preserves_baseline_and_expires_artifact(simulation_environment):
    session_factory, config = simulation_environment
    baseline_hash_before = hashlib.sha256(config.baseline_path.read_bytes()).hexdigest()
    service = SimulationService(config)
    try:
        run = service.create(DriftSimulationRequest(preset="low", rows=2), "admin")
        completed = _wait_for_completion(service, run.simulation_id)
        assert completed.status == "succeeded"
        artifact = config.artifact_root / completed.artifact_filename
        assert artifact.is_file()
        _, csv_payload = service.csv_bytes(run.simulation_id)
        assert b"f0" in csv_payload
        _, parquet_path = service.download_path(run.simulation_id)
        assert parquet_path == artifact
        assert hashlib.sha256(config.baseline_path.read_bytes()).hexdigest() == baseline_hash_before

        with session_factory() as session:
            stored = session.get(SimulationRun, run.simulation_id)
            stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        assert service.cleanup_expired() == 1
        assert not artifact.exists()
        assert service.get(run.simulation_id).status == "expired"
        with pytest.raises(LookupError):
            service.download_path(run.simulation_id)
    finally:
        service.shutdown()


def test_concurrent_simulation_is_rejected(simulation_environment):
    session_factory, config = simulation_environment
    service = SimulationService(config)
    try:
        with session_factory() as session:
            session.add(
                SimulationRun(
                    simulation_id="active-simulation",
                    actor="admin",
                    status="running",
                    preset="low",
                    rows=2,
                    request_payload={"transformations": []},
                    artifact_filename="active-simulation.parquet",
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                )
            )
            session.commit()
        with pytest.raises(RuntimeError, match="already running"):
            service.create(DriftSimulationRequest(preset="high", rows=2), "admin")
    finally:
        service.shutdown()


def test_restart_recovery_marks_partial_run_failed(simulation_environment):
    session_factory, config = simulation_environment
    service = SimulationService(config)
    config.artifact_root.mkdir(parents=True)
    simulation_id = "partial-simulation"
    (config.artifact_root / f".{simulation_id}.parquet.tmp").write_bytes(b"partial")
    with session_factory() as session:
        session.add(
            SimulationRun(
                simulation_id=simulation_id,
                actor="admin",
                status="running",
                preset="low",
                rows=1,
                request_payload={"transformations": []},
                artifact_filename=f"{simulation_id}.parquet",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
        )
        session.commit()
    try:
        assert service.reconcile_stale_runs() == 1
        assert service.get(simulation_id).status == "failed"
        assert not (config.artifact_root / f".{simulation_id}.parquet.tmp").exists()
    finally:
        service.shutdown()
