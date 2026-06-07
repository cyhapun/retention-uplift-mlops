from src.policy.budget_optimizer import optimize_actions_for_budget


def test_budget_optimizer_selects_actions_under_budget():
    candidates = [
        {"user_id": "u1", "uplift_score": 0.25, "customer_value": 200},
        {"user_id": "u2", "uplift_score": 0.12, "customer_value": 100},
        {"user_id": "u3", "uplift_score": 0.03, "customer_value": 100},
    ]

    result = optimize_actions_for_budget(
        candidates=candidates,
        max_budget=20,
    )

    assert result["total_cost"] <= 20
    assert result["n_selected"] >= 1
    assert result["total_expected_incremental_value"] > 0


def test_budget_optimizer_skips_actions_when_budget_exceeded():
    candidates = [
        {"user_id": "u1", "uplift_score": 0.25, "customer_value": 200},
        {"user_id": "u2", "uplift_score": 0.25, "customer_value": 180},
    ]

    result = optimize_actions_for_budget(
        candidates=candidates,
        max_budget=15,
    )

    assert result["n_selected"] == 1
    assert result["n_skipped"] == 1
    assert result["total_cost"] <= 15


def test_budget_optimizer_tracks_no_action_candidates():
    candidates = [
        {"user_id": "u1", "uplift_score": -0.01, "customer_value": 100},
        {"user_id": "u2", "uplift_score": 0.01, "customer_value": 100},
    ]

    result = optimize_actions_for_budget(
        candidates=candidates,
        max_budget=100,
    )

    assert result["n_selected"] == 0
    assert result["n_no_action"] == 2