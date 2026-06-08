from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker

from src.db.database import Base
from src.db.repository import (
    create_decision_log,
    get_action_distribution,
    get_average_uplift_score,
    get_decision_log_by_id,
)


def create_test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    return testing_session_local()


def test_create_decision_log_persists_row():
    session = create_test_session()

    decision_log = create_decision_log(
        session=session,
        decision_id="decision_001",
        user_id="user_001",
        features={"f0": 0.1},
        treatment_probability=0.25,
        control_probability=0.10,
        uplift_score=0.15,
        customer_value=100.0,
        treatment_cost=5.0,
        expected_incremental_value=10.0,
        roi=2.0,
        recommended_action="standard_discount",
        decision_reason=["positive_uplift"],
        model_name="uplift_model",
        model_alias="champion",
        model_version="test",
    )

    saved = get_decision_log_by_id(
        session=session,
        decision_id=decision_log.decision_id,
    )

    assert saved is not None
    assert saved.user_id == "user_001"
    assert saved.recommended_action == "standard_discount"
    assert saved.uplift_score == 0.15


def test_get_action_distribution_returns_counts():
    session = create_test_session()

    for idx in range(2):
        create_decision_log(
            session=session,
            decision_id=f"decision_{idx}",
            user_id=f"user_{idx}",
            features={"f0": 0.1},
            treatment_probability=0.25,
            control_probability=0.10,
            uplift_score=0.15,
            customer_value=100.0,
            treatment_cost=5.0,
            expected_incremental_value=10.0,
            roi=2.0,
            recommended_action="standard_discount",
            decision_reason=["positive_uplift"],
            model_name="uplift_model",
            model_alias="champion",
            model_version="test",
        )

    distribution = get_action_distribution(session)

    assert distribution == [{"recommended_action": "standard_discount", "count": 2}]


def test_get_average_uplift_score_returns_average():
    session = create_test_session()

    create_decision_log(
        session=session,
        decision_id="decision_001",
        user_id="user_001",
        features={"f0": 0.1},
        treatment_probability=0.25,
        control_probability=0.10,
        uplift_score=0.15,
        customer_value=100.0,
        treatment_cost=5.0,
        expected_incremental_value=10.0,
        roi=2.0,
        recommended_action="standard_discount",
        decision_reason=["positive_uplift"],
        model_name="uplift_model",
        model_alias="champion",
        model_version="test",
    )

    create_decision_log(
        session=session,
        decision_id="decision_002",
        user_id="user_002",
        features={"f0": 0.2},
        treatment_probability=0.30,
        control_probability=0.10,
        uplift_score=0.20,
        customer_value=100.0,
        treatment_cost=5.0,
        expected_incremental_value=15.0,
        roi=3.0,
        recommended_action="standard_discount",
        decision_reason=["positive_uplift"],
        model_name="uplift_model",
        model_alias="champion",
        model_version="test",
    )

    assert get_average_uplift_score(session) == 0.175