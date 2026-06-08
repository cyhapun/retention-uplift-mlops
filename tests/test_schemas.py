import pytest
from pydantic import ValidationError

from src.serving.schemas import DecisionRequest


def test_decision_request_accepts_valid_payload():
    request = DecisionRequest(
        user_id="user_001",
        customer_value=100,
        features={f"f{i}": 0.1 for i in range(11)},
    )

    assert request.user_id == "user_001"
    assert request.customer_value == 100
    assert len(request.features) == 11


def test_decision_request_rejects_empty_user_id():
    with pytest.raises(ValidationError):
        DecisionRequest(
            user_id="",
            customer_value=100,
            features={f"f{i}": 0.1 for i in range(11)},
        )


def test_decision_request_rejects_non_positive_customer_value():
    with pytest.raises(ValidationError):
        DecisionRequest(
            user_id="user_001",
            customer_value=0,
            features={f"f{i}": 0.1 for i in range(11)},
        )
