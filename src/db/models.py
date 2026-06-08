from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.database import Base

class DecisionLog(Base):
    __tablename__ = "decision_logs"

    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    features: Mapped[dict] = mapped_column(JSON, nullable=False)

    treatment_probability: Mapped[float] = mapped_column(Float, nullable=False)
    control_probability: Mapped[float] = mapped_column(Float, nullable=False)
    uplift_score: Mapped[float] = mapped_column(Float, nullable=False)

    customer_value: Mapped[float] = mapped_column(Float, nullable=False)
    treatment_cost: Mapped[float] = mapped_column(Float, nullable=False)
    expected_incremental_value: Mapped[float] = mapped_column(Float, nullable=False)
    roi: Mapped[float] = mapped_column(Float, nullable=False)

    recommended_action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    decision_reason: Mapped[list] = mapped_column(JSON, nullable=False)

    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_alias: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    feedback_logs: Mapped[list["FeedbackLog"]] = relationship(
        back_populates="decision_log",
        cascade="all, delete-orphan",
    )

class FeedbackLog(Base):
    __tablename__ = "feedback_logs"

    feedback_id: Mapped[str] = mapped_column(String, primary_key=True)

    decision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("decision_logs.decision_id"),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    observed_outcome: Mapped[int] = mapped_column(Integer, nullable=False)
    simulated_outcome_probability: Mapped[float] = mapped_column(Float, nullable=False)

    customer_value: Mapped[float] = mapped_column(Float, nullable=False)
    treatment_cost: Mapped[float] = mapped_column(Float, nullable=False)
    realized_value: Mapped[float] = mapped_column(Float, nullable=False)

    feedback_delay_days: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    decision_log: Mapped[DecisionLog] = relationship(back_populates="feedback_logs")

Index("idx_decision_logs_created_action", DecisionLog.created_at, DecisionLog.recommended_action)
Index("idx_feedback_logs_observed_at", FeedbackLog.observed_at)
Index("idx_feedback_logs_user_outcome", FeedbackLog.user_id, FeedbackLog.observed_outcome)