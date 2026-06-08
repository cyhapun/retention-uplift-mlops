from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.database import Base
from src.db.feedback_repository import (
    count_feedback_logs,
    create_feedback_log,
    get_decisions_without_feedback,
    get_feedback_log_by_decision_id,
    get_feedback_summary_by_action,
)
from src.db.repository import create_decision_log


def create_test_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)

    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    return testing_session_local()


def create_test_decision(session, decision_id="decision_001", action="standard_discount"):
    return create_decision_log(
        session=session,
        decision_id=decision_id,
        user_id="user_001",
        features={"f0": 0.1},
        treatment_probability=0.25,
        control_probability=0.10,
        uplift_score=0.15,
        customer_value=100.0,
        treatment_cost=5.0,
        expected_incremental_value=10.0,
        roi=2.0,
        recommended_action=action,
        decision_reason=["positive_uplift"],
        model_name="uplift_model",
        model_alias="champion",
        model_version="test",
    )


def test_create_feedback_log_persists_row():
    session = create_test_session()
    decision = create_test_decision(session)

    feedback = create_feedback_log(
        session=session,
        feedback_id="feedback_001",
        decision_id=decision.decision_id,
        user_id=decision.user_id,
        observed_outcome=1,
        simulated_outcome_probability=0.25,
        customer_value=100.0,
        treatment_cost=5.0,
        realized_value=95.0,
        feedback_delay_days=7,
    )

    saved = get_feedback_log_by_decision_id(
        session=session,
        decision_id=decision.decision_id,
    )

    assert saved is not None
    assert saved.feedback_id == feedback.feedback_id
    assert saved.observed_outcome == 1
    assert count_feedback_logs(session) == 1


def test_get_decisions_without_feedback_excludes_feedbacked_decisions():
    session = create_test_session()
    decision = create_test_decision(session)

    assert len(get_decisions_without_feedback(session)) == 1

    create_feedback_log(
        session=session,
        feedback_id="feedback_001",
        decision_id=decision.decision_id,
        user_id=decision.user_id,
        observed_outcome=1,
        simulated_outcome_probability=0.25,
        customer_value=100.0,
        treatment_cost=5.0,
        realized_value=95.0,
        feedback_delay_days=7,
    )

    assert get_decisions_without_feedback(session) == []


def test_get_feedback_summary_by_action_returns_action_level_metrics():
    session = create_test_session()
    decision = create_test_decision(session)

    create_feedback_log(
        session=session,
        feedback_id="feedback_001",
        decision_id=decision.decision_id,
        user_id=decision.user_id,
        observed_outcome=1,
        simulated_outcome_probability=0.25,
        customer_value=100.0,
        treatment_cost=5.0,
        realized_value=95.0,
        feedback_delay_days=7,
    )

    summary = get_feedback_summary_by_action(session)

    assert len(summary) == 1
    assert summary[0]["recommended_action"] == "standard_discount"
    assert summary[0]["n_feedback"] == 1
    assert summary[0]["observed_outcome_rate"] == 1.0
    assert summary[0]["total_realized_value"] == 95.0