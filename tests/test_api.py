import pandas as pd
from fastapi.testclient import TestClient

from src.data.constants import FEATURE_COLS
from src.serving.main import create_app


class FakeUpliftModel:
    def predict(self, model_input: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "treatment_probability": 0.25,
                    "control_probability": 0.10,
                    "uplift_score": 0.15,
                }
            ]
        )


def make_payload() -> dict:
    return {
        "user_id": "user_001",
        "customer_value": 100,
        "features": {feature: 0.1 for feature in FEATURE_COLS},
    }


def test_health_endpoint_returns_ok():
    app = create_app(model=FakeUpliftModel())

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_info_endpoint_returns_registry_uri():
    app = create_app(model=FakeUpliftModel())

    with TestClient(app) as client:
        response = client.get("/model-info")

    assert response.status_code == 200

    body = response.json()

    assert body["model_name"] == "uplift_model"
    assert body["model_alias"] == "champion"
    assert body["model_uri"] == "models:/uplift_model@champion"
    assert body["model_loaded"] is True


def test_decide_action_endpoint_returns_decision():
    app = create_app(model=FakeUpliftModel())

    with TestClient(app) as client:
        response = client.post("/decide-action", json=make_payload())

    assert response.status_code == 200

    body = response.json()

    assert body["user_id"] == "user_001"
    assert body["treatment_probability"] == 0.25
    assert body["control_probability"] == 0.10
    assert body["uplift_score"] == 0.15
    assert body["customer_value"] == 100
    assert body["recommended_action"] == "standard_discount"
    assert body["expected_incremental_value"] == 10.0
    assert body["model_name"] == "uplift_model"
    assert body["model_alias"] == "champion"
    assert "decision_id" in body

def test_decide_action_endpoint_rejects_missing_features():
    app = create_app(model=FakeUpliftModel())
    payload = make_payload()
    payload["features"].pop("f0")

    with TestClient(app) as client:
        response = client.post("/decide-action", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Missing required features."
    assert response.json()["detail"]["missing_features"] == ["f0"]