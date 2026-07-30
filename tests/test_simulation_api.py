from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import src.ops.main as ops_main
from src.db.models import SimulationRun


class FakeSimulationService:
    def __init__(self):
        self.run = SimulationRun(
            simulation_id="simulation-1",
            actor="admin",
            status="succeeded",
            preset="low",
            rows=2,
            request_payload={
                "transformations": [{"feature": "f0", "operation": "scale_percent", "value": 15}]
            },
            summary_payload={
                "rows": 2,
                "affected_feature_count": 1,
                "severity": "low",
                "affected_features": [
                    {
                        "feature": "f0",
                        "operation": "scale_percent",
                        "value": 15,
                        "before_mean": 1,
                        "after_mean": 1.15,
                        "before_std": 0,
                        "after_std": 0,
                    }
                ],
            },
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    def shutdown(self):
        return None

    def create(self, _request, _actor):
        return self.run

    def get(self, _simulation_id):
        return self.run

    def list(self, _actor, _limit):
        return [self.run]


def test_simulation_endpoints_require_admin_authorization(monkeypatch):
    monkeypatch.delenv("OPS_ADMIN_TOKEN", raising=False)
    with TestClient(ops_main.app) as client:
        response = client.get("/simulations")
    assert response.status_code == 503


def test_simulation_request_rejects_unknown_feature(monkeypatch):
    monkeypatch.setenv("OPS_ADMIN_TOKEN", "test-token")
    with TestClient(ops_main.app) as client:
        response = client.post(
            "/simulations",
            headers={"authorization": "Bearer test-token"},
            json={
                "preset": None,
                "rows": 100,
                "transformations": [
                    {"feature": "customer_value", "operation": "shift", "value": 1}
                ],
            },
        )
    assert response.status_code == 422


def test_simulation_summary_does_not_expose_internal_path(monkeypatch):
    monkeypatch.setenv("OPS_ADMIN_TOKEN", "test-token")
    with TestClient(ops_main.app) as client:
        ops_main.app.state.simulations = FakeSimulationService()
        response = client.post(
            "/simulations",
            headers={"authorization": "Bearer test-token"},
            json={"preset": "low", "rows": 2},
        )
    assert response.status_code == 202
    payload = response.json()
    assert payload["summary"]["affected_feature_count"] == 1
    assert "artifact" not in payload
    assert "data/" not in response.text
    assert payload["downloads"][0]["url"].startswith("/api/simulations/")
