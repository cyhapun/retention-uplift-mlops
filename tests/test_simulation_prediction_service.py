import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.data.constants import FEATURE_COLS
from src.db.database import Base
from src.db.models import DecisionLog, FeedbackLog, SimulationPredictionRun, SimulationRun
from src.ops.simulation_prediction import SimulationPredictionRequest
from src.ops.simulation_prediction_service import SimulationPredictionService
from src.ops.simulation_service import SimulationConfig
from src.policy.config import load_policy_config


class FakeModel:
    metadata = SimpleNamespace(run_id="fake-model-version")

    def predict(self, frame):
        uplift = frame["f0"].astype(float) * 0.01
        return pd.DataFrame(
            {
                "treatment_probability": 0.5 + uplift,
                "control_probability": 0.5,
                "uplift_score": uplift,
            }
        )


@pytest.fixture
def prediction_environment(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'prediction.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr("src.ops.simulation_prediction_service.SessionLocal", session_factory)
    monkeypatch.setattr(
        "src.ops.simulation_prediction_service.load_champion_model",
        lambda **_kwargs: FakeModel(),
    )
    monkeypatch.setattr(
        "src.ops.simulation_prediction_service.get_active_policy",
        lambda: (load_policy_config(), None),
    )

    baseline = pd.DataFrame({feature: [1.0, 2.0, 3.0] for feature in FEATURE_COLS})
    baseline_path = tmp_path / "baseline.parquet"
    artifact_path = tmp_path / "simulation.parquet"
    baseline.to_parquet(baseline_path, index=False)
    simulated = baseline.copy()
    simulated["f0"] = [2.0, 3.0, 4.0]
    simulated.to_parquet(artifact_path, index=False)

    config = SimulationConfig()
    config.baseline_path = baseline_path
    config.artifact_root = tmp_path
    config.retention_seconds = 60
    simulations = SimpleNamespace(config=config, artifact_path=lambda _run: artifact_path)
    with session_factory() as session:
        session.add(
            SimulationRun(
                simulation_id="simulation-1",
                actor="admin",
                status="succeeded",
                preset="low",
                rows=3,
                request_payload={"transformations": []},
                artifact_filename="simulation.parquet",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
        )
        session.commit()
    return session_factory, simulations


def wait_for_result(service, prediction_id):
    for _ in range(100):
        result = service.get(prediction_id)
        if result and result.status in {"succeeded", "failed", "expired"}:
            return result
        time.sleep(0.02)
    pytest.fail("Prediction did not finish within the test timeout")


def test_model_only_prediction_isolated_from_production_logs(prediction_environment):
    session_factory, simulations = prediction_environment
    service = SimulationPredictionService(simulations)
    try:
        run = service.create("simulation-1", "admin", SimulationPredictionRequest())
        completed = wait_for_result(service, run.prediction_id)
        assert completed.status == "succeeded", completed.error_summary
        assert completed.summary_payload["mode"] == "model_only"
        assert completed.summary_payload["recommendation_changed_count"] is None
        assert service.download_path(run.prediction_id)[1].is_file()
        with session_factory() as session:
            assert session.scalars(select(DecisionLog)).all() == []
            assert session.scalars(select(FeedbackLog)).all() == []
    finally:
        service.shutdown()


def test_policy_prediction_persists_comparison_and_expiry_cleanup(prediction_environment):
    session_factory, simulations = prediction_environment
    service = SimulationPredictionService(simulations)
    try:
        request = SimulationPredictionRequest(mode="policy_comparison", customer_value=100)
        run = service.create("simulation-1", "admin", request)
        completed = wait_for_result(service, run.prediction_id)
        assert completed.status == "succeeded", completed.error_summary
        assert completed.policy_config_hash
        assert completed.summary_payload["baseline_action_distribution"]
        _, csv_payload = service.csv_bytes(run.prediction_id)
        assert b"baseline_uplift_score" in csv_payload

        with session_factory() as session:
            stored = session.get(SimulationPredictionRun, run.prediction_id)
            stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        assert service.cleanup_expired() == 1
        assert service.get(run.prediction_id).status == "expired"
        with pytest.raises(LookupError):
            service.download_path(run.prediction_id)
    finally:
        service.shutdown()
