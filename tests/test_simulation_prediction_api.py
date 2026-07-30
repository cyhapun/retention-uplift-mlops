from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import src.ops.main as ops_main
from src.db.models import SimulationPredictionRun


class FakePredictionService:
    def __init__(self):
        self.run = SimulationPredictionRun(
            prediction_id="prediction-1",
            simulation_id="simulation-1",
            actor="admin",
            status="queued",
            mode="model_only",
            customer_value=None,
            request_payload={"mode": "model_only", "customer_value": None},
            model_reference={
                "model_name": "uplift_model",
                "model_alias": "champion",
                "model_uri": "models:/uplift_model@champion",
                "model_version": "pending",
            },
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    def initialize(self):
        return None

    def shutdown(self):
        return None

    def create(self, _simulation_id, _actor, _request):
        return self.run

    def get(self, _prediction_id):
        return self.run

    def list(self, _actor, _limit):
        return [self.run]


def test_prediction_endpoints_require_admin_authorization(monkeypatch):
    monkeypatch.delenv("OPS_ADMIN_TOKEN", raising=False)
    with TestClient(ops_main.app) as client:
        response = client.get("/simulation-predictions")
    assert response.status_code == 503


def test_policy_prediction_requires_customer_value(monkeypatch):
    monkeypatch.setenv("OPS_ADMIN_TOKEN", "test-token")
    with TestClient(ops_main.app) as client:
        response = client.post(
            "/simulations/simulation-1/predict",
            headers={"authorization": "Bearer test-token"},
            json={"mode": "policy_comparison"},
        )
    assert response.status_code == 422


def test_prediction_response_exposes_only_opaque_download_contract(monkeypatch):
    monkeypatch.setenv("OPS_ADMIN_TOKEN", "test-token")
    with TestClient(ops_main.app) as client:
        ops_main.app.state.predictions = FakePredictionService()
        response = client.post(
            "/simulations/simulation-1/predict",
            headers={"authorization": "Bearer test-token"},
            json={"mode": "model_only"},
        )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert "data/" not in response.text
    assert "model_path" not in response.text
