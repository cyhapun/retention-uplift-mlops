from fastapi.testclient import TestClient

import src.ops.main as ops_main
from src.policy.schemas import PolicyAction, PolicyDocument
from src.policy.store import policy_config_to_document, validate_policy_document


def sample_policy() -> PolicyDocument:
    return PolicyDocument(
        actions={
            "no_action": PolicyAction(cost=0, min_expected_value=0, min_uplift=0, priority=0),
            "low_cost_email": PolicyAction(
                cost=0.2, min_expected_value=1, min_uplift=0.02, priority=1
            ),
        },
        min_uplift_for_action=0.02,
        max_daily_budget=10000,
    )


def test_policy_document_is_validated_with_business_rules():
    validate_policy_document(sample_policy())


def test_policy_document_rejects_duplicate_offer_priorities():
    policy = sample_policy()
    policy.actions["standard_discount"] = PolicyAction(
        cost=5,
        min_expected_value=5,
        min_uplift=0.1,
        priority=1,
    )

    try:
        validate_policy_document(policy)
    except ValueError as error:
        assert "priorities" in str(error)
    else:
        raise AssertionError("Expected duplicate priorities to be rejected")


def test_policy_endpoint_returns_yaml_fallback_when_store_is_disabled(monkeypatch):
    monkeypatch.setenv("POLICY_STORE_ENABLED", "false")
    monkeypatch.delenv("OPS_ADMIN_TOKEN", raising=False)

    with TestClient(ops_main.app) as client:
        response = client.get("/policy")

    assert response.status_code == 200
    assert response.json()["version_id"] == "yaml-fallback"
    assert response.json()["editable"] is False


def test_policy_validation_endpoint_reports_cross_field_errors(monkeypatch):
    monkeypatch.setenv("POLICY_STORE_ENABLED", "false")
    policy = sample_policy().model_dump(mode="json")
    policy["actions"]["standard_discount"] = {
        "cost": 5,
        "min_expected_value": 5,
        "min_uplift": 0.1,
        "priority": 1,
    }

    with TestClient(ops_main.app) as client:
        response = client.post("/policy/validate", json=policy)

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "priorities" in response.json()["errors"][0]


def test_yaml_policy_can_be_converted_to_api_document():
    from src.policy.config import load_policy_config

    document = policy_config_to_document(load_policy_config())

    assert document.actions["low_cost_email"].cost == 0.2
    assert document.max_daily_budget == 10000


def test_policy_activation_and_rollback_create_versions(monkeypatch):
    monkeypatch.setenv("POLICY_STORE_ENABLED", "true")
    monkeypatch.setenv("OPS_ADMIN_TOKEN", "test-token")

    with TestClient(ops_main.app) as client:
        current = client.get("/policy").json()
        policy = current["policy"]
        policy["actions"]["low_cost_email"]["cost"] = 0.25
        activated = client.post(
            "/policy/activate",
            headers={"authorization": "Bearer test-token"},
            json={
                "policy": policy,
                "expected_version_id": current["version_id"],
                "confirm": True,
                "change_summary": "Test activation",
            },
        )
        assert activated.status_code == 201
        assert activated.json()["version_number"] == current["version_number"] + 1

        history = client.get("/policy/history", headers={"authorization": "Bearer test-token"})
        assert history.status_code == 200
        previous = next(
            item
            for item in history.json()["versions"]
            if item["version_id"] == current["version_id"]
        )

        rolled_back = client.post(
            f"/policy/rollback/{previous['version_id']}",
            headers={"authorization": "Bearer test-token"},
            json={
                "expected_version_id": activated.json()["version_id"],
                "confirm": True,
            },
        )
        assert rolled_back.status_code == 201
        assert rolled_back.json()["version_number"] == activated.json()["version_number"] + 1
