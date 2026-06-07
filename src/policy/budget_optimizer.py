from src.policy.config import PolicyConfig, load_policy_config
from src.policy.decision_engine import recommend_action_from_policy


def optimize_actions_for_budget(
    candidates: list[dict],
    max_budget: float | None = None,
    policy_config: PolicyConfig | None = None,
) -> dict:
    """
    Select recommended actions under a budget constraint.

    Each candidate should contain:
    - user_id
    - uplift_score
    - customer_value
    """
    if policy_config is None:
        policy_config = load_policy_config()

    if max_budget is None:
        max_budget = policy_config.max_daily_budget

    if max_budget < 0:
        raise ValueError("max_budget must be greater than or equal to 0.")

    scored_candidates = []

    for candidate in candidates:
        decision = recommend_action_from_policy(
            uplift_score=float(candidate["uplift_score"]),
            customer_value=float(candidate["customer_value"]),
            policy_config=policy_config,
        )

        scored_candidates.append(
            {
                **candidate,
                **decision,
            }
        )

    actionable_candidates = [
        candidate
        for candidate in scored_candidates
        if candidate["recommended_action"] != "no_action"
        and candidate["expected_incremental_value"] > 0
        and candidate["treatment_cost"] > 0
    ]

    actionable_candidates.sort(
        key=lambda candidate: (
            candidate["expected_incremental_value"],
            candidate["roi"],
        ),
        reverse=True,
    )

    selected_actions = []
    skipped_actions = []
    total_cost = 0.0
    total_expected_incremental_value = 0.0

    for candidate in actionable_candidates:
        next_cost = total_cost + candidate["treatment_cost"]

        if next_cost <= max_budget:
            selected_actions.append(candidate)
            total_cost = next_cost
            total_expected_incremental_value += candidate["expected_incremental_value"]
        else:
            skipped_actions.append({**candidate, "skip_reason": "budget_exceeded"})

    no_action_candidates = [
        candidate for candidate in scored_candidates if candidate["recommended_action"] == "no_action"
    ]

    return {
        "selected_actions": selected_actions,
        "skipped_actions": skipped_actions,
        "no_action_candidates": no_action_candidates,
        "max_budget": max_budget,
        "total_cost": total_cost,
        "remaining_budget": max_budget - total_cost,
        "total_expected_incremental_value": total_expected_incremental_value,
        "n_candidates": len(candidates),
        "n_selected": len(selected_actions),
        "n_skipped": len(skipped_actions),
        "n_no_action": len(no_action_candidates),
    }