import pytest

from src.policy.config import load_policy_config
from src.policy.decision_engine import (
    calculate_expected_value,
    recommend_action,
    recommend_action_from_policy,
)


def test_expected_value():
    value = calculate_expected_value(
        uplift_score=0.1,
        customer_value=100,
        treatment_cost=5,
    )

    assert value == 5


def test_simple_policy_no_action_when_negative_roi():
    result = recommend_action(
        uplift_score=0.01,
        customer_value=100,
        treatment_cost=5,
    )

    assert result["recommended_action"] == "no_action"


def test_simple_policy_standard_discount():
    result = recommend_action(
        uplift_score=0.12,
        customer_value=100,
        treatment_cost=5,
    )

    assert result["recommended_action"] == "standard_discount"
    assert result["expected_incremental_value"] == 7


def test_config_loader_reads_policy_yaml():
    config = load_policy_config()

    assert "no_action" in config.actions
    assert "low_cost_email" in config.actions
    assert "standard_discount" in config.actions
    assert "premium_offer" in config.actions
    assert config.min_uplift_for_action == 0.02
    assert config.max_daily_budget == 10000.0


def test_policy_returns_no_action_for_negative_uplift():
    result = recommend_action_from_policy(
        uplift_score=-0.01,
        customer_value=100,
    )

    assert result["recommended_action"] == "no_action"
    assert "non_positive_uplift" in result["decision_reason"]


def test_policy_returns_no_action_below_global_threshold():
    result = recommend_action_from_policy(
        uplift_score=0.01,
        customer_value=100,
    )

    assert result["recommended_action"] == "no_action"
    assert "below_global_uplift_threshold" in result["decision_reason"]


def test_policy_recommends_low_cost_email():
    result = recommend_action_from_policy(
        uplift_score=0.03,
        customer_value=100,
    )

    assert result["recommended_action"] == "low_cost_email"
    assert result["treatment_cost"] == 0.2
    assert result["expected_incremental_value"] == pytest.approx(2.8)


def test_policy_recommends_standard_discount():
    result = recommend_action_from_policy(
        uplift_score=0.12,
        customer_value=100,
    )

    assert result["recommended_action"] == "standard_discount"
    assert result["treatment_cost"] == 5.0
    assert result["expected_incremental_value"] == pytest.approx(7.0)


def test_policy_recommends_premium_offer():
    result = recommend_action_from_policy(
        uplift_score=0.25,
        customer_value=200,
    )

    assert result["recommended_action"] == "premium_offer"
    assert result["treatment_cost"] == 15.0
    assert result["expected_incremental_value"] == pytest.approx(35.0)


def test_policy_raises_for_invalid_customer_value():
    with pytest.raises(ValueError, match="customer_value must be greater than 0"):
        recommend_action_from_policy(
            uplift_score=0.2,
            customer_value=0,
        )