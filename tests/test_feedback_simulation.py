import numpy as np

from src.feedback.simulate_feedback import (
    calculate_realized_value,
    get_simulated_outcome_probability,
    is_treatment_action,
    simulate_binary_outcome,
)


class DummyDecision:
    def __init__(
        self,
        recommended_action: str,
        treatment_probability: float,
        control_probability: float,
    ):
        self.recommended_action = recommended_action
        self.treatment_probability = treatment_probability
        self.control_probability = control_probability


def test_is_treatment_action_returns_false_for_no_action():
    assert is_treatment_action("no_action") is False


def test_is_treatment_action_returns_true_for_intervention():
    assert is_treatment_action("standard_discount") is True


def test_get_simulated_outcome_probability_uses_control_for_no_action():
    decision = DummyDecision(
        recommended_action="no_action",
        treatment_probability=0.8,
        control_probability=0.2,
    )

    assert get_simulated_outcome_probability(decision) == 0.2


def test_get_simulated_outcome_probability_uses_treatment_for_action():
    decision = DummyDecision(
        recommended_action="premium_offer",
        treatment_probability=0.8,
        control_probability=0.2,
    )

    assert get_simulated_outcome_probability(decision) == 0.8


def test_calculate_realized_value_subtracts_treatment_cost():
    assert calculate_realized_value(
        observed_outcome=1,
        customer_value=100,
        treatment_cost=5,
    ) == 95


def test_simulate_binary_outcome_clips_probability():
    rng = np.random.default_rng(42)

    assert simulate_binary_outcome(probability=2.0, rng=rng) == 1
    assert simulate_binary_outcome(probability=-1.0, rng=rng) == 0