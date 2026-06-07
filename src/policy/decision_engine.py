from src.policy.config import PolicyConfig, load_policy_config


def calculate_expected_value(
    uplift_score: float,
    customer_value: float,
    treatment_cost: float,
) -> float:
    return uplift_score * customer_value - treatment_cost


def calculate_roi(expected_value: float, treatment_cost: float) -> float:
    if treatment_cost <= 0:
        return 0.0

    return expected_value / treatment_cost


def recommend_action(
    uplift_score: float,
    customer_value: float,
    treatment_cost: float,
) -> dict:
    """
    Backward-compatible simple policy.

    This function will be useful later in FastAPI when a request directly provides
    a treatment cost. The config-driven function below is preferred for production.
    """
    expected_value = calculate_expected_value(
        uplift_score=uplift_score,
        customer_value=customer_value,
        treatment_cost=treatment_cost,
    )

    if uplift_score <= 0 or expected_value <= 0:
        action = "no_action"
    elif uplift_score >= 0.20 and expected_value >= 20:
        action = "premium_offer"
    elif uplift_score >= 0.10 and expected_value >= 5:
        action = "standard_discount"
    else:
        action = "low_cost_email"

    return {
        "uplift_score": uplift_score,
        "customer_value": customer_value,
        "treatment_cost": treatment_cost,
        "expected_incremental_value": expected_value,
        "roi": calculate_roi(expected_value, treatment_cost),
        "recommended_action": action,
    }


def get_no_action_decision(
    uplift_score: float,
    customer_value: float,
    reason: str,
) -> dict:
    return {
        "uplift_score": uplift_score,
        "customer_value": customer_value,
        "treatment_cost": 0.0,
        "expected_incremental_value": 0.0,
        "roi": 0.0,
        "recommended_action": "no_action",
        "decision_reason": [reason],
    }


def recommend_action_from_policy(
    uplift_score: float,
    customer_value: float,
    policy_config: PolicyConfig | None = None,
) -> dict:
    """
    Config-driven policy engine.

    It chooses the highest-value eligible action whose:
    - uplift is above global and action-specific thresholds
    - expected incremental value is positive
    - expected incremental value is above the action threshold
    """
    if policy_config is None:
        policy_config = load_policy_config()

    if customer_value <= 0:
        raise ValueError("customer_value must be greater than 0.")

    if uplift_score <= 0:
        return get_no_action_decision(
            uplift_score=uplift_score,
            customer_value=customer_value,
            reason="non_positive_uplift",
        )

    if uplift_score < policy_config.min_uplift_for_action:
        return get_no_action_decision(
            uplift_score=uplift_score,
            customer_value=customer_value,
            reason="below_global_uplift_threshold",
        )

    candidate_decisions = []

    for action_name, action_config in policy_config.actions.items():
        if action_name == "no_action":
            continue

        expected_value = calculate_expected_value(
            uplift_score=uplift_score,
            customer_value=customer_value,
            treatment_cost=action_config.cost,
        )

        is_eligible = (
            uplift_score >= action_config.min_uplift
            and expected_value > 0
            and expected_value >= action_config.min_expected_value
        )

        if not is_eligible:
            continue

        candidate_decisions.append(
            {
                "uplift_score": uplift_score,
                "customer_value": customer_value,
                "treatment_cost": action_config.cost,
                "expected_incremental_value": expected_value,
                "roi": calculate_roi(expected_value, action_config.cost),
                "recommended_action": action_name,
                "action_priority": action_config.priority,
                "decision_reason": [
                    "positive_uplift",
                    "positive_expected_value",
                    "action_threshold_met",
                ],
            }
        )

    if not candidate_decisions:
        return get_no_action_decision(
            uplift_score=uplift_score,
            customer_value=customer_value,
            reason="no_action_met_policy_thresholds",
        )

    candidate_decisions.sort(
        key=lambda decision: (
            decision["action_priority"],
            decision["expected_incremental_value"],
            decision["roi"],
        ),
        reverse=True,
    )

    return candidate_decisions[0]
