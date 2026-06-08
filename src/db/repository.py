from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import DecisionLog


def create_decision_log(
    session: Session,
    decision_id: str,
    user_id: str,
    features: dict,
    treatment_probability: float,
    control_probability: float,
    uplift_score: float,
    customer_value: float,
    treatment_cost: float,
    expected_incremental_value: float,
    roi: float,
    recommended_action: str,
    decision_reason: list[str],
    model_name: str,
    model_alias: str,
    model_version: str,
) -> DecisionLog:
    decision_log = DecisionLog(
        decision_id=decision_id,
        user_id=user_id,
        features=features,
        treatment_probability=treatment_probability,
        control_probability=control_probability,
        uplift_score=uplift_score,
        customer_value=customer_value,
        treatment_cost=treatment_cost,
        expected_incremental_value=expected_incremental_value,
        roi=roi,
        recommended_action=recommended_action,
        decision_reason=decision_reason,
        model_name=model_name,
        model_alias=model_alias,
        model_version=model_version,
    )

    session.add(decision_log)
    session.commit()
    session.refresh(decision_log)

    return decision_log


def get_decision_log_by_id(session: Session, decision_id: str) -> DecisionLog | None:
    return session.get(DecisionLog, decision_id)


def get_action_distribution(session: Session) -> list[dict]:
    statement = (
        select(
            DecisionLog.recommended_action,
            func.count(DecisionLog.decision_id).label("count"),
        )
        .group_by(DecisionLog.recommended_action)
        .order_by(func.count(DecisionLog.decision_id).desc())
    )

    rows = session.execute(statement).all()

    return [
        {
            "recommended_action": row.recommended_action,
            "count": row.count,
        }
        for row in rows
    ]


def get_average_uplift_score(session: Session) -> float | None:
    statement = select(func.avg(DecisionLog.uplift_score))
    result = session.execute(statement).scalar_one_or_none()

    return float(result) if result is not None else None
