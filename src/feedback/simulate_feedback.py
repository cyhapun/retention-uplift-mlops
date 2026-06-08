import argparse
from uuid import uuid4

import numpy as np
from sqlalchemy.orm import Session

from src.db.database import SessionLocal, init_database
from src.db.feedback_repository import (
    create_feedback_log,
    get_decisions_without_feedback,
    get_feedback_summary_by_action,
)


def is_treatment_action(recommended_action: str) -> bool:
    return recommended_action != "no_action"


def get_simulated_outcome_probability(decision) -> float:
    if is_treatment_action(decision.recommended_action):
        return float(decision.treatment_probability)

    return float(decision.control_probability)


def simulate_binary_outcome(
    probability: float,
    rng: np.random.Generator,
) -> int:
    probability = min(max(probability, 0.0), 1.0)

    return int(rng.random() < probability)


def calculate_realized_value(
    observed_outcome: int,
    customer_value: float,
    treatment_cost: float,
) -> float:
    return observed_outcome * customer_value - treatment_cost


def simulate_feedback_for_decisions(
    session: Session,
    limit: int = 1000,
    feedback_delay_days: int = 7,
    random_state: int = 42,
) -> dict:
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")

    if feedback_delay_days < 0:
        raise ValueError("feedback_delay_days must be greater than or equal to 0.")

    rng = np.random.default_rng(random_state)

    decisions = get_decisions_without_feedback(
        session=session,
        limit=limit,
    )

    created_feedback = []

    for decision in decisions:
        outcome_probability = get_simulated_outcome_probability(decision)

        observed_outcome = simulate_binary_outcome(
            probability=outcome_probability,
            rng=rng,
        )

        realized_value = calculate_realized_value(
            observed_outcome=observed_outcome,
            customer_value=float(decision.customer_value),
            treatment_cost=float(decision.treatment_cost),
        )

        feedback_log = create_feedback_log(
            session=session,
            feedback_id=str(uuid4()),
            decision_id=decision.decision_id,
            user_id=decision.user_id,
            observed_outcome=observed_outcome,
            simulated_outcome_probability=outcome_probability,
            customer_value=float(decision.customer_value),
            treatment_cost=float(decision.treatment_cost),
            realized_value=realized_value,
            feedback_delay_days=feedback_delay_days,
        )

        created_feedback.append(feedback_log)

    summary_by_action = get_feedback_summary_by_action(session)

    total_realized_value = sum(
        float(feedback.realized_value)
        for feedback in created_feedback
    )

    observed_outcome_rate = (
        sum(int(feedback.observed_outcome) for feedback in created_feedback) / len(created_feedback)
        if created_feedback
        else 0.0
    )

    return {
        "n_decisions_available": len(decisions),
        "n_feedback_created": len(created_feedback),
        "observed_outcome_rate": observed_outcome_rate,
        "total_realized_value_created": total_realized_value,
        "summary_by_action": summary_by_action,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate delayed feedback for decision logs.")

    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of decisions to simulate feedback for.",
    )
    parser.add_argument(
        "--feedback-delay-days",
        type=int,
        default=7,
        help="Simulated delay between decision and observed feedback.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible feedback simulation.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    init_database()

    with SessionLocal() as session:
        summary = simulate_feedback_for_decisions(
            session=session,
            limit=args.limit,
            feedback_delay_days=args.feedback_delay_days,
            random_state=args.random_state,
        )

    print("Feedback simulation completed.")
    for key, value in summary.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()