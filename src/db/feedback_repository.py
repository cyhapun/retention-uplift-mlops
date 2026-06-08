from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import DecisionLog, FeedbackLog


def get_decisions_without_feedback(
    session: Session,
    limit: int = 1000,
) -> list[DecisionLog]:
    statement = (
        select(DecisionLog)
        .outerjoin(
            FeedbackLog,
            DecisionLog.decision_id == FeedbackLog.decision_id,
        )
        .where(FeedbackLog.decision_id.is_(None))
        .order_by(DecisionLog.created_at.asc())
        .limit(limit)
    )

    return list(session.execute(statement).scalars().all())


def create_feedback_log(
    session: Session,
    feedback_id: str,
    decision_id: str,
    user_id: str,
    observed_outcome: int,
    simulated_outcome_probability: float,
    customer_value: float,
    treatment_cost: float,
    realized_value: float,
    feedback_delay_days: int,
    observed_at: datetime | None = None,
) -> FeedbackLog:
    if observed_at is None:
        observed_at = datetime.now(timezone.utc)

    feedback_log = FeedbackLog(
        feedback_id=feedback_id,
        decision_id=decision_id,
        user_id=user_id,
        observed_outcome=observed_outcome,
        simulated_outcome_probability=simulated_outcome_probability,
        customer_value=customer_value,
        treatment_cost=treatment_cost,
        realized_value=realized_value,
        feedback_delay_days=feedback_delay_days,
        observed_at=observed_at,
    )

    session.add(feedback_log)
    session.commit()
    session.refresh(feedback_log)

    return feedback_log


def get_feedback_log_by_decision_id(
    session: Session,
    decision_id: str,
) -> FeedbackLog | None:
    statement = select(FeedbackLog).where(FeedbackLog.decision_id == decision_id)

    return session.execute(statement).scalar_one_or_none()


def get_feedback_summary_by_action(session: Session) -> list[dict]:
    statement = (
        select(
            DecisionLog.recommended_action,
            func.count(FeedbackLog.feedback_id).label("n_feedback"),
            func.avg(FeedbackLog.observed_outcome).label("observed_outcome_rate"),
            func.avg(DecisionLog.expected_incremental_value).label("avg_expected_incremental_value"),
            func.sum(FeedbackLog.realized_value).label("total_realized_value"),
            func.sum(DecisionLog.treatment_cost).label("total_treatment_cost"),
        )
        .join(DecisionLog, DecisionLog.decision_id == FeedbackLog.decision_id)
        .group_by(DecisionLog.recommended_action)
        .order_by(func.count(FeedbackLog.feedback_id).desc())
    )

    rows = session.execute(statement).all()

    return [
        {
            "recommended_action": row.recommended_action,
            "n_feedback": int(row.n_feedback),
            "observed_outcome_rate": float(row.observed_outcome_rate or 0.0),
            "avg_expected_incremental_value": float(row.avg_expected_incremental_value or 0.0),
            "total_realized_value": float(row.total_realized_value or 0.0),
            "total_treatment_cost": float(row.total_treatment_cost or 0.0),
        }
        for row in rows
    ]


def count_feedback_logs(session: Session) -> int:
    statement = select(func.count(FeedbackLog.feedback_id))

    return int(session.execute(statement).scalar_one())